"""为 enrollment 表增加 total_lessons / unit_price，并回填已有订单。"""
from __future__ import annotations

import asyncio
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import text

from config.db_conf import AsyncSessionLocal

DEMO_TOTAL_LESSONS = 30


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
        if not await _column_exists(db, "enrollment", "total_lessons"):
            await db.execute(
                text(
                    """
                    ALTER TABLE enrollment
                    ADD COLUMN total_lessons INT NOT NULL DEFAULT 30
                    COMMENT '购课总课次'
                    AFTER paid_amount
                    """
                )
            )
        if not await _column_exists(db, "enrollment", "unit_price"):
            await db.execute(
                text(
                    """
                    ALTER TABLE enrollment
                    ADD COLUMN unit_price DECIMAL(10, 2) NOT NULL DEFAULT 0.00
                    COMMENT '单课次原价'
                    AFTER total_lessons
                    """
                )
            )
        await db.commit()

    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                text(
                    "SELECT id, paid_amount, total_lessons, unit_price FROM enrollment"
                )
            )
        ).all()
        updated = 0
        for row in rows:
            paid = Decimal(str(row.paid_amount))
            total = int(row.total_lessons or 0)
            unit = Decimal(str(row.unit_price or 0))
            if total <= 0:
                total = DEMO_TOTAL_LESSONS
            if unit <= 0 and total > 0:
                unit = (paid / Decimal(total)).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            if (
                total != int(row.total_lessons or 0)
                or unit != Decimal(str(row.unit_price or 0))
            ):
                await db.execute(
                    text(
                        """
                        UPDATE enrollment
                        SET total_lessons = :total, unit_price = :unit
                        WHERE id = :id
                        """
                    ),
                    {"id": row.id, "total": total, "unit": unit},
                )
                updated += 1
        await db.commit()
        print(f"migrate ok: {len(rows)} rows, backfilled {updated}")


if __name__ == "__main__":
    asyncio.run(migrate())
