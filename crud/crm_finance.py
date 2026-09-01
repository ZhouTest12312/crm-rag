"""工单域 CRUD：工单 / 优惠券 / 现金券 / 退款单。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import models  # noqa: F401
from models.cash_voucher import CashVoucher
from models.coupon import Coupon
from models.refund_order import RefundOrder
from models.work_order import WorkOrder


async def list_work_orders(
    db: AsyncSession,
    *,
    status: str | None = None,
    apply_type: str | None = None,
    order_no: str | None = None,
    student_id: int | None = None,
    limit: int = 20,
):
    stmt = select(WorkOrder)
    if status:
        stmt = stmt.where(WorkOrder.status == status)
    if apply_type:
        stmt = stmt.where(WorkOrder.apply_type == apply_type)
    if order_no:
        stmt = stmt.where(WorkOrder.order_no == order_no.upper())
    if student_id is not None:
        stmt = stmt.where(WorkOrder.student_id == int(student_id))
    stmt = stmt.order_by(WorkOrder.id.desc()).limit(limit)
    return (await db.execute(stmt)).scalars().all()


async def count_work_orders(
    db: AsyncSession,
    *,
    status: str | None = None,
    apply_type: str | None = None,
) -> int:
    stmt = select(func.count()).select_from(WorkOrder)
    if status:
        stmt = stmt.where(WorkOrder.status == status)
    if apply_type:
        stmt = stmt.where(WorkOrder.apply_type == apply_type)
    return (await db.execute(stmt)).scalar_one()


async def list_coupons(
    db: AsyncSession,
    *,
    student_id: int | None = None,
    status: str | None = None,
    order_no: str | None = None,
    limit: int = 20,
):
    stmt = select(Coupon)
    if student_id is not None:
        stmt = stmt.where(Coupon.student_id == int(student_id))
    if status:
        stmt = stmt.where(Coupon.status == status)
    if order_no:
        stmt = stmt.where(Coupon.order_no == order_no.upper())
    stmt = stmt.order_by(Coupon.id.desc()).limit(limit)
    return (await db.execute(stmt)).scalars().all()


async def count_coupons(db: AsyncSession, *, status: str | None = None) -> int:
    stmt = select(func.count()).select_from(Coupon)
    if status:
        stmt = stmt.where(Coupon.status == status)
    return (await db.execute(stmt)).scalar_one()


async def list_cash_vouchers(
    db: AsyncSession,
    *,
    student_id: int | None = None,
    status: str | None = None,
    limit: int = 20,
):
    stmt = select(CashVoucher)
    if student_id is not None:
        stmt = stmt.where(CashVoucher.student_id == int(student_id))
    if status:
        stmt = stmt.where(CashVoucher.status == status)
    stmt = stmt.order_by(CashVoucher.id.desc()).limit(limit)
    return (await db.execute(stmt)).scalars().all()


async def count_cash_vouchers(db: AsyncSession, *, status: str | None = None) -> int:
    stmt = select(func.count()).select_from(CashVoucher)
    if status:
        stmt = stmt.where(CashVoucher.status == status)
    return (await db.execute(stmt)).scalar_one()


async def list_refunds(
    db: AsyncSession,
    *,
    order_no: str | None = None,
    student_id: int | None = None,
    status: str | None = None,
    refund_no: str | None = None,
    limit: int = 20,
):
    stmt = select(RefundOrder)
    if order_no:
        stmt = stmt.where(RefundOrder.order_no == order_no.upper())
    if student_id is not None:
        stmt = stmt.where(RefundOrder.student_id == int(student_id))
    if status:
        stmt = stmt.where(RefundOrder.status == status)
    if refund_no:
        stmt = stmt.where(RefundOrder.refund_no == refund_no.upper())
    stmt = stmt.order_by(RefundOrder.id.desc()).limit(limit)
    return (await db.execute(stmt)).scalars().all()


async def count_refunds(db: AsyncSession, *, status: str | None = None) -> int:
    stmt = select(func.count()).select_from(RefundOrder)
    if status:
        stmt = stmt.where(RefundOrder.status == status)
    return (await db.execute(stmt)).scalar_one()


async def get_refund_by_no(db: AsyncSession, refund_no: str) -> RefundOrder | None:
    stmt = select(RefundOrder).where(RefundOrder.refund_no == refund_no.upper())
    return (await db.execute(stmt)).scalar_one_or_none()


async def update_refund_status(
    db: AsyncSession, refund_no: str, status: str, reason: str | None = None
) -> RefundOrder | None:
    row = await get_refund_by_no(db, refund_no)
    if not row:
        return None
    row.status = status
    if reason is not None:
        row.reason = reason
    await db.flush()
    return row
