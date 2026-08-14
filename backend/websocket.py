"""
枫桥智盾 · WebSocket 实时推送
================================

频道定义：
  - cockpit:feed        驾驶舱实时动态流（新案件、新预警）
  - cockpit:dashboard   仪表盘计数器更新
  - task:{task_id}      异步任务进度推送
  - alert:new            实时预警弹窗

前端连接：
  const ws = new WebSocket('ws://localhost:5000/ws');
  ws.onmessage = (e) => { const data = JSON.parse(e.data); ... };
"""
import json, asyncio
from fastapi import WebSocket, WebSocketDisconnect
from redis_adapter import get_cache

r = get_cache()

# 频道 → WebSocket 连接集合
_channels: dict[str, set[WebSocket]] = {}

# 定时任务：从 Redis 拉取消息并广播
_broadcast_task = None


async def register(ws: WebSocket, channel: str):
    """客户端订阅频道"""
    await ws.accept()
    if channel not in _channels:
        _channels[channel] = set()
    _channels[channel].add(ws)
    try:
        while True:
            await ws.receive_text()  # 保活心跳
    except WebSocketDisconnect:
        pass
    finally:
        _channels.get(channel, set()).discard(ws)


async def broadcast(channel: str, data: dict):
    """向频道所有客户端广播消息"""
    if channel not in _channels:
        return
    dead = set()
    payload = json.dumps(data, ensure_ascii=False)
    for ws in _channels[channel]:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    _channels[channel] -= dead


async def _feed_poller():
    """后台轮询 Redis feed 队列，推送到 WebSocket"""
    last_id = '0'
    while True:
        await asyncio.sleep(2)
        try:
            items = r.lrange('feed:list', 0, 0)
            if items:
                item = json.loads(items[0])
                msg_id = item.get('id', '')
                if msg_id != last_id:
                    last_id = msg_id
                    await broadcast('cockpit:feed', item)
                    # 驾驶舱计数从 DB 实时统计
                    from models import Case, get_session
                    from sqlalchemy import func
                    s = get_session()
                    try:
                        await broadcast('cockpit:dashboard', {
                            'type': 'dashboard_update',
                            'total': s.query(func.count(Case.id)).scalar() or 0,
                            'dedup': s.query(func.count(Case.id)).filter(Case.dedup_status >= 2).scalar() or 0,
                            'alerts': s.query(func.count(Case.id)).filter(Case.alert_level > 0).scalar() or 0,
                            'resolved': s.query(func.count(Case.id)).filter(Case.status >= 2).scalar() or 0,
                        })
                    finally:
                        s.close()
        except Exception:
            pass


def start_feed_poller():
    """启动 feed 轮询任务"""
    global _broadcast_task
    loop = asyncio.get_event_loop()
    _broadcast_task = loop.create_task(_feed_poller())
