"""
枫桥智盾 · Prometheus 监控指标
================================

暴露 `/metrics` 端点供 Prometheus + Grafana 采集，覆盖：

  业务指标：
    - fengqiao_cases_total          案件总数
    - fengqiao_dedup_total          去重识别数
    - fengqiao_alerts_total         预警总数（按等级分 label）
    - fengqiao_import_duration      导入耗时
    - fengqiao_ai_call_total        AI 调用次数（按 backend 分 label）
    - fengqiao_cache_hit_total      缓存命中/未命中

  HTTP 指标：
    - fengqiao_requests_total       请求总数（method/endpoint/status）
    - fengqiao_request_duration     请求耗时 Histogram

  系统指标：
    - fengqiao_db_connections       数据库连接数
    - fengqiao_task_queue_size      任务队列长度

Grafana 对接：导入 grafana_dashboard.json 即可展示完整大盘。
"""
import time, threading
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST

_registry = CollectorRegistry()

# ===== 业务指标 =====
cases_total = Counter('fengqiao_cases_total', '案件总数', ['status'], registry=_registry)
dedup_total = Counter('fengqiao_dedup_matches_total', '去重匹配数', registry=_registry)
alerts_total = Counter('fengqiao_alerts_total', '预警总数', ['level'], registry=_registry)
ai_call_total = Counter('fengqiao_ai_call_total', 'AI 调用次数', ['backend'], registry=_registry)
cache_hits = Counter('fengqiao_cache_hits', '缓存命中', ['result'], registry=_registry)

import_histogram = Histogram('fengqiao_import_duration_seconds', '导入耗时(秒)', buckets=[0.1, 0.5, 1, 2, 5, 10, 30], registry=_registry)

# ===== HTTP 指标 =====
request_total = Counter('fengqiao_requests_total', '请求总数', ['method', 'endpoint', 'status'], registry=_registry)
request_duration = Histogram('fengqiao_request_duration_seconds', '请求耗时(秒)', ['method', 'endpoint'], buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10, 30], registry=_registry)

# ===== 系统指标 =====
db_connections = Gauge('fengqiao_db_connections', '数据库活跃连接数', ['type'], registry=_registry)
task_queue_size = Gauge('fengqiao_task_queue_size', '任务队列长度', ['queue'], registry=_registry)
active_users = Gauge('fengqiao_active_users', '活跃用户数', registry=_registry)


# ===== 中间件 =====

class MetricsMiddleware:
    """FastAPI 中间件：自动记录每个请求的计数和耗时"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        start = time.time()
        method = scope.get('method', 'UNKNOWN')
        path = scope.get('path', '/')

        async def send_wrapper(message):
            if message['type'] == 'http.response.start':
                status = str(message.get('status', 200))
                duration = time.time() - start
                request_total.labels(method=method, endpoint=path, status=status).inc()
                request_duration.labels(method=method, endpoint=path).observe(duration)
            await send(message)

        await self.app(scope, receive, send_wrapper)


def get_metrics_response():
    """返回 Prometheus 文本格式的指标数据"""
    return generate_latest(_registry), CONTENT_TYPE_LATEST


def update_task_queue_metrics():
    """后台更新任务队列指标（每 30 秒）"""
    from redis_adapter import get_cache
    r = get_cache()
    try:
        for queue_name in ['dedup_batch:queue', 'generate_report:queue']:
            size = r.llen(queue_name) or 0
            task_queue_size.labels(queue=queue_name.split(':')[0]).set(size)
    except:
        pass


def start_metrics_updater():
    """启动指标后台更新线程"""
    def _updater():
        while True:
            try:
                update_task_queue_metrics()
            except:
                pass
            time.sleep(30)

    t = threading.Thread(target=_updater, daemon=True)
    t.start()
