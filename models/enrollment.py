"""报名订单表。对照：edu-crm-agent/models/enrollment.py（表结构须一致）"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Enrollment(Base):
    __tablename__ = "enrollment"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    order_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("student.id"), nullable=False
    )
    class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("crm_class.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="active")
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    total_lessons: Mapped[int] = mapped_column(Integer, default=30)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    consumed_lessons: Mapped[int] = mapped_column(Integer, default=0)
    free_transfer_used: Mapped[int] = mapped_column(Integer, default=0)
    order_source: Mapped[str] = mapped_column(
        String(32), default="offline", comment="订单来源"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )
