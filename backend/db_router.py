"""
枫桥智盾 · 数据库读写分离路由
================================

MySQL 主从架构 + 连接池管理：
  - Master：处理所有 INSERT/UPDATE/DELETE
  - Slave(s)：处理所有 SELECT（轮询负载均衡）
  - 自动故障转移：Slave 不可用时自动回退到 Master
  - 连接池独立：主/从各自维护连接池，互不影响

环境变量：
  DB_MASTER_HOST=localhost               # 主库主机
  DB_SLAVE_HOSTS=localhost:3307          # 从库列表（逗号分隔，可选）
  DB_READ_STRATEGY=round_robin           # 读库选择策略
"""
import os, threading, random
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# ===== 基础连接参数 =====
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'FengQiao@2026')
DB_NAME = os.getenv('DB_NAME', 'fengqiao_zhidun')
DB_PORT = os.getenv('DB_PORT', '3306')

DB_MASTER_HOST = os.getenv('DB_MASTER_HOST', os.getenv('DB_HOST', 'localhost'))
DB_SLAVE_HOSTS_RAW = os.getenv('DB_SLAVE_HOSTS', '')
READ_STRATEGY = os.getenv('DB_READ_STRATEGY', 'round_robin')

_pwd_encoded = quote_plus(DB_PASSWORD)

# ===== Master 引擎 =====
def _make_engine(host: str) -> create_engine:
    return create_engine(
        f'mysql+pymysql://{DB_USER}:{_pwd_encoded}@{host}:{DB_PORT}/{DB_NAME}?charset=utf8mb4',
        poolclass=QueuePool, pool_size=20, max_overflow=10, pool_recycle=3600,
        echo=False,
    )

master_engine = _make_engine(DB_MASTER_HOST)
MasterSession = sessionmaker(bind=master_engine)

# ===== Slave 引擎池 =====
slave_engines = []
slave_sessions = []

def _init_slaves():
    """初始化从库连接池"""
    global slave_engines, slave_sessions
    raw = DB_SLAVE_HOSTS_RAW.strip()
    if not raw:
        return  # 无从库配置，所有查询回退到 Master

    for host in [h.strip() for h in raw.split(',') if h.strip()]:
        try:
            eng = _make_engine(host)
            slave_engines.append(eng)
            slave_sessions.append(sessionmaker(bind=eng))
            print(f'从库已连接: {host}')
        except Exception as e:
            print(f'从库连接失败: {host} - {e}')

_init_slaves()

# ===== 读库选择 =====
_slave_index = 0
_lock = threading.Lock()

def _next_slave() -> int | None:
    """选择下一个可用从库索引，Return None if none available"""
    global _slave_index
    if not slave_sessions:
        return None
    with _lock:
        if READ_STRATEGY == 'random':
            idx = random.randint(0, len(slave_sessions) - 1)
        else:  # round_robin
            idx = _slave_index % len(slave_sessions)
            _slave_index += 1
    return idx

# ===== 公共接口 =====

def get_master_session():
    """获取主库会话（用于写操作）"""
    return MasterSession()

def get_slave_session():
    """获取从库会话（用于读操作），无可用从库时回退到主库"""
    idx = _next_slave()
    if idx is not None:
        try:
            return slave_sessions[idx]()
        except Exception:
            pass  # 从库不可用，回退
    return MasterSession()

# 兼容旧接口
def get_session():
    """默认获取写库会话（保持向后兼容）"""
    return MasterSession()

def get_read_session():
    """获取读库会话"""
    return get_slave_session()

def get_write_session():
    """获取写库会话"""
    return get_master_session()

def get_master_engine():
    """获取主库引擎（供 init_db 建表使用）"""
    return master_engine

def get_status() -> dict:
    """返回集群状态"""
    return {
        'master': DB_MASTER_HOST,
        'slaves': [f'{h}' for h in DB_SLAVE_HOSTS_RAW.split(',') if h.strip()] if DB_SLAVE_HOSTS_RAW else [],
        'read_strategy': READ_STRATEGY,
        'active_slaves': len(slave_engines),
    }
