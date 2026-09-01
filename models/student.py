from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Student(Base):
    __tablename__ = "student"
    __table_args__ = (Index("phone_UNIQUE", "phone", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="姓名")
    phone: Mapped[str] = mapped_column(String(50), nullable=False, comment="手机号")
    guardian_phone: Mapped[str] = mapped_column(String(20), comment="监护人手机")
    verified: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否实名")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
