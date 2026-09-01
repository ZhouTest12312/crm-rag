"""工单请求/响应模型。"""
from decimal import Decimal

from pydantic import BaseModel, Field


class WorkOrderQuery(BaseModel):
    work_no: str | None = None
    apply_type: str | None = None
    order_no: str | None = None
    student_id: int | None = None
    status: str | None = None
    order_source: str | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)


class WorkOrderCreate(BaseModel):
    apply_type: str = Field(..., description="change_class / transfer_class / withdraw / settle_transfer / settle_refund")
    order_no: str = Field(..., min_length=1)
    student_id: int
    from_class_id: int
    to_class_id: int | None = None
    order_source: str = "offline"
    reason: str | None = None
    amount: Decimal | None = None
    fee_amount: Decimal | None = None
    applicant: str = "顾问"


class WorkOrderStatusUpdate(BaseModel):
    status: str = Field(..., description="pending / approved / rejected / completed / cancelled")
    remark: str | None = None
