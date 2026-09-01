"""工单 CRUD。本地 work_order 表。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import models  # noqa: F401
from models.work_order import WorkOrder
from schemas.work_order import WorkOrderCreate, WorkOrderQuery


async def get_by_work_no(db: AsyncSession, work_no: str) -> WorkOrder | None:
    stmt = select(WorkOrder).where(WorkOrder.work_no == work_no.upper())
    return (await db.execute(stmt)).scalar_one_or_none()


def _apply_filters(stmt, query: WorkOrderQuery):
    if query.work_no:
        stmt = stmt.where(WorkOrder.work_no.like(f"%{query.work_no.upper()}%"))
    if query.apply_type:
        stmt = stmt.where(WorkOrder.apply_type == query.apply_type)
    if query.order_no:
        stmt = stmt.where(WorkOrder.order_no.like(f"%{query.order_no.upper()}%"))
    if query.student_id is not None:
        stmt = stmt.where(WorkOrder.student_id == query.student_id)
    if query.status:
        stmt = stmt.where(WorkOrder.status == query.status)
    if query.order_source:
        stmt = stmt.where(WorkOrder.order_source == query.order_source)
    return stmt


async def search_work_orders(db: AsyncSession, query: WorkOrderQuery):
    stmt = _apply_filters(select(WorkOrder), query)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()
    offset = (query.page - 1) * query.page_size
    stmt = stmt.order_by(WorkOrder.id.desc()).offset(offset).limit(query.page_size)
    rows = (await db.execute(stmt)).scalars().all()
    return rows, total


async def next_work_no(db: AsyncSession) -> str:
    """WO + YYYYMMDD + 三位序号。"""
    day = datetime.now().strftime("%Y%m%d")
    prefix = f"WO{day}"
    stmt = (
        select(func.count())
        .select_from(WorkOrder)
        .where(WorkOrder.work_no.like(f"{prefix}%"))
    )
    n = (await db.execute(stmt)).scalar_one() or 0
    return f"{prefix}{n + 1:03d}"


async def create_work_order(db: AsyncSession, body: WorkOrderCreate) -> WorkOrder:
    work_no = await next_work_no(db)
    row = WorkOrder(
        work_no=work_no,
        apply_type=body.apply_type,
        order_no=body.order_no.upper(),
        student_id=body.student_id,
        from_class_id=body.from_class_id,
        to_class_id=body.to_class_id,
        order_source=body.order_source,
        status="pending",
        reason=body.reason,
        amount=body.amount,
        fee_amount=body.fee_amount,
        applicant=body.applicant,
    )
    db.add(row)
    await db.flush()
    return row


async def update_status(
    db: AsyncSession, work_no: str, status: str, remark: str | None = None
) -> WorkOrder | None:
    row = await get_by_work_no(db, work_no)
    if not row:
        return None
    row.status = status
    if remark is not None:
        row.remark = remark
    await db.flush()
    return row
