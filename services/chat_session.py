"""多轮会话：Redis 存 messages（对照：edu-crm-agent/services/chat_session.py）"""
from __future__ import annotations

import json

from config.redis_conf import get_redis

PENDING_PREFIX = "edu-crm-langgraph:pending-cancel:"
_memory_pending: dict[str, str] = {}
PREFIX = "edu-crm-langgraph:session:"
TTL = 86400  # 24 小时

# Redis 没起来时，先放内存里（重启会丢；Day6 演示够用）
_memory_sessions: dict[str, list[dict]] = {}


def load_messages(session_id: str | None) -> list[dict]:
    """读历史。无 session_id → 空列表。"""
    if not session_id:
        return []

    r = get_redis()
    if r is None:
        return list(_memory_sessions.get(session_id, []))

    raw = r.get(PREFIX + session_id)  # key = 前缀 + session_id
    if not raw:
        return []
    return json.loads(raw)  # 存的时候 dumps，读的时候 loads


def save_messages(session_id: str | None, messages: list[dict]) -> None:
    """写历史。只保留 user / assistant 的 role + content。"""
    if not session_id:
        return

    slim = [
        {"role": m["role"], "content": m["content"]}
        for m in messages
        if m.get("role") in ("user", "assistant")
    ]

    r = get_redis()
    if r is None:
        _memory_sessions[session_id] = slim
        return

    r.setex(PREFIX + session_id, TTL, json.dumps(slim, ensure_ascii=False))


def set_pending_cancel(session_id: str | None, order_no):
    if not session_id:
        return
    r = get_redis()
    if r is None:
        _memory_pending[session_id] = order_no
    else:
        r.setex(PENDING_PREFIX + session_id, TTL, order_no)


def peek_pending_cancel(session_id: str | None):
    if not session_id:
        return None
    r = get_redis()
    if r is None:
        return _memory_pending.get(session_id)
    else:
        return r.get(PENDING_PREFIX + session_id)


def clear_pending_cancel(session_id: str | None):
    if not session_id:
        return
    r = get_redis()
    if r is None:
        return _memory_pending.pop(session_id, None)
    else:
        return r.delete(PENDING_PREFIX + session_id)
