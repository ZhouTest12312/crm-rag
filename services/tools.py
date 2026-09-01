"""
订单工具：优先 MySQL（与 edu-crm-agent 同库）；失败时可再考虑 mock。
"""
from __future__ import annotations

import re
from decimal import Decimal
from config.db_conf import AsyncSessionLocal, run_async
from crud.enrollments import (
    get_detail_order_no,
    update_status_by_order_no,
    get_max_lesson,
    count_enrollments,
    list_enrollments_brief,
    count_by_order_source,
    list_by_student_id,
)
from crud.students import get_student_id, count_students, list_students
from crud.classes import (
    count_classes,
    list_classes_brief,
    list_teachers,
    count_classes_filtered,
)
from crud.crm_finance import (
    list_cash_vouchers,
    list_coupons,
    list_refunds,
    list_work_orders,
    count_work_orders,
    count_coupons,
    count_cash_vouchers,
    count_refunds,
    update_refund_status,
    get_refund_by_no,
)
from crud.work_orders import update_status as update_work_order_status, get_by_work_no
from schemas.student import StudentQuery
from models.work_order import APPLY_TYPE_LABELS, ORDER_SOURCE_LABELS, WO_STATUSES
_ENR_PATTERN = re.compile(r"ENR\d+", re.I)
# 漏写 E：NR20250820005 → ENR20250820005
_NR_TYPO_PATTERN = re.compile(r"NR(202508\d+)", re.I)


def _normalize_order_no(order_no: str | None) -> str | None:
    if not order_no:
        return None
    s = str(order_no).strip().upper()
    m = _ENR_PATTERN.search(s)
    if m:
        return m.group(0)
    m2 = _NR_TYPO_PATTERN.search(s)
    if m2:
        return f"ENR{m2.group(1)}"
    # 没有 ENR/NR 模式时必须返回 None，不能把整句中文当成订单号
    return None


def extract_order_no(text: str) -> str | None:
    return _normalize_order_no(text)


async def _lookup(order_no: str) -> dict:
    order_no = _normalize_order_no(order_no) or ""
    async with AsyncSessionLocal() as db:
        row = await get_detail_order_no(db, order_no)
        if not row:
            return {"ok": False, "error": "订单不存在"}
        student_name = None
        student = await get_student_id(db, row.student_id)
        if student:
            student_name = student.name
        return {
            "ok": True,
            "order_no": row.order_no,
            "status": row.status,
            "consumed_lessons": row.consumed_lessons,
            "total_lessons": row.total_lessons,
            "unit_price": str(row.unit_price),
            "student_id": row.student_id,
            "class_id": row.class_id,
            "paid_amount": str(row.paid_amount),
            "student_name": student_name,
            "order_source": getattr(row, "order_source", None),
            "order_source_label": ORDER_SOURCE_LABELS.get(
                getattr(row, "order_source", "") or "",
                getattr(row, "order_source", None),
            ),
        }


def lookup_order(order_no: str) -> dict:
    if not order_no:
        return {"ok": False, "error": "缺少订单号"}
    return run_async(_lookup(order_no))


async def _cancel(order_no: str) -> dict:
    async with AsyncSessionLocal() as db:
        row = await update_status_by_order_no(db, order_no, "cancelled")
        if not row:
            await db.rollback()
            return {"ok": False, "error": "订单不存在"}
        await db.commit()
        return {"ok": True, "order_no": row.order_no, "status": row.status}


def cancel_order(order_no: str) -> dict:
    if not order_no:
        return {"ok": False, "error": "缺少订单号"}
    return run_async(_cancel(order_no))


async def _max_paid() -> dict:
    async with AsyncSessionLocal() as db:
        row = await get_max_lesson(db)
        if not row:
            return {"ok": False, "error": "暂无报名数据"}
        return {
            "ok": True,
            "order_no": row.order_no,
            "max_paid": str(row.paid_amount),
            "status": row.status,
            "student_id": row.student_id,
            "class_id": row.class_id,
        }


def max_paid() -> dict:
    """同步入口：实付最高的报名订单。"""
    return run_async(_max_paid())


