"""
枫桥智盾 · 熔断器
==================

服务间调用的故障隔离机制，防止级联雪崩：
  - 关闭状态 (CLOSED)：正常调用，失败计数累计
  - 打开状态 (OPEN)  ：熔断触发，快速失败不调用下游
  - 半开状态 (HALF_OPEN)：冷却后试探性放行一个请求

适用场景：
  - gRPC AI 微服务调用（主服务 → AI 服务）
  - 外部 API 调用（DeepSeek 云端 API）
  - 数据库连接检测

配合 grpc_client 使用，熔断时自动降级到本地执行。
"""
import time, threading
from enum import Enum


class State(Enum):
    CLOSED = 1       # 正常
    OPEN = 2         # 熔断
    HALF_OPEN = 3    # 半开（试探）


class CircuitBreaker:
    """
    熔断器。

    config = {
        'failure_threshold': 5,    # 连续失败 5 次触发熔断
        'timeout': 30,             # 熔断后 30 秒进入半开状态
        'half_open_max': 1,        # 半开状态最多允许 1 个试探请求
        'success_threshold': 2,    # 连续成功 2 次关闭熔断
    }
    """

    def __init__(self, name: str, config: dict = None):
        self.name = name
        cfg = config or {}
        self.failure_threshold = cfg.get('failure_threshold', 5)
        self.timeout = cfg.get('timeout', 30)
        self.half_open_max = cfg.get('half_open_max', 1)
        self.success_threshold = cfg.get('success_threshold', 2)

        self.state = State.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.half_open_requests = 0
        self._lock = threading.Lock()

    def call(self, func, *args, fallback=None, **kwargs):
        """
        执行受保护调用。

        Args:
            func: 要调用的函数
            fallback: 熔断时的降级函数

        Returns:
            func() 或 fallback() 的返回值
        """
        with self._lock:
            if self.state == State.OPEN:
                if time.time() - self.last_failure_time >= self.timeout:
                    self.state = State.HALF_OPEN
                    self.half_open_requests = 0
                else:
                    # 熔断中，走降级
                    if fallback:
                        return fallback(*args, **kwargs)
                    raise CircuitBreakerError(f'[{self.name}] 熔断中，请 {int(self.timeout - (time.time() - self.last_failure_time))} 秒后重试')

            if self.state == State.HALF_OPEN:
                self.half_open_requests += 1
                if self.half_open_requests > self.half_open_max:
                    if fallback:
                        return fallback(*args, **kwargs)
                    raise CircuitBreakerError(f'[{self.name}] 半开状态已达试探上限')

        # 执行实际调用
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            if fallback:
                return fallback(*args, **kwargs)
            raise

    def _on_success(self):
        with self._lock:
            self.failure_count = 0
            if self.state == State.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = State.CLOSED
                    self.success_count = 0
                    self.half_open_requests = 0

    def _on_failure(self):
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = State.OPEN

    def status(self) -> dict:
        """返回熔断器状态"""
        return {
            'name': self.name,
            'state': self.state.name,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure': self.last_failure_time,
        }


class CircuitBreakerError(Exception):
    pass


# ===== 全局熔断器实例 =====

# AI 微服务熔断（gRPC 调用）
ai_breaker = CircuitBreaker('ai_grpc', {
    'failure_threshold': 3,
    'timeout': 60,
    'half_open_max': 1,
    'success_threshold': 2,
})

# DeepSeek API 熔断
deepseek_breaker = CircuitBreaker('deepseek_api', {
    'failure_threshold': 5,
    'timeout': 120,
})


def all_status() -> dict:
    """返回所有熔断器状态"""
    return {
        'ai_grpc': ai_breaker.status(),
        'deepseek_api': deepseek_breaker.status(),
    }
