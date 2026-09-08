"""老师调课记录。"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


# 调课原因分类（与制度对齐）
CHANGE_REASONS = (
    "teacher_leave",     # 老师请假
    "teacher_conflict",  # 老师档期冲突
    "force_majeure",     # 不可抗力（台风等）
    "classroom",         # 教室/场地
    "other",
)

CHANGE_REASON_LABELS = {
    "teacher_leave": "老师请假",
    "teacher_conflict": "老师档期冲突",
    "force_majeure": "不可抗力",
    "classroom": "教室场地调整",
    "other": "其他",
}


class ScheduleChange(Base):
    __tablename__ = "schedule_change"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    change_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    class_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    lesson_no: Mapped[int] = mapped_column(Integer, nullable=False)
    teacher_name: Mapped[str] = mapped_column(String(50), nullable=False)
    old_date: Mapped[date] = mapped_column(Date, nullable=False)
    new_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason_code: Mapped[str] = mapped_column(
        String(32), default="teacher_leave", comment="原因码"
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False, comment="原因说明")
    notify_hours: Mapped[int] = mapped_column(
        Integer, default=24, comment="提前通知小时数"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="notified", comment="draft/notified/done/cancelled"
    )
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
