"""
枫桥智盾 · Redis 异步任务队列
==============================

基于 Redis List 的轻量级消息队列，不引入 RabbitMQ/Kafka 等重依赖：
  - 发布：enqueue(task_name, params) → 写入 Redis List + 状态 Hash
  - 消费：后台线程轮询 → 执行任务 → 更新状态
  - 查询：get_status(task_id) → 前端轮询进度

适用场景：
  - 批量去重（AI 调用耗时长，42 条案件需逐条比对）
  - AI 分析报告生成（DeepSeek 响应 10-30 秒）
  - 后续扩展：数据导入后处理、定时预警扫描、钉钉批量推送
"""
import json, uuid, threading, time, traceback
from datetime import datetime
from redis_adapter import get_cache

r = get_cache()

# ===== 配置 =====
POLL_INTERVAL = 0.5          # 后台线程轮询间隔（秒）
TASK_TTL = 3600              # 任务状态保留 1 小时

# ===== 任务注册表 =====
_HANDLERS = {}

def register(name: str):
    """装饰器：注册任务处理函数"""
    def decorator(fn):
        _HANDLERS[name] = fn
        return fn
    return decorator

def enqueue(task_name: str, params: dict = None) -> str:
    """提交任务到队列，返回 task_id"""
    task_id = f"{task_name}_{uuid.uuid4().hex[:8]}"
    payload = {'task_id': task_id, 'task_name': task_name, 'params': params or {}}
    r.rpush(f'{task_name}:queue', json.dumps(payload, ensure_ascii=False))
    r.hset(f'task:{task_id}', mapping={
        'status': 'pending', 'progress': '0', 'result': '',
        'created_at': datetime.now().isoformat(),
    })
    r.expire(f'task:{task_id}', TASK_TTL)
    return task_id

def get_status(task_id: str) -> dict:
    """查询任务状态"""
    data = r.hgetall(f'task:{task_id}')
    if not data:
        return {'task_id': task_id, 'status': 'not_found'}
    return {
        'task_id': task_id,
        'status': data.get(b'status', b'').decode(),
        'progress': int(data.get(b'progress', b'0')),
        'result': data.get(b'result', b'').decode() or None,
        'created_at': data.get(b'created_at', b'').decode(),
    }

def update_status(task_id: str, status: str, progress: int = None, result: str = None):
    """更新任务状态"""
    mapping = {'status': status}
    if progress is not None:
        mapping['progress'] = str(progress)
    if result is not None:
        mapping['result'] = result
    r.hset(f'task:{task_id}', mapping=mapping)

# ===== 后台 Worker =====
_worker_started = False

def _worker_loop():
    """后台工作线程：轮询所有任务队列"""
    while True:
        for name in _HANDLERS:
            payload_raw = r.lpop(f'{name}:queue')
            if payload_raw:
                try:
                    payload = json.loads(payload_raw)
                    task_id = payload['task_id']
                    update_status(task_id, 'running', progress=10)
                    handler = _HANDLERS[name]
                    result = handler(payload.get('params', {}), task_id)
                    update_status(task_id, 'done', progress=100, result=json.dumps(result, ensure_ascii=False))
                except Exception as e:
                    task_id = payload.get('task_id', 'unknown') if 'payload' in dir() else 'unknown'
                    update_status(task_id, 'failed', result=traceback.format_exc())
        time.sleep(POLL_INTERVAL)

def start_worker():
    """启动后台任务消费者"""
    global _worker_started
    if _worker_started:
        return
    t = threading.Thread(target=_worker_loop, daemon=True, name='task-worker')
    t.start()
    _worker_started = True
    print('异步任务队列已启动（Redis-backed）')


# ===== 具体任务定义 =====

@register('dedup_batch')
def task_dedup_batch(params: dict, task_id: str) -> dict:
    """异步执行批量去重（耗时操作，逐条比对 AI 语义）"""
    from models import Case, DedupRecord, get_session
    from ai_service import semantic_similarity, field_scores
    batch = params.get('batch', '')
    case_ids = params.get('case_ids', [])
    if not batch or not case_ids:
        return {'error': '缺少 batch 或 case_ids'}

    session = get_session()
    matches = []
    try:
        new_cases = session.query(Case).filter(Case.import_batch == batch).all()
        total = len(new_cases)
        for idx, new_case in enumerate(new_cases):
            old_cases = session.query(Case).filter(Case.id.notin_([c.id for c in new_cases])).all()
            for old_case in old_cases:
                a = {c.name: getattr(new_case, c.name) for c in Case.__table__.columns}
                b = {c.name: getattr(old_case, c.name) for c in Case.__table__.columns}
                scores = field_scores(a, b)
                semantic = 0
                try:
                    a_text = f"{a.get('description','')} {a.get('dispute_type','')}"
                    b_text = f"{b.get('description','')} {b.get('dispute_type','')}"
                    if a_text.strip() and b_text.strip():
                        semantic = max(0, min(20, int(semantic_similarity(a_text, b_text) * 20)))
                except:
                    pass
                total_score = scores['phone'] + scores['address'] + semantic + scores['name']
                if total_score >= 85:
                    session.add(DedupRecord(case_id=new_case.id, matched_case_id=old_case.id,
                        score_phone=scores['phone'], score_address=scores['address'],
                        score_semantic=semantic, score_name=scores['name'], total_score=total_score))
                    new_case.dedup_status = 2
                    matches.append({'case_id': new_case.id, 'matched': old_case.id, 'score': total_score})
            update_status(task_id, 'running', progress=10 + int(80 * (idx + 1) / total))
        session.commit()
        return {'success': True, 'matches': len(matches), 'total': total, 'details': matches[:20]}
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


@register('generate_report')
def task_generate_report(params: dict, task_id: str) -> dict:
    """异步生成 AI 分析报告"""
    from report_generator import generate_report
    update_status(task_id, 'running', progress=30)
    result = generate_report(
        report_type=params.get('report_type', 'monthly'),
        year=params.get('year'),
        period=params.get('period'),
    )
    update_status(task_id, 'running', progress=90)
    return {'success': True, 'report': result}
