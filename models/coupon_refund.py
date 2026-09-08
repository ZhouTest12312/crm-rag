"""退款拆分：现金应退 vs 优惠券不退部分（结转退班等）。"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class CouponRefund(Base):
    __tablename__ = "coupon_refund"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    refund_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    order_no: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    work_no: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    cash_refund: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="现金应退"
    )
    coupon_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=0, comment="用券面额（不退）"
    )
    coupon_refundable: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=0, comment="券可退部分，结转退班为0"
    )
    total_refund: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="实际退款=现金"
    )
    policy: Mapped[str] = mapped_column(
        String(64),
        default="settle_no_coupon",
        comment="settle_no_coupon / withdraw_cash_only / full",
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending", comment="pending/approved/paid"
    )
    remark: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
