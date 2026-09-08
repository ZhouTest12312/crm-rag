"""班级课次表：每班多节课的日期与状态。"""
from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class ClassLesson(Base):
    __tablename__ = "class_lesson"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    lesson_no: Mapped[int] = mapped_column(Integer, nullable=False, comment="第几课")
    lesson_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default="scheduled",
        comment="scheduled/done/cancelled/rescheduled",
    )
    classroom: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