async def _count_orders(status: str | None = None) -> dict:
    async with AsyncSessionLocal() as db:
        total = await count_enrollments(db, status=status or None)
        # 顺带给各状态数量，方便「有多少订单」一次说清
        by_status = {}
        for st in (
            "active",
            "pending_start",
            "completed",
            "refunded",
            "cancelled",
        ):
            by_status[st] = await count_enrollments(db, status=st)
        return {
            "ok": True,
            "total": total if not status else by_status.get(status, total),
            "filter_status": status,
            "by_status": by_status,
            "all_total": sum(by_status.values()),
        }


def count_orders(status: str | None = None) -> dict:
    """统计报名订单数量；可按 status 过滤。"""
    return run_async(_count_orders(status or None))


async def _list_orders(status: str | None = None, limit: int = 20) -> dict:
    async with AsyncSessionLocal() as db:
        rows = await list_enrollments_brief(
            db, status=status or None, limit=min(int(limit or 20), 50)
        )
        items = [
            {
                "order_no": r.order_no,
                "student_id": r.student_id,
                "class_id": r.class_id,
                "status": r.status,
                "paid_amount": str(r.paid_amount),
                "consumed_lessons": r.consumed_lessons,
                "total_lessons": r.total_lessons,
            }
            for r in rows
        ]
        return {"ok": True, "count": len(items), "items": items}


def list_orders(status: str | None = None, limit: int = 20) -> dict:
    """列出报名订单（默认不含 cancelled；传 status 则按状态筛）。"""
    return run_async(_list_orders(status, limit))


async def _lookup_teachers() -> dict:
    async with AsyncSessionLocal() as db:
        rows = await list_teachers(db)
        items = [
            {"teacher_name": name, "class_count": int(cnt)} for name, cnt in rows
        ]
        return {"ok": True, "count": len(items), "items": items}


def lookup_teachers() -> dict:
    """统计/列出主讲老师（来自班级表去重）。"""
    return run_async(_lookup_teachers())


def _normalize_subject(subject: str | None) -> str | None:
    """英语班 → 英语；语文课程 → 语文。"""
    if not subject:
        return None
    s = str(subject).strip()
    for suffix in ("班级", "班次", "课程", "课", "班"):
        if len(s) > len(suffix) and s.endswith(suffix):
            s = s[: -len(suffix)].strip()
            break
    return s or None


def _normalize_teacher_name(name: str | None) -> str | None:
    if not name:
        return None
    s = str(name).strip()
    for suffix in ("老师", "教师", "老师傅"):
        if len(s) > len(suffix) and s.endswith(suffix):
            # 保留「王老师」这类完整称谓也行；去掉后缀便于模糊：王老师→王
            # 但库里存的是「王老师」，所以优先保留原串；仅去掉多余「的班」
            break
    s = s.replace("的班", "").replace("带的班", "").strip()
    return s or None


async def _lookup_classes(
    status: str | None = None,
    subject: str | None = None,
    teacher_name: str | None = None,
) -> dict:
    subject = _normalize_subject(subject)
    teacher_name = _normalize_teacher_name(teacher_name)
    async with AsyncSessionLocal() as db:
        total = await count_classes_filtered(
            db,
            status=status or None,
            subject=subject or None,
            teacher_name=teacher_name or None,
        )
        rows = await list_classes_brief(
            db,
            status=status or None,
            subject=subject or None,
            teacher_name=teacher_name or None,
            limit=50,
        )
        items = [
            {
                "id": r.id,
                "name": r.name,
                "subject": r.subject,
                "teacher_name": r.teacher_name,
                "status": r.status,
                "enrolled_count": r.enrolled_count,
                "max_seats": r.max_seats,
            }
            for r in rows
        ]
        return {
            "ok": True,
            "count": total,
            "filter": {
                "status": status,
                "subject": subject,
                "teacher_name": teacher_name,
            },
            "items": items,
        }


def lookup_classes(
    status: str | None = None,
    subject: str | None = None,
    teacher_name: str | None = None,
) -> dict:
    """统计并列出班级；可按状态/科目/老师过滤。"""
    return run_async(_lookup_classes(status, subject, teacher_name))


async def _count_students() -> dict:
    async with AsyncSessionLocal() as db:
        total = await count_students(db)
        return {"ok": True, "count": total}


def count_students_tool() -> dict:
    """学员总数。"""
    return run_async(_count_students())


