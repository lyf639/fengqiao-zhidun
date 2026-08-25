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
    """查询任务状态（兼容 decode_responses 字符串键）"""
    data = r.hgetall(f'task:{task_id}')
    if not data:
        return {'task_id': task_id, 'status': 'not_found'}
    # fakeredis decode_responses=True 返回 str 键，真实 redis 返回 bytes 键，两者兼容
    def _get(key: str, default: str = '') -> str:
        v = data.get(key, default)
        if v is None:
            v = data.get(key.encode(), default)
        if isinstance(v, bytes):
            v = v.decode()
        return v
    return {
        'task_id': task_id,
        'status': _get('status', 'unknown'),
        'progress': int(_get('progress', '0') or 0),
        'result': _get('result', '') or None,
        'created_at': _get('created_at', ''),
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
    from concurrent.futures import ThreadPoolExecutor
    batch = params.get('batch', '')
    case_ids = params.get('case_ids', [])
    if not batch or not case_ids:
        return {'error': '缺少 batch 或 case_ids'}

    session = get_session()
    matches = []
    results = []
    # 全局 AI 调用预算：候选过多时用规则引擎兜底，保证任务在有限时间内完成
    AI_BUDGET = 120
    ai_calls = 0
    try:
        new_cases = session.query(Case).filter(Case.import_batch == batch).all()
        total = len(new_cases)
        for idx, new_case in enumerate(new_cases):
            new_dict = {
                'parties': new_case.parties or '',
                'district': new_case.district or '',
                'dispute_type': new_case.dispute_type or '',
                'description': new_case.description or '',
            }
            # 字段级预筛：pre=电话+地址+姓名（满分 80），总评 = pre + 语义(0~20)，阈值 85。
            # 仅当 65 ≤ pre < 85 时语义分才可能影响判定 → 只对该区间候选调 AI，
            # pre ≥ 85（防御，实际最大 80）直接判重复，pre < 65 直接判唯一。
            candidates = []
            immediate_dups = []
            for old_case in session.query(Case).filter(Case.id != new_case.id).all():
                old_dict = {
                    'parties': old_case.parties or '',
                    'district': old_case.district or '',
                    'dispute_type': old_case.dispute_type or '',
                    'description': old_case.description or '',
                }
                f = field_scores(new_dict, old_dict)
                pre = f['phone'] + f['address'] + f['name']
                if pre >= 85:
                    immediate_dups.append((old_case, f, pre))
                elif pre >= 65:
                    candidates.append((old_case, f, pre))
            candidates.sort(key=lambda x: x[2], reverse=True)
            candidates = candidates[:5]

            # 并发调用 AI 语义，避免串行 30s 超时堆积
            def ai_judge(cand):
                old_case, f, pre = cand
                semantic = 0
                if ai_calls < AI_BUDGET:
                    try:
                        a_text = f"{new_dict['description']} {new_dict['dispute_type']}"
                        b_text = f"{old_case.description or ''} {old_case.dispute_type or ''}"
                        if a_text.strip() and b_text.strip():
                            sim = semantic_similarity(
                                {'description': a_text, 'dispute_type': ''},
                                {'description': b_text, 'dispute_type': ''},
                            )
                            semantic = max(0, min(20, int(sim.get('score', 0))))
                    except Exception:
                        pass
                return (old_case, f, pre, semantic)

            processed = []
            if candidates:
                with ThreadPoolExecutor(max_workers=5) as ex:
                    processed = list(ex.map(ai_judge, candidates))
                ai_calls += len(candidates)

            for old_case, f, pre, semantic in processed + [(c[0], c[1], c[2], 0) for c in immediate_dups]:
                total_score = pre + semantic
                if total_score >= 85:
                    session.add(DedupRecord(case_id=new_case.id, matched_case_id=old_case.id,
                        score_phone=f['phone'], score_address=f['address'],
                        score_semantic=semantic, score_name=f['name'], total_score=total_score))
                    new_case.dedup_status = 2
                    matches.append({'case_id': new_case.id, 'matched': old_case.id, 'score': total_score})
                    results.append({
                        'case_id': new_case.id, 'match_count': 1, 'total_score': total_score,
                        'ai_backend': 'async', 'ai_reason': '字段+AI 语义综合判定',
                    })
            update_status(task_id, 'running', progress=10 + int(80 * (idx + 1) / total))
        session.commit()
        return {'success': True, 'matches': len(matches), 'total': total,
                'results': results, 'details': matches[:20]}
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
