"""
枫桥智盾 · Redis 连接适配器

统一 Redis 连接入口：
  - 开发/演示：fakeredis（零依赖，内存缓存）
  - 生产环境：redis-py（需 redis-server）
  - 切换方式：修改本文件顶部 import 即可
"""
import os, fakeredis

# 生产环境需连真实 Redis 时：
# import redis; _r = redis.Redis(host=os.getenv('REDIS_HOST','localhost'), port=int(os.getenv('REDIS_PORT',6379)), db=0, decode_responses=True)

_r = fakeredis.FakeRedis(decode_responses=True)


def get_cache():
    """返回 Redis 缓存实例（fakeredis 或真实 Redis）"""
    return _r
