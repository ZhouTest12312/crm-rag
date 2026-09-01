"""Redis 客户端（对照：edu-crm-agent/config/redis_conf.py）"""
from __future__ import annotations

import redis

from utils.setting import settings

_client = None


def get_redis():
    """连上 Redis 返回 client；连不上返回 None（后面用内存兜底）。"""
    global _client
    if _client is not None:
        return _client
    try:
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()  # ping 只是测通，返回值 True/False，不是 client
        _client = client
        return _client
    except Exception:
        return None
