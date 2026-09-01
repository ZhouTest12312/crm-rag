"""工单 API：列表 / 详情 / 新建 / 改状态。仿 CRM 资源申请，数据仅本地库。"""
from fastapi import APIRouter, Depends, HTTPException

from config.db_conf import get_database
from crud.classes import list_classes_detail
from crud.enrollments import get_detail_order_no
from crud.students import get_student_id
from crud.work_orders import (
    create_work_order,
    get_by_work_no,
    search_work_orders,
    update_status,
)
from models.work_order import (
    APPLY_TYPE_LABELS,
    APPLY_TYPES,
    ORDER_SOURCE_LABELS,
    ORDER_SOURCES,
    WO_STATUSES,
)
from schemas.work_order import WorkOrderCreate, WorkOrderQuery, WorkOrderStatusUpdate
from utils.auth import require_perm

router = APIRouter(prefix="/api/work-orders", tags=["work-orders"])


def _row_dict(r):
    return {
        "id": r.id,
        "work_no": r.work_no,
        "apply_type": r.apply_type,
        "apply_type_label": APPLY_TYPE_LABELS.get(r.apply_type, r.apply_type),
        "order_no": r.order_no,
        "student_id": r.student_id,
        "from_class_id": r.from_class_id,
        "to_class_id": r.to_class_id,
        "order_source": r.order_source,
        "order_source_label": ORDER_SOURCE_LABELS.get(r.order_source, r.order_source),
        "status": r.status,
        "reason": r.reason,
        "amount": str(r.amount) if r.amount is not None else None,
        "fee_amount": str(r.fee_amount) if r.fee_amount is not None else None,
        "applicant": r.applicant,
        "remark": r.remark,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


@router.get("/meta")
async def work_order_meta():
    """前端下拉：申请类型 / 订单来源 / 状态。"""
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "apply_types": [
                {"value": k, "label": APPLY_TYPE_LABELS[k]} for k in APPLY_TYPES
            ],
            "order_sources": [
                {"value": k, "label": ORDER_SOURCE_LABELS[k]} for k in ORDER_SOURCES
            ],
            "statuses": list(WO_STATUSES),
        },
    }


@router.get("/list")
async def list_work_orders(
    query: WorkOrderQuery = Depends(),
    db=Depends(get_database),
):
    rows, total = await search_work_orders(db, query)
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "total": total,
            "page": query.page,
            "page_size": query.page_size,
            "items": [_row_dict(r) for r in rows],
        },
    }


@router.get("/{work_no}")
async def get_work_order(work_no: str, db=Depends(get_database)):
    row = await get_by_work_no(db, work_no)
    if not row:
        raise HTTPException(status_code=404, detail="工单不存在")
    return {"code": 200, "msg": "success", "data": _row_dict(row)}


@router.post("/add")
async def add_work_order(
    body: WorkOrderCreate,
    db=Depends(get_database),
    _user=Depends(require_perm("order:write")),
):
    if body.apply_type not in APPLY_TYPES:
        raise HTTPException(status_code=400, detail="申请类型不合法")
    if body.order_source not in ORDER_SOURCES:
        raise HTTPException(status_code=400, detail="订单来源不合法")
    # 换班/转班/结转换必须有目标班；退班/结转退可不填
    need_to = body.apply_type in ("change_class", "transfer_class", "settle_transfer")
    if need_to and not body.to_class_id:
        raise HTTPException(status_code=400, detail="该申请类型必须填写目标班级")
    if body.apply_type in ("withdraw", "settle_refund") and body.to_class_id:
        raise HTTPException(status_code=400, detail="退班类工单不应填写目标班级")

    student = await get_student_id(db, body.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学员不存在")
    from_cls = await list_classes_detail(db, body.from_class_id)
    if not from_cls:
        raise HTTPException(status_code=404, detail="原班级不存在")
    if body.to_class_id is not None:
        to_cls = await list_classes_detail(db, body.to_class_id)
        if not to_cls:
            raise HTTPException(status_code=404, detail="目标班级不存在")
    enr = await get_detail_order_no(db, body.order_no)
    if not enr:
        raise HTTPException(status_code=404, detail="关联报名订单不存在")

    row = await create_work_order(db, body)
    return {"code": 200, "msg": "success", "data": _row_dict(row)}


@router.patch("/{work_no}")
async def patch_work_order_status(
    work_no: str,
    body: WorkOrderStatusUpdate,
    db=Depends(get_database),
    _user=Depends(require_perm("order:write")),
):
    if body.status not in WO_STATUSES:
        raise HTTPException(status_code=400, detail="状态不合法")
    row = await update_status(db, work_no, body.status, body.remark)
    if not row:
        raise HTTPException(status_code=404, detail="工单不存在")
    return {"code": 200, "msg": "success", "data": _row_dict(row)}
