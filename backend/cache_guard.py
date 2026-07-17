"""
枫桥智盾 · 缓存防护模块
========================

三层缓存安全机制，防止 Redis 高并发场景下的常见问题：

1. 缓存穿透防护（Cache Penetration）
   - 查询不存在的数据时，缓存空值（Null Object），TTL 较短（60s）
   - 避免恶意/高频查询不存在的 key 直接打穿到数据库

2. 缓存击穿防护（Hotspot Invalid / Cache Breakdown）
   - 热点 key 过期瞬间，大量并发请求同时穿透到 DB
   - 方案：互斥锁（Mutex），同一 key 同一时刻仅一个请求去重建缓存
   - 其他请求等待并复用重建结果

3. 缓存雪崩防护（Cache Avalanche）
   - 大量 key 同时过期导致 DB 瞬时压力骤增
   - 方案：TTL 增加 ±20% 随机抖动（Jitter），分散过期时间点

4. 并发控制（Request Coalescing）
   - 同一 key 的并发 miss 请求，只发一次 DB 查询
   - threading.Event 实现请求合并

使用方式：
  result = await cache_get_or_set('user:123', ttl=3600, fetch_fn=lambda: db.query(...))
"""
import time, random, threading
from redis_adapter import get_cache

r = get_cache()

# ===== 配置 =====
NULL_TTL = 60                # 空值缓存 TTL（秒）
NULL_PLACEHOLDER = '__NULL__'
DEFAULT_TTL = 3600           # 默认缓存 TTL（1 小时）
JITTER_RATIO = 0.2           # TTL 抖动幅度（±20%）
MUTEX_TIMEOUT = 30           # 互斥锁超时（秒）

# ===== 互斥锁表 =====
_mutex_locks: dict[str, threading.Lock] = {}
_mutex_results: dict[str, any] = {}
_mutex_events: dict[str, threading.Event] = {}
_lock_registry = threading.Lock()


def _jitter(ttl: int) -> int:
    """TTL 增加 ±JITTER_RATIO 随机抖动，防止批量过期"""
    if ttl <= 60:
        return ttl  # 短 TTL 不加抖动
    jitter = int(ttl * JITTER_RATIO * random.uniform(-1, 1))
    return max(ttl // 2, ttl + jitter)


def _get_mutex(key: str) -> threading.Lock:
    """获取或创建 key 级互斥锁"""
    with _lock_registry:
        if key not in _mutex_locks:
            _mutex_locks[key] = threading.Lock()
            _mutex_events[key] = threading.Event()
        return _mutex_locks[key]


def _cleanup_mutex(key: str):
    """清理互斥锁资源（避免内存泄漏）"""
    with _lock_registry:
        _mutex_locks.pop(key, None)
        _mutex_results.pop(key, None)
        _mutex_events.pop(key, None)


def cache_get_or_set(key: str, ttl: int = None, fetch_fn=None, null_cache: bool = True):
    """
    缓存读取（带穿透/击穿/雪崩三重防护）。

    Args:
        key: Redis 缓存键
        ttl: 过期时间（秒），默认 3600
        fetch_fn: 缓存 miss 时的数据获取函数
        null_cache: 是否缓存空值（防穿透）

    Returns:
        缓存中的数据，或 fetch_fn 的返回值

    流程：
      1. 先查 Redis 缓存 → 命中直接返回
      2. Miss 时加互斥锁 → 只有一个请求去查 DB
      3. 其他等待的请求在锁释放后读取缓存结果
      4. 空值也缓存（防止穿透），TTL 较短
    """
    ttl = ttl or DEFAULT_TTL

    # 1. 查缓存
    cached = r.get(key)
    if cached is not None:
        if cached == NULL_PLACEHOLDER:
            return None
        # 尝试 JSON 反序列化，失败则返回原始字符串
        import json
        try:
            return json.loads(cached)
        except (json.JSONDecodeError, TypeError):
            return cached

    if not fetch_fn:
        return None

    # 2. 缓存 miss → 加互斥锁
    mutex = _get_mutex(key)

    if not mutex.acquire(blocking=False):
        # 锁已被其他线程持有 → 等待重建完成
        event = _mutex_events.get(key)
        if event:
            event.wait(timeout=MUTEX_TIMEOUT)
        # 重新读缓存
        cached = r.get(key)
        if cached is not None:
            if cached == NULL_PLACEHOLDER:
                return None
            import json
            try:
                return json.loads(cached)
            except (json.JSONDecodeError, TypeError):
                return cached
        return fetch_fn()  # 超时则自己查

    # 3. 获得锁 → 执行数据获取
    try:
        # Double-check: 再查一次（可能已被前一个请求写入）
        cached = r.get(key)
        if cached is not None:
            if cached == NULL_PLACEHOLDER:
                return None
            import json
            try:
                return json.loads(cached)
            except (json.JSONDecodeError, TypeError):
                return cached

        # 真正查 DB
        try:
            data = fetch_fn()
        except Exception:
            raise

        # 写入缓存
        if data is None and null_cache:
            r.setex(key, _jitter(NULL_TTL), NULL_PLACEHOLDER)
        elif data is not None:
            import json
            r.setex(key, _jitter(ttl), json.dumps(data, ensure_ascii=False, default=str))
        return data

    finally:
        # 通知等待者
        event = _mutex_events.get(key)
        if event:
            event.set()
            event.clear()
        mutex.release()


def cache_get_or_set_sync(key: str, ttl: int = None, fetch_fn=None, null_cache: bool = True):
    """同步版本，直接调用（无需 async/await）"""
    return cache_get_or_set(key, ttl, fetch_fn, null_cache)


def invalidate(key: str):
    """清除指定缓存"""
    r.delete(key)


def invalidate_pattern(pattern: str):
    """批量清除匹配模式的缓存（慎用，影响面大）"""
    keys = r.keys(pattern)
    if keys:
        r.delete(*keys)


def cache_stats() -> dict:
    """返回缓存防护状态"""
    return {
        'active_mutexes': len(_mutex_locks),
        'null_cache_ttl': NULL_TTL,
        'default_ttl': DEFAULT_TTL,
        'jitter_ratio': JITTER_RATIO,
    }
