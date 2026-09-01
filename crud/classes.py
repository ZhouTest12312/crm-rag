from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.crm_class import CrmClass


async def list_classes(db: AsyncSession):
    stmt = select(CrmClass)
    result = await db.execute(stmt)
    return result.scalars().all()


async def list_classes_detail(db: AsyncSession, id: str | int):
    stmt = select(CrmClass).where(CrmClass.id == int(id))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def count_classes(db: AsyncSession, status: str | None = None) -> int:
    stmt = select(func.count()).select_from(CrmClass)
    if status:
        stmt = stmt.where(CrmClass.status == status)
    return (await db.execute(stmt)).scalar_one()


async def list_classes_brief(
    db: AsyncSession,
    *,
    status: str | None = None,
    subject: str | None = None,
    teacher_name: str | None = None,
    limit: int = 50,
):
    stmt = select(CrmClass)
    if status:
        stmt = stmt.where(CrmClass.status == status)
    if subject:
        stmt = stmt.where(CrmClass.subject.like(f"%{subject}%"))
    if teacher_name:
        stmt = stmt.where(CrmClass.teacher_name.like(f"%{teacher_name}%"))
    stmt = stmt.order_by(CrmClass.id.asc()).limit(limit)
    return (await db.execute(stmt)).scalars().all()


async def count_classes_filtered(
    db: AsyncSession,
    *,
    status: str | None = None,
    subject: str | None = None,
    teacher_name: str | None = None,
) -> int:
    stmt = select(func.count()).select_from(CrmClass)
    if status:
        stmt = stmt.where(CrmClass.status == status)
    if subject:
        stmt = stmt.where(CrmClass.subject.like(f"%{subject}%"))
    if teacher_name:
        stmt = stmt.where(CrmClass.teacher_name.like(f"%{teacher_name}%"))
    return (await db.execute(stmt)).scalar_one()


async def list_teachers(db: AsyncSession):
    """主讲老师去重列表 + 带班数。"""
    stmt = (
        select(
            CrmClass.teacher_name,
            func.count(CrmClass.id).label("class_count"),
        )
        .group_by(CrmClass.teacher_name)
        .order_by(CrmClass.teacher_name)
    )
    return (await db.execute(stmt)).all()
