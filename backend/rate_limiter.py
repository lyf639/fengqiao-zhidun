"""
枫桥智盾 · 流量控制模块
========================

基于 Redis 令牌桶算法的分布式限流器。

  算法：令牌桶（Token Bucket）
    - 每个 key（IP/用户）对应一个桶，容量 = rate 个令牌
    - 令牌以 rate/window 的速率匀速补充
    - 请求到达时取一个令牌，无令牌则返回 429
    - 分布式安全：所有状态存储在 Redis，多 API 节点共享限流计数

  限流策略（三级）：
    strict    —— 30 req / 60s（后台管理 API，防暴力破解）
    normal    —— 100 req / 60s（业务 API）
    relaxed   —— 300 req / 60s（公开端点：dashboard/metrics）

  使用方式：
    @rate_limit('strict')
    def admin_login(...): ...

    @rate_limit('normal', key_fn=lambda r: r.client.host)
    def import_cases(...): ...
"""
import time
from functools import wraps
from fastapi import HTTPException, Request
from redis_adapter import get_cache

r = get_cache()

# ===== 预置策略 =====
POLICIES = {
    'strict':   {'rate': 30,  'window': 60},   # 30次/分钟
    'normal':   {'rate': 100, 'window': 60},   # 100次/分钟
    'relaxed':  {'rate': 300, 'window': 60},   # 300次/分钟
    'import':   {'rate': 10,  'window': 60},   # 导入10次/分钟
    'ai':       {'rate': 5,   'window': 60},   # AI 调用5次/分钟
}


def _get_client_ip(request: Request) -> str:
    """获取客户端真实 IP"""
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    client = getattr(request, 'client', None)
    return client.host if client else '127.0.0.1'


def check_rate_limit(key: str, rate: int, window: int) -> tuple[bool, int, int]:
    """
    令牌桶限流检查。

    Returns:
        (allowed, remaining, retry_after_seconds)
    """
    now = time.time()
    bucket_key = f'ratelimit:{key}'
    timestamp_key = f'ratelimit:{key}:ts'

    # 获取当前令牌数和上次填充时间
    tokens_str = r.get(bucket_key)
    tokens = float(tokens_str) if tokens_str else float(rate)
    last_ts_str = r.get(timestamp_key)
    last_ts = float(last_ts_str) if last_ts_str else now

    # 计算应补充的令牌数
    elapsed = now - last_ts
    refill = elapsed * (rate / window)
    tokens = min(float(rate), tokens + refill)

    # 尝试消费一个令牌
    remaining = 0
    allowed = False
    if tokens >= 1:
        tokens -= 1
        allowed = True
        remaining = int(tokens)

    # 计算重试等待时间
    retry_after = 0
    if not allowed:
        fill_time = (1 - tokens) * (window / rate)
        retry_after = max(1, int(fill_time))

    # 写回 Redis
    pipe = r.pipeline()
    pipe.setex(bucket_key, window * 2, str(tokens))
    pipe.setex(timestamp_key, window * 2, str(now))
    pipe.execute()

    return allowed, remaining, retry_after


def rate_limit(policy: str = 'normal', key_fn=None):
    """
    限流装饰器。

    Args:
        policy: 预置策略名（'strict'/'normal'/'relaxed'/'import'/'ai'）或自定义 dict
        key_fn: 自定义 key 生成函数，默认取客户端 IP

    Usage:
        @app.post('/api/import')
        @rate_limit('import')
        def import_data(request: Request, ...): ...
    """
    if isinstance(policy, str):
        cfg = POLICIES.get(policy, POLICIES['normal'])
    else:
        cfg = policy
    rate_val = cfg['rate']
    window_val = cfg['window']

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 提取 Request 对象
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get('request')

            if not request:
                return func(*args, **kwargs)

            # 生成限流 key
            key_prefix = func.__name__
            if key_fn:
                key = f'{key_prefix}:{key_fn(request)}'
            else:
                key = f'{key_prefix}:{_get_client_ip(request)}'

            allowed, remaining, retry = check_rate_limit(key, rate_val, window_val)
            if not allowed:
                raise HTTPException(
                    429,
                    detail=f'请求过于频繁，请 {retry} 秒后重试（限制：{rate_val}次/{window_val}秒）',
                    headers={'X-RateLimit-Retry-After': str(retry), 'Retry-After': str(retry)}
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator


def get_rate_limit_status(key: str) -> dict:
    """查询指定 key 的限流状态"""
    bucket_key = f'ratelimit:{key}'
    tokens = r.get(bucket_key)
    return {
        'key': key,
        'tokens_remaining': float(tokens) if tokens else 0,
    }
