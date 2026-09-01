"""异步 MySQL。对照：edu-crm-agent/config/db_conf.py"""
from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from utils.setting import settings

T = TypeVar("T")

async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=5,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_database():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# 专用后台 loop：避免 asyncio.run 关 loop 后，aiomysql 连接池挂死（确认取消 500）
_loop: asyncio.AbstractEventLoop | None = None
_loop_lock = threading.Lock()


def _ensure_db_loop() -> asyncio.AbstractEventLoop:
    global _loop
    with _loop_lock:
        if _loop is not None and _loop.is_running():
            return _loop
        loop = asyncio.new_event_loop()

        def _runner() -> None:
            asyncio.set_event_loop(loop)
            loop.run_forever()

        t = threading.Thread(target=_runner, name="edu-crm-db-loop", daemon=True)
        t.start()
        _loop = loop
        return _loop


def run_async(coro: Awaitable[T]) -> T:
    """在同步 LangGraph / FastAPI 节点里跑一小段 async DB 代码。"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # 无运行中的 loop（常见：sync def 路由 / graph 节点）→ 丢到专用线程
        fut = asyncio.run_coroutine_threadsafe(coro, _ensure_db_loop())
        return fut.result()
    # 已在 async 上下文（如 async 路由）→ 不能再嵌套 asyncio.run
    raise RuntimeError(
        "run_async() 不能在已有事件循环里调用；请直接 await 对应的 async 函数"
    )
