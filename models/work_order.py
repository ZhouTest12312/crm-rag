"""教务工单（仿 CRM 资源申请）。本地库，与线上无关。"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


# 申请类型（与制度文件用语对齐）
APPLY_TYPES = (
    "change_class",      # 换班
    "transfer_class",    # 转班
    "withdraw",          # 退班
    "settle_transfer",   # 结转换班
    "settle_refund",     # 结转退班
)

APPLY_TYPE_LABELS = {
    "change_class": "换班",
    "transfer_class": "转班",
    "withdraw": "退班",
    "settle_transfer": "结转换班",
    "settle_refund": "结转退班",
}

# 工单状态
WO_STATUSES = (
    "pending",     # 待审核
    "approved",    # 已通过
    "rejected",    # 已驳回
    "completed",   # 已完成（财务/教务落地）
    "cancelled",   # 已撤销
)

# 订单来源（仿 CRM 下拉）
ORDER_SOURCES = (
    "offline",       # 线下门店
    "douyin",        # 抖音
    "referral",      # 老生转介绍
    "renewal",       # 老生续报
    "phone",         # 电话咨询
    "other",         # 其他
)

ORDER_SOURCE_LABELS = {
    "offline": "线下门店",
    "douyin": "抖音",
    "referral": "老生转介绍",
    "renewal": "老生续报",
    "phone": "电话咨询",
    "other": "其他",
}


class WorkOrder(Base):
    __tablename__ = "work_order"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_no: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, comment="工单号 WO…"
    )
    apply_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="换班/转班/退班/结转换/结转退"
    )
    order_no: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="关联报名订单号"
    )
    student_id: Mapped[int] = mapped_column(Integer, nullable=False)
    from_class_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="原班级"
    )
    to_class_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="目标班级"
    )
    order_source: Mapped[str] = mapped_column(
        String(32), default="offline", comment="订单来源"
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="工单状态")
    reason: Mapped[Optional[str]] = mapped_column(String(255), comment="申请原因")
    amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True, comment="试算金额：退款或补差"
    )
    fee_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True, comment="手续费"
    )
    applicant: Mapped[str] = mapped_column(
        String(50), default="顾问", comment="提交人"
    )
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="审核备注")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
