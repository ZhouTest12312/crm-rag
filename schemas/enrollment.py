from decimal import Decimal

from pydantic import BaseModel, Field


class EnrollmentQuery(BaseModel):
    id: int | None = None
    order_no: str | None = None
    student_id: int | None = None
    class_id: int | None = None
    status: str | None = None
    paid_amount: float | None = None
    consumed_lessons: int | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)


class EnrollmentStatusUpdate(BaseModel):
    status: str = Field(
        ..., min_length=1, description="active / pending_start / completed / refunded"
    )


class EnrollmentCreate(BaseModel):
    order_no: str = Field(..., min_length=1)
    student_id: int
    class_id: int
    paid_amount: Decimal
    total_lessons: int = Field(30, ge=1, description="购课总课次")
    unit_price: Decimal | None = Field(
        None, description="单课次原价；不传则按 paid_amount / total_lessons 推算"
    )
    status: str = "pending_start"