async def _lookup_students(name: str | None = None, phone: str | None = None) -> dict:
    async with AsyncSessionLocal() as db:
        query = StudentQuery(
            name=name or None,
            phone=phone or None,
            page=1,
            page_size=20,
        )
        rows, total = await list_students(db, query)
        items = [
            {
                "id": r.id,
                "name": r.name,
                "phone": r.phone,
                "verified": bool(r.verified),
            }
            for r in rows
        ]
        return {"ok": True, "count": total, "items": items}


def lookup_students(name: str | None = None, phone: str | None = None) -> dict:
    """按姓名/手机号查学员。"""
    if not (name or phone):
        return {"ok": False, "error": "请提供姓名或手机号"}
    return run_async(_lookup_students(name, phone))


async def _lookup_student_orders(
    student_id: int | None = None, name: str | None = None
) -> dict:
    async with AsyncSessionLocal() as db:
        sid = _int_or_none(student_id)
        if sid is None and name:
            query = StudentQuery(name=name, page=1, page_size=5)
            students, _ = await list_students(db, query)
            if not students:
                return {"ok": False, "error": f"未找到学员：{name}"}
            if len(students) > 1:
                return {
                    "ok": False,
                    "error": "姓名匹配多人，请改用 student_id",
                    "candidates": [
                        {"id": s.id, "name": s.name, "phone": s.phone}
                        for s in students
                    ],
                }
            sid = students[0].id
        if sid is None:
            return {"ok": False, "error": "请提供 student_id 或 name"}
        student = await get_student_id(db, sid)
        if not student:
            return {"ok": False, "error": "学员不存在"}
        rows = await list_by_student_id(db, sid)
        return {
            "ok": True,
            "student_id": sid,
            "student_name": student.name,
            "count": len(rows),
            "items": [
                {
                    "order_no": r.order_no,
                    "class_id": r.class_id,
                    "status": r.status,
                    "paid_amount": str(r.paid_amount),
                    "order_source": getattr(r, "order_source", None),
                    "order_source_label": ORDER_SOURCE_LABELS.get(
                        getattr(r, "order_source", "") or "",
                        getattr(r, "order_source", None),
                    ),
                }
                for r in rows
            ],
        }


def lookup_student_orders(
    student_id: int | str | None = None, name: str | None = None
) -> dict:
    """查某学员的报名订单。"""
    return run_async(_lookup_student_orders(_int_or_none(student_id), name))


async def _count_orders_by_source() -> dict:
    async with AsyncSessionLocal() as db:
        rows = await count_by_order_source(db)
        items = [
            {
                "order_source": src or "unknown",
                "order_source_label": ORDER_SOURCE_LABELS.get(src or "", src),
                "count": int(cnt),
            }
            for src, cnt in rows
        ]
        return {
            "ok": True,
            "total": sum(i["count"] for i in items),
            "items": items,
        }


def count_orders_by_source() -> dict:
    """按订单来源统计报名单数量。"""
    return run_async(_count_orders_by_source())


async def _count_domain(
    kind: str, status: str | None = None, apply_type: str | None = None
) -> dict:
    async with AsyncSessionLocal() as db:
        if kind == "work_orders":
            n = await count_work_orders(
                db, status=status or None, apply_type=apply_type or None
            )
        elif kind == "coupons":
            n = await count_coupons(db, status=status or None)
        elif kind == "cash_vouchers":
            n = await count_cash_vouchers(db, status=status or None)
        elif kind == "refunds":
            n = await count_refunds(db, status=status or None)
        else:
            return {"ok": False, "error": f"未知类型 {kind}"}
        return {"ok": True, "kind": kind, "status": status, "count": n}


def count_work_orders_tool(
    status: str | None = None, apply_type: str | None = None
) -> dict:
    return run_async(_count_domain("work_orders", status, apply_type))


def count_coupons_tool(status: str | None = None) -> dict:
    return run_async(_count_domain("coupons", status))


def count_cash_vouchers_tool(status: str | None = None) -> dict:
    return run_async(_count_domain("cash_vouchers", status))


def count_refunds_tool(status: str | None = None) -> dict:
    return run_async(_count_domain("refunds", status))


