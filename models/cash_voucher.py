"""现金券（本地演示表）。"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class CashVoucher(Base):
    __tablename__ = "cash_voucher"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    voucher_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    face_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="面值"
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="剩余可用"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="active", comment="active/used_up/frozen/expired"
    )
    order_no: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, comment="最近使用订单"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
