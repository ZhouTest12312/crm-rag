"""报名 CRUD。对照：edu-crm-agent/crud/enrollments.py"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import models  # noqa: F401 — 注册 student / crm_class，避免 flush 时 NoReferencedTableError
from models.enrollment import Enrollment
from schemas.enrollment import EnrollmentCreate, EnrollmentQuery


async def get_detail_order_no(db: AsyncSession, order_no: str) -> Enrollment | None:
    stmt = select(Enrollment).where(Enrollment.order_no == str(order_no).upper())
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_max_lesson(db: AsyncSession):
    stmt = (
        select(Enrollment)
        .order_by(Enrollment.paid_amount.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def count_enrollments(db: AsyncSession, status: str | None = None) -> int:
    stmt = select(func.count()).select_from(Enrollment)
    if status:
        stmt = stmt.where(Enrollment.status == status)
    return (await db.execute(stmt)).scalar_one()


async def list_enrollments_brief(
    db: AsyncSession, *, status: str | None = None, limit: int = 20
):
    stmt = select(Enrollment)
    if status:
        stmt = stmt.where(Enrollment.status == status)
    else:
        stmt = stmt.where(Enrollment.status != "cancelled")
    stmt = stmt.order_by(Enrollment.id.desc()).limit(limit)
    return (await db.execute(stmt)).scalars().all()


async def count_by_order_source(db: AsyncSession):
    stmt = (
        select(Enrollment.order_source, func.count(Enrollment.id))
        .group_by(Enrollment.order_source)
        .order_by(func.count(Enrollment.id).desc())
    )
    return (await db.execute(stmt)).all()
# 兼容 tools / 旧名
get_by_order_no = get_detail_order_no


async def list_by_student_id(db: AsyncSession, student_id: str | int):
    stmt = select(Enrollment).where(Enrollment.student_id == int(student_id))
    result = await db.execute(stmt)
    return result.scalars().all()


def _apply_enrollment_filters(stmt, query: EnrollmentQuery):
    if query.id is not None:
        stmt = stmt.where(Enrollment.id == query.id)
    if query.order_no:
        stmt = stmt.where(Enrollment.order_no.like(f"%{query.order_no}%"))
    if query.student_id is not None:
        stmt = stmt.where(Enrollment.student_id == query.student_id)
    if query.class_id is not None:
        stmt = stmt.where(Enrollment.class_id == query.class_id)
    if query.status:
        stmt = stmt.where(Enrollment.status == query.status)
    if query.paid_amount is not None:
        stmt = stmt.where(Enrollment.paid_amount == query.paid_amount)
    if query.consumed_lessons is not None:
        stmt = stmt.where(Enrollment.consumed_lessons == query.consumed_lessons)
    return stmt


async def search_enrollments(db: AsyncSession, query: EnrollmentQuery):
    stmt = _apply_enrollment_filters(select(Enrollment), query)
    if query.status:
        stmt = stmt.where(Enrollment.status == query.status)
    else:
        stmt = stmt.where(Enrollment.status != "cancelled")
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (query.page - 1) * query.page_size
    stmt = (
        stmt.order_by(Enrollment.id.desc()).offset(offset).limit(query.page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return rows, total


async def update_status_by_order_no(db: AsyncSession, order_no: str, status: str):
    row = await get_detail_order_no(db, order_no)
    if not row:
        return None
    row.status = status
    await db.flush()
    return row



async def create_enrollment(db: AsyncSession, query: EnrollmentCreate):
    total_lessons = query.total_lessons
    unit_price = query.unit_price
    if unit_price is None:
        unit_price = query.paid_amount / total_lessons
    row = Enrollment(
        order_no=query.order_no.upper(),
        student_id=query.student_id,
        class_id=query.class_id,
        paid_amount=query.paid_amount,
        total_lessons=total_lessons,
        unit_price=unit_price,
        status=query.status,
        consumed_lessons=0,
        free_transfer_used=0,
    )
    db.add(row)
    await db.flush()
    return row


