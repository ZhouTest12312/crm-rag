"""创建 work_order 表并写入演示工单（纯本地，与线上 CRM 无关）。

用法：
  .venv\\Scripts\\python scripts\\migrate_work_orders.py
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import text

from config.db_conf import AsyncSessionLocal
from crud.work_orders import create_work_order, search_work_orders
from schemas.work_order import WorkOrderCreate, WorkOrderQuery


CREATE_SQL = """
CREATE TABLE IF NOT EXISTS work_order (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  work_no VARCHAR(32) NOT NULL,
  apply_type VARCHAR(32) NOT NULL COMMENT 'apply type',
  order_no VARCHAR(32) NOT NULL COMMENT 'enrollment order_no',
  student_id INT NOT NULL,
  from_class_id INT NOT NULL COMMENT 'from class',
  to_class_id INT NULL COMMENT 'to class',
  order_source VARCHAR(32) NOT NULL DEFAULT 'offline' COMMENT 'order source',
  status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'status',
  reason VARCHAR(255) NULL COMMENT 'reason',
  amount DECIMAL(10,2) NULL COMMENT 'amount',
  fee_amount DECIMAL(10,2) NULL COMMENT 'fee',
  applicant VARCHAR(50) NOT NULL DEFAULT 'advisor' COMMENT 'applicant',
  remark TEXT NULL COMMENT 'remark',
  created_at DATETIME NULL COMMENT 'created',
  updated_at DATETIME NULL COMMENT 'updated',
  UNIQUE KEY uk_work_no (work_no),
  KEY idx_order_no (order_no),
  KEY idx_status (status)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='work order local'
"""

SEED = [
    WorkOrderCreate(
        apply_type="change_class",
        order_no="ENR20250820005",
        student_id=5,
        from_class_id=5,
        to_class_id=1,
        order_source="offline",
        reason="同科目换时段",
        amount=Decimal("0"),
        fee_amount=Decimal("0"),
        applicant="顾问小王",
    ),
    WorkOrderCreate(
        apply_type="withdraw",
        order_no="ENR20250820005",
        student_id=5,
        from_class_id=5,
        to_class_id=None,
        order_source="douyin",
        reason="开课后试算退班",
        amount=Decimal("1200.00"),
        fee_amount=Decimal("60.00"),
        applicant="顾问小李",
    ),
    WorkOrderCreate(
        apply_type="transfer_class",
        order_no="ENR20250820003",
        student_id=3,
        from_class_id=3,
        to_class_id=2,
        order_source="referral",
        reason="转不同科目",
        amount=Decimal("300.00"),
        fee_amount=Decimal("0"),
        applicant="顾问小王",
    ),
    WorkOrderCreate(
        apply_type="settle_transfer",
        order_no="ENR20250820003",
        student_id=3,
        from_class_id=3,
        to_class_id=4,
        order_source="renewal",
        reason="原班结课结转换班",
        amount=Decimal("0"),
        fee_amount=Decimal("0"),
        applicant="教务小张",
    ),
    WorkOrderCreate(
        apply_type="settle_refund",
        order_no="ENR20250815002",
        student_id=2,
        from_class_id=2,
        to_class_id=None,
        order_source="phone",
        reason="结课不转新班，结转退班",
        amount=Decimal("900.00"),
        fee_amount=Decimal("0"),
        applicant="教务小张",
    ),
]


async def migrate() -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(text(CREATE_SQL))
        await db.commit()
        print("table work_order ready")

    async with AsyncSessionLocal() as db:
        existing, total = await search_work_orders(
            db, WorkOrderQuery(page=1, page_size=1)
        )
        if total > 0:
            print(f"skip seed: already {total} work orders")
            return
        for body in SEED:
            # 种子里部分订单可能已 cancelled，仍允许建历史工单演示
            row = await create_work_order(db, body)
            print(f"seed {row.work_no} {row.apply_type}")
        await db.commit()
        print(f"seeded {len(SEED)} work orders")


if __name__ == "__main__":
    asyncio.run(migrate())
