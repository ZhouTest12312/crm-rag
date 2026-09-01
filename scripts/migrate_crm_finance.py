"""创建优惠券 / 现金券 / 退款单表并种子数据（纯本地）。

依赖：先有 work_order（可先跑 migrate_work_orders.py）。

用法：
  $env:PYTHONPATH=\"D:\\workspace\\edu-crm-langgraph\"
  .venv\\Scripts\\python scripts\\migrate_crm_finance.py
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal

from sqlalchemy import text

from config.db_conf import AsyncSessionLocal
from models.cash_voucher import CashVoucher
from models.coupon import Coupon
from models.refund_order import RefundOrder

CREATE_COUPON = """
CREATE TABLE IF NOT EXISTS coupon (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  coupon_no VARCHAR(32) NOT NULL,
  student_id INT NOT NULL,
  name VARCHAR(100) NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'unused',
  order_no VARCHAR(32) NULL,
  order_source VARCHAR(32) NOT NULL DEFAULT 'offline',
  created_at DATETIME NULL,
  updated_at DATETIME NULL,
  UNIQUE KEY uk_coupon_no (coupon_no)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

CREATE_CASH = """
CREATE TABLE IF NOT EXISTS cash_voucher (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  voucher_no VARCHAR(32) NOT NULL,
  student_id INT NOT NULL,
  face_value DECIMAL(10,2) NOT NULL,
  balance DECIMAL(10,2) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  order_no VARCHAR(32) NULL,
  created_at DATETIME NULL,
  updated_at DATETIME NULL,
  UNIQUE KEY uk_voucher_no (voucher_no)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

CREATE_REFUND = """
CREATE TABLE IF NOT EXISTS refund_order (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  refund_no VARCHAR(32) NOT NULL,
  order_no VARCHAR(32) NOT NULL,
  student_id INT NOT NULL,
  work_no VARCHAR(32) NULL,
  amount DECIMAL(10,2) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  channel VARCHAR(32) NOT NULL DEFAULT 'original',
  reason VARCHAR(255) NULL,
  created_at DATETIME NULL,
  updated_at DATETIME NULL,
  UNIQUE KEY uk_refund_no (refund_no)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


async def _count(db, table: str) -> int:
    return (await db.execute(text(f"SELECT COUNT(*) FROM {table}"))).scalar_one()


async def migrate() -> None:
    now = datetime.now()
    async with AsyncSessionLocal() as db:
        await db.execute(text(CREATE_COUPON))
        await db.execute(text(CREATE_CASH))
        await db.execute(text(CREATE_REFUND))
        await db.commit()
        print("tables coupon / cash_voucher / refund_order ready")

    async with AsyncSessionLocal() as db:
        if await _count(db, "coupon") == 0:
            db.add_all(
                [
                    Coupon(
                        coupon_no="CPN20250901001",
                        student_id=5,
                        name="秋季开学满减100",
                        amount=Decimal("100.00"),
                        status="unused",
                        order_source="douyin",
                        updated_at=now,
                    ),
                    Coupon(
                        coupon_no="CPN20250901002",
                        student_id=5,
                        name="老生续报立减50",
                        amount=Decimal("50.00"),
                        status="used",
                        order_no="ENR20250820005",
                        order_source="renewal",
                        updated_at=now,
                    ),
                    Coupon(
                        coupon_no="CPN20250901003",
                        student_id=3,
                        name="转介绍优惠80",
                        amount=Decimal("80.00"),
                        status="unused",
                        order_source="referral",
                        updated_at=now,
                    ),
                ]
            )
            print("seeded coupons")
        else:
            print("skip coupon seed")

        if await _count(db, "cash_voucher") == 0:
            db.add_all(
                [
                    CashVoucher(
                        voucher_no="CV20250901001",
                        student_id=5,
                        face_value=Decimal("200.00"),
                        balance=Decimal("120.00"),
                        status="active",
                        order_no="ENR20250820005",
                        updated_at=now,
                    ),
                    CashVoucher(
                        voucher_no="CV20250901002",
                        student_id=2,
                        face_value=Decimal("300.00"),
                        balance=Decimal("0.00"),
                        status="used_up",
                        order_no="ENR20250815002",
                        updated_at=now,
                    ),
                    CashVoucher(
                        voucher_no="CV20250901003",
                        student_id=3,
                        face_value=Decimal("150.00"),
                        balance=Decimal("150.00"),
                        status="active",
                        updated_at=now,
                    ),
                ]
            )
            print("seeded cash vouchers")
        else:
            print("skip cash_voucher seed")

        if await _count(db, "refund_order") == 0:
            db.add_all(
                [
                    RefundOrder(
                        refund_no="RF20250901001",
                        order_no="ENR20250820005",
                        student_id=5,
                        work_no="WO20260901002",
                        amount=Decimal("1200.00"),
                        status="pending",
                        channel="original",
                        reason="开课后退班试算",
                        updated_at=now,
                    ),
                    RefundOrder(
                        refund_no="RF20250901002",
                        order_no="ENR20250815002",
                        student_id=2,
                        work_no="WO20260901005",
                        amount=Decimal("900.00"),
                        status="paid",
                        channel="original",
                        reason="结转退班",
                        updated_at=now,
                    ),
                    RefundOrder(
                        refund_no="RF20250901003",
                        order_no="ENR20250820008",
                        student_id=8,
                        work_no=None,
                        amount=Decimal("500.00"),
                        status="approved",
                        channel="transfer",
                        reason="协商退款",
                        updated_at=now,
                    ),
                ]
            )
            print("seeded refunds")
        else:
            print("skip refund seed")

        await db.commit()
        print("migrate_crm_finance ok")


if __name__ == "__main__":
    asyncio.run(migrate())
