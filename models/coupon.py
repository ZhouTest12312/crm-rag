"""优惠券（本地演示表）。"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Coupon(Base):
    __tablename__ = "coupon"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coupon_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="券名称")
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="面额")
    status: Mapped[str] = mapped_column(
        String(20), default="unused", comment="unused/used/expired"
    )
    order_no: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, comment="核销关联订单"
    )
    order_source: Mapped[str] = mapped_column(
        String(32), default="offline", comment="发券来源"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