async def _set_work_order_status(
    work_no: str, status: str, remark: str | None = None
) -> dict:
    if status not in WO_STATUSES:
        return {"ok": False, "error": "状态不合法"}
    async with AsyncSessionLocal() as db:
        row = await update_work_order_status(db, work_no, status, remark)
        if not row:
            await db.rollback()
            return {"ok": False, "error": "工单不存在"}
        await db.commit()
        return {
            "ok": True,
            "work_no": row.work_no,
            "status": row.status,
            "apply_type_label": APPLY_TYPE_LABELS.get(row.apply_type, row.apply_type),
        }


def set_work_order_status(
    work_no: str, status: str, remark: str | None = None
) -> dict:
    """写操作：改工单状态（调用方需先 interrupt 确认）。"""
    if not work_no:
        return {"ok": False, "error": "缺少工单号"}
    return run_async(_set_work_order_status(work_no.upper(), status, remark))


async def _mark_refund_paid(refund_no: str) -> dict:
    async with AsyncSessionLocal() as db:
        row = await update_refund_status(db, refund_no, "paid")
        if not row:
            await db.rollback()
            return {"ok": False, "error": "退款单不存在"}
        # 关联报名单标记 refunded
        enr = await get_detail_order_no(db, row.order_no)
        if enr and enr.status not in ("cancelled", "refunded"):
            enr.status = "refunded"
        await db.commit()
        return {
            "ok": True,
            "refund_no": row.refund_no,
            "order_no": row.order_no,
            "amount": str(row.amount),
            "status": row.status,
        }


def mark_refund_paid(refund_no: str) -> dict:
    if not refund_no:
        return {"ok": False, "error": "缺少退款号"}
    return run_async(_mark_refund_paid(refund_no.upper()))


async def _apply_enrollment_refund(order_no: str) -> dict:
    """退班落地：订单 → refunded；若无退款单则跳过建单，只改状态。"""
    order_no = _normalize_order_no(order_no) or ""
    async with AsyncSessionLocal() as db:
        row = await update_status_by_order_no(db, order_no, "refunded")
        if not row:
            await db.rollback()
            return {"ok": False, "error": "订单不存在"}
        await db.commit()
        return {"ok": True, "order_no": row.order_no, "status": row.status}


def apply_enrollment_refund(order_no: str) -> dict:
    if not order_no:
        return {"ok": False, "error": "缺少订单号"}
    return run_async(_apply_enrollment_refund(order_no))


async def _crm_overview() -> dict:
    """一览：订单/班级/老师/学员/工单数量，顺口问「有多少」时用。"""
    async with AsyncSessionLocal() as db:
        orders = await count_enrollments(db)
        classes = await count_classes(db)
        teachers = len(await list_teachers(db))
        students = await count_students(db)
        work_orders = await count_work_orders(db)
        coupons = await count_coupons(db)
        vouchers = await count_cash_vouchers(db)
        refunds = await count_refunds(db)
        return {
            "ok": True,
            "orders": orders,
            "classes": classes,
            "teachers": teachers,
            "students": students,
            "work_orders": work_orders,
            "coupons": coupons,
            "cash_vouchers": vouchers,
            "refunds": refunds,
        }


def crm_overview() -> dict:
    return run_async(_crm_overview())


def estimate_refund(order_no: str) -> dict:
    """退班试算：字段已齐，具体公式由调用方/你自行实现。"""
    row = lookup_order(order_no)
    if not row.get("ok"):
        return row
    if row["status"] == "cancelled":
        return {"ok": False, "error": "订单已取消，无法试算"}
    if row['consumed_lessons'] == 0:
        refund = Decimal(row["paid_amount"])
    else:
        refund = (
            Decimal(row["paid_amount"])
            - Decimal(int(row["consumed_lessons"]) * Decimal(row["unit_price"]))
            + Decimal(str(float(row["paid_amount"]) * 0.05))
        )
    return {
        "ok": True,
        "order_no": row["order_no"],
        "status": row["status"],
        "paid_amount": row["paid_amount"],
        "consumed_lessons": row["consumed_lessons"],
        "total_lessons": row["total_lessons"],
        "refund_amount": str(refund),
        "unit_price": row["unit_price"],
    }


# ---------- 工单域：工单 / 优惠券 / 现金券 / 退款单 ----------


def _int_or_none(v):
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


