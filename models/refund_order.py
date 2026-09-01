"""退款单（本地演示表）。"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class RefundOrder(Base):
    __tablename__ = "refund_order"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    refund_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    order_no: Mapped[str] = mapped_column(String(32), nullable=False, comment="报名订单")
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    work_no: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, comment="关联工单"
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", comment="pending/approved/paid/rejected"
    )
    channel: Mapped[str] = mapped_column(
        String(32), default="original", comment="original/cash/transfer"
    )
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
