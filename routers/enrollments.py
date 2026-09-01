from fastapi import APIRouter, Depends, HTTPException

from config.db_conf import get_database
from crud.classes import list_classes_detail
from crud.enrollments import (
    create_enrollment,
    get_detail_order_no,
    search_enrollments,
    update_status_by_order_no,
)
from crud.students import get_student_id
from schemas.enrollment import EnrollmentCreate, EnrollmentQuery, EnrollmentStatusUpdate
from utils.auth import require_perm

router = APIRouter(prefix="/api/enrollments", tags=["enrollments"])

ALLOWED = {"active", "pending_start", "completed", "refunded", "cancelled"}


@router.get("/list")
async def list_enrollments(query: EnrollmentQuery = Depends(), db=Depends(get_database)):
    rows, total = await search_enrollments(db, query)
    return {
        "code": "200",
        "msg": "success",
        "data": {
            "total": total,
            "page": query.page,
            "page_size": query.page_size,
            "enrollments": [
                {
                    "id": r.id,
                    "order_no": r.order_no,
                    "student_id": r.student_id,
                    "class_id": r.class_id,
                    "status": r.status,
                    "paid_amount": str(r.paid_amount),
                    "consumed_lessons": r.consumed_lessons,
                }
                for r in rows
            ],
        },
    }


@router.get("/{order_no}")
async def get_order_no(order_no: str, db=Depends(get_database)):
    result = await get_detail_order_no(db, order_no)
    if not result:
        raise HTTPException(status_code=404, detail="订单不存在")
    return {
        "code": "200",
        "msg": "success",
        "data": {
            "id": result.id,
            "order_no": result.order_no,
            "student_id": result.student_id,
            "class_id": result.class_id,
            "status": result.status,
            "paid_amount": str(result.paid_amount),
            "consumed_lessons": result.consumed_lessons,
        },
    }


@router.patch("/{order_no}")
async def patch_enrollment_status(
    order_no: str,
    body: EnrollmentStatusUpdate,
    db=Depends(get_database),
    _user=Depends(require_perm("order:write")),
):
    if body.status not in ALLOWED:
        raise HTTPException(status_code=400, detail="不在白名单")
    result = await update_status_by_order_no(db, order_no, body.status)
    if not result:
        raise HTTPException(status_code=404, detail="找不到订单")
    return {
        "code": "200",
        "msg": "success",
        "data": {
            "id": result.id,
            "order_no": result.order_no,
            "student_id": result.student_id,
            "class_id": result.class_id,
            "status": result.status,
            "paid_amount": str(result.paid_amount),
            "consumed_lessons": result.consumed_lessons,
        },
    }


@router.post("/add")
async def create_enrollment_api(
    body: EnrollmentCreate,
    db=Depends(get_database),
    _user=Depends(require_perm("order:write")),
):
    if body.status not in ALLOWED:
        raise HTTPException(status_code=400, detail="不在白名单")
    student = await get_student_id(db, body.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学员不存在")
    classes = await list_classes_detail(db, body.class_id)
    if not classes:
        raise HTTPException(status_code=404, detail="班级不存在")
    has_order = await get_detail_order_no(db, body.order_no)
    if has_order:
        raise HTTPException(status_code=409, detail="订单号已存在")
    result = await create_enrollment(db, body)
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "id": result.id,
            "order_no": result.order_no,
            "student_id": result.student_id,
            "class_id": result.class_id,
            "status": result.status,
            "paid_amount": str(result.paid_amount),
            "consumed_lessons": result.consumed_lessons,
        },
    }


@router.delete("/{order_no}")
async def soft_delete(
    order_no: str,
    db=Depends(get_database),
    _user=Depends(require_perm("order:cancel")),
):
    result = await update_status_by_order_no(db, order_no, "cancelled")
    if not result:
        raise HTTPException(status_code=404, detail="订单不存在")
    return {"code": 200, "msg": "success"}