async def _lookup_work_orders(
    status: str | None = None,
    apply_type: str | None = None,
    order_no: str | None = None,
    student_id: int | None = None,
) -> dict:
    async with AsyncSessionLocal() as db:
        rows = await list_work_orders(
            db,
            status=status or None,
            apply_type=apply_type or None,
            order_no=_normalize_order_no(order_no) if order_no else None,
            student_id=_int_or_none(student_id),
        )
        items = [
            {
                "work_no": r.work_no,
                "apply_type": r.apply_type,
                "apply_type_label": APPLY_TYPE_LABELS.get(r.apply_type, r.apply_type),
                "order_no": r.order_no,
                "student_id": r.student_id,
                "from_class_id": r.from_class_id,
                "to_class_id": r.to_class_id,
                "order_source": r.order_source,
                "order_source_label": ORDER_SOURCE_LABELS.get(
                    r.order_source, r.order_source
                ),
                "status": r.status,
                "amount": str(r.amount) if r.amount is not None else None,
                "reason": r.reason,
            }
            for r in rows
        ]
        return {"ok": True, "count": len(items), "items": items}


def lookup_work_orders(
    status: str | None = None,
    apply_type: str | None = None,
    order_no: str | None = None,
    student_id: int | str | None = None,
) -> dict:
    """查工单：可按状态/类型/订单号/学员过滤。"""
    return run_async(
        _lookup_work_orders(status, apply_type, order_no, _int_or_none(student_id))
    )


async def _lookup_coupons(
    student_id: int | None = None,
    status: str | None = None,
    order_no: str | None = None,
) -> dict:
    async with AsyncSessionLocal() as db:
        rows = await list_coupons(
            db,
            student_id=_int_or_none(student_id),
            status=status or None,
            order_no=_normalize_order_no(order_no) if order_no else None,
        )
        items = [
            {
                "coupon_no": r.coupon_no,
                "student_id": r.student_id,
                "name": r.name,
                "amount": str(r.amount),
                "status": r.status,
                "order_no": r.order_no,
                "order_source": r.order_source,
                "order_source_label": ORDER_SOURCE_LABELS.get(
                    r.order_source, r.order_source
                ),
            }
            for r in rows
        ]
        return {"ok": True, "count": len(items), "items": items}


def lookup_coupons(
    student_id: int | str | None = None,
    status: str | None = None,
    order_no: str | None = None,
) -> dict:
    return run_async(
        _lookup_coupons(_int_or_none(student_id), status, order_no)
    )


async def _lookup_cash_vouchers(
    student_id: int | None = None, status: str | None = None
) -> dict:
    async with AsyncSessionLocal() as db:
        rows = await list_cash_vouchers(
            db, student_id=_int_or_none(student_id), status=status or None
        )
        items = [
            {
                "voucher_no": r.voucher_no,
                "student_id": r.student_id,
                "face_value": str(r.face_value),
                "balance": str(r.balance),
                "status": r.status,
                "order_no": r.order_no,
            }
            for r in rows
        ]
        return {"ok": True, "count": len(items), "items": items}


def lookup_cash_vouchers(
    student_id: int | str | None = None, status: str | None = None
) -> dict:
    return run_async(_lookup_cash_vouchers(_int_or_none(student_id), status))


async def _lookup_refunds(
    order_no: str | None = None,
    student_id: int | None = None,
    status: str | None = None,
    refund_no: str | None = None,
) -> dict:
    async with AsyncSessionLocal() as db:
        rows = await list_refunds(
            db,
            order_no=_normalize_order_no(order_no) if order_no else None,
            student_id=_int_or_none(student_id),
            status=status or None,
            refund_no=(refund_no or "").upper() or None,
        )
        items = [
            {
                "refund_no": r.refund_no,
                "order_no": r.order_no,
                "student_id": r.student_id,
                "work_no": r.work_no,
                "amount": str(r.amount),
                "status": r.status,
                "channel": r.channel,
                "reason": r.reason,
            }
            for r in rows
        ]
        return {"ok": True, "count": len(items), "items": items}


def lookup_refunds(
    order_no: str | None = None,
    student_id: int | str | None = None,
    status: str | None = None,
    refund_no: str | None = None,
) -> dict:
    return run_async(
        _lookup_refunds(
            order_no, _int_or_none(student_id), status, refund_no
        )
    )
