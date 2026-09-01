from fastapi import APIRouter, Depends, HTTPException

from config.db_conf import get_database
from crud.enrollments import list_by_student_id
from crud.students import get_student_id, list_students
from schemas.student import StudentQuery

router = APIRouter(prefix="/api/student", tags=["student"])


@router.get("/list")
async def list_student(query: StudentQuery = Depends(), db=Depends(get_database)):
    rows, total = await list_students(db, query)
    return {
        "code": "200",
        "msg": "success",
        "data": {
            "total": total,
            "page": query.page,
            "page_size": query.page_size,
            "students": [
                {
                    "id": r.id,
                    "name": r.name,
                    "phone": r.phone,
                    "verified": r.verified,
                }
                for r in rows
            ],
        },
    }


@router.get("/{id}/enrollments")
async def get_student_enrollments(id: str, db=Depends(get_database)):
    student = await get_student_id(db, id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    rows = await list_by_student_id(db, id)
    return {
        "code": "200",
        "msg": "success",
        "data": {
            "student_id": student.id,
            "count": len(rows),
            "enrollments": [
                {
                    "id": r.id,
                    "order_no": r.order_no,
                    "class_id": r.class_id,
                    "status": r.status,
                    "paid_amount": str(r.paid_amount),
                    "consumed_lessons": r.consumed_lessons,
                }
                for r in rows
            ],
        },
    }


@router.get("/detail/{id}")
async def get_student(id: str, db=Depends(get_database)):
    result = await get_student_id(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="学生不存在")
    return {
        "code": "200",
        "msg": "success",
        "data": {
            "id": result.id,
            "name": result.name,
            "phone": result.phone,
        },
    }
