"""enrollment 增加 order_source，并回填演示来源。

用法：
  $env:PYTHONPATH=\"D:\\workspace\\edu-crm-langgraph\"
  .venv\\Scripts\\python scripts\\migrate_order_source.py
"""
from __future__ import annotations

import asyncio

from sqlalchemy import text

from config.db_conf import AsyncSessionLocal

# 按 id 轮转回填，纯本地演示
SOURCES = ("offline", "douyin", "referral", "renewal", "phone", "other")


async def _column_exists(db, table: str, column: str) -> bool:
    sql = text(
        """
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = :table
          AND COLUMN_NAME = :column
        """
    )
    n = (await db.execute(sql, {"table": table, "column": column})).scalar_one()
    return n > 0


async def migrate() -> None:
    async with AsyncSessionLocal() as db:
        if not await _column_exists(db, "enrollment", "order_source"):
            await db.execute(
                text(
                    """
                    ALTER TABLE enrollment
                    ADD COLUMN order_source VARCHAR(32) NOT NULL DEFAULT 'offline'
                    COMMENT 'order source'
                    AFTER free_transfer_used
                    """
                )
            )
            await db.commit()
            print("added enrollment.order_source")
        else:
            print("order_source already exists")

    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(text("SELECT id FROM enrollment ORDER BY id"))
        ).all()
        for i, (eid,) in enumerate(rows):
            src = SOURCES[i % len(SOURCES)]
            await db.execute(
                text("UPDATE enrollment SET order_source = :src WHERE id = :id"),
                {"src": src, "id": eid},
            )
        await db.commit()
        print(f"backfilled {len(rows)} enrollments")


if __name__ == "__main__":
    asyncio.run(migrate())
