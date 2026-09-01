from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.student import Student
from schemas.student import StudentQuery


async def get_student_id(db: AsyncSession, id: str | int):
    stmt = select(Student).where(Student.id == int(id))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _apply_student_filters(stmt, query: StudentQuery):
    if query.id is not None:
        stmt = stmt.where(Student.id == query.id)
    if query.name:
        stmt = stmt.where(Student.name.like(f"%{query.name}%"))
    if query.phone:
        stmt = stmt.where(Student.phone.like(f"%{query.phone}%"))
    if query.guardian_phone:
        stmt = stmt.where(Student.guardian_phone.like(f"%{query.guardian_phone}%"))
    if query.verified is not None:
        stmt = stmt.where(Student.verified == query.verified)
    return stmt


async def list_students(db: AsyncSession, query: StudentQuery):
    stmt = _apply_student_filters(select(Student), query)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (query.page - 1) * query.page_size
    stmt = stmt.order_by(Student.id.desc()).offset(offset).limit(query.page_size)
    rows = (await db.execute(stmt)).scalars().all()
    return rows, total


async def count_students(db: AsyncSession) -> int:
    return (await db.execute(select(func.count()).select_from(Student))).scalar_one()
