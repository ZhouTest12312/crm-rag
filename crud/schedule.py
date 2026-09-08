"""课表 / 调课 / 分期 / 券退款 CRUD。"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.class_lesson import ClassLesson
from models.coupon_refund import CouponRefund
from models.installment import Installment
from models.schedule_change import ScheduleChange


async def list_lessons(
    db: AsyncSession,
    *,
    class_id: int,
    status: str | None = None,
    upcoming_only: bool = False,
    limit: int = 30,
):
    stmt = select(ClassLesson).where(ClassLesson.class_id == class_id)
    if status:
        stmt = stmt.where(ClassLesson.status == status)
    if upcoming_only:
        stmt = stmt.where(
            ClassLesson.lesson_date >= date.today(),
            ClassLesson.status.in_(("scheduled", "rescheduled")),
        )
    stmt = stmt.order_by(ClassLesson.lesson_no.asc()).limit(limit)
    return (await db.execute(stmt)).scalars().all()


async def next_lesson(db: AsyncSession, class_id: int) -> ClassLesson | None:
    rows = await list_lessons(db, class_id=class_id, upcoming_only=True, limit=1)
    return rows[0] if rows else None


async def list_schedule_changes(
    db: AsyncSession,
    *,
    class_id: int | None = None,
    teacher_name: str | None = None,
    status: str | None = None,
    limit: int = 30,
):
    stmt = select(ScheduleChange)
    if class_id is not None:
        stmt = stmt.where(ScheduleChange.class_id == class_id)
    if teacher_name:
        stmt = stmt.where(ScheduleChange.teacher_name.like(f"%{teacher_name}%"))
    if status:
        stmt = stmt.where(ScheduleChange.status == status)
    stmt = stmt.order_by(ScheduleChange.id.desc()).limit(limit)
    return (await db.execute(stmt)).scalars().all()


async def list_installments(db: AsyncSession, order_no: str):
    stmt = (
        select(Installment)
        .where(Installment.order_no == order_no.upper())
        .order_by(Installment.period_no.asc())
    )
    return (await db.execute(stmt)).scalars().all()


async def count_unpaid_installments(db: AsyncSession, order_no: str) -> int:
    stmt = (
        select(func.count())
        .select_from(Installment)
        .where(
            Installment.order_no == order_no.upper(),
            Installment.status.in_(("pending", "overdue")),
        )
    )
    return (await db.execute(stmt)).scalar_one()


async def list_coupon_refunds(
    db: AsyncSession,
    *,
    order_no: str | None = None,
    refund_no: str | None = None,
    status: str | None = None,
    limit: int = 30,
):
    stmt = select(CouponRefund)
    if order_no:
        stmt = stmt.where(CouponRefund.order_no == order_no.upper())
    if refund_no:
        stmt = stmt.where(CouponRefund.refund_no == refund_no.upper())
    if status:
        stmt = stmt.where(CouponRefund.status == status)
    stmt = stmt.order_by(CouponRefund.id.desc()).limit(limit)
    return (await db.execute(stmt)).scalars().all()
