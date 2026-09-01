from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class CrmClass(Base):
    __tablename__ = "crm_class"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="班级名称")
    subject: Mapped[str] = mapped_column(String(50), nullable=False, comment="科目")
    teacher_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="主讲老师"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending_start", comment="待开班/在读/已结课/停办"
    )
    max_seats: Mapped[int] = mapped_column(Integer, default=30, comment="满员人数")
    enrolled_count: Mapped[int] = mapped_column(Integer, default=0, comment="已占座")
    start_date: Mapped[Optional[date]] = mapped_column(Date, comment="首课日期")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="更新时间"
    )
