"""扩场景：加列 + 新表 + 各表约 20 条种子（幂等）。

用法（项目根）：
  $env:PYTHONPATH="."
  .venv\\Scripts\\python.exe scripts\\migrate_expand_scenarios.py
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import text

from config.db_conf import AsyncSessionLocal
from models.class_lesson import ClassLesson
from models.coupon import Coupon
from models.coupon_refund import CouponRefund
from models.crm_class import CrmClass
from models.enrollment import Enrollment
from models.installment import Installment
from models.refund_order import RefundOrder
from models.schedule_change import ScheduleChange
from models.student import Student
from models.work_order import WorkOrder

NOW = datetime(2026, 9, 8, 10, 0, 0)

CREATE_LESSON = """
CREATE TABLE IF NOT EXISTS class_lesson (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  class_id INT NOT NULL,
  lesson_no INT NOT NULL,
  lesson_date DATE NOT NULL,
  start_time TIME NULL,
  end_time TIME NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
  classroom VARCHAR(50) NULL,
  created_at DATETIME NULL,
  updated_at DATETIME NULL,
  KEY idx_lesson_class (class_id),
  UNIQUE KEY uk_class_lesson (class_id, lesson_no)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

CREATE_CHANGE = """
CREATE TABLE IF NOT EXISTS schedule_change (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  change_no VARCHAR(32) NOT NULL,
  class_id INT NOT NULL,
  lesson_no INT NOT NULL,
  teacher_name VARCHAR(50) NOT NULL,
  old_date DATE NOT NULL,
  new_date DATE NOT NULL,
  reason_code VARCHAR(32) NOT NULL DEFAULT 'teacher_leave',
  reason VARCHAR(255) NOT NULL,
  notify_hours INT NOT NULL DEFAULT 24,
  status VARCHAR(20) NOT NULL DEFAULT 'notified',
  remark TEXT NULL,
  created_at DATETIME NULL,
  updated_at DATETIME NULL,
  UNIQUE KEY uk_change_no (change_no),
  KEY idx_change_class (class_id)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

CREATE_INSTALL = """
CREATE TABLE IF NOT EXISTS installment (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  order_no VARCHAR(32) NOT NULL,
  student_id INT NOT NULL,
  period_no INT NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  due_date DATE NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  paid_at DATETIME NULL,
  created_at DATETIME NULL,
  updated_at DATETIME NULL,
  KEY idx_inst_order (order_no)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

CREATE_CRF = """
CREATE TABLE IF NOT EXISTS coupon_refund (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  refund_no VARCHAR(32) NOT NULL,
  order_no VARCHAR(32) NOT NULL,
  student_id INT NOT NULL,
  work_no VARCHAR(32) NULL,
  cash_refund DECIMAL(10,2) NOT NULL,
  coupon_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
  coupon_refundable DECIMAL(10,2) NOT NULL DEFAULT 0,
  total_refund DECIMAL(10,2) NOT NULL,
  policy VARCHAR(64) NOT NULL DEFAULT 'settle_no_coupon',
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  remark VARCHAR(255) NULL,
  created_at DATETIME NULL,
  updated_at DATETIME NULL,
  UNIQUE KEY uk_crf_no (refund_no),
  KEY idx_crf_order (order_no)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

STUDENT_NAMES = [
    "周小北", "吴小南", "郑小东", "王小西", "冯小雨",
    "陈小雪", "褚小风", "卫小阳", "蒋小晨", "沈小夜",
    "韩小秋", "杨小冬", "朱小夏", "秦小春", "尤小岚",
    "许小桐", "何小荷", "吕小舟", "施小桥", "张小帆",
]

CLASS_SPECS = [
    # id 由自增；用 name 幂等
    ("秋季初二数学提高A班", "数学", "王老师", "pending_start", 12, 3, date(2026, 10, 12), date(2027, 1, 18), "周日", "09:00-10:30", "301"),
    ("秋季初二数学提高B班", "数学", "王老师", "active", 16, 16, date(2026, 8, 2), date(2026, 12, 20), "周六", "09:00-10:30", "302"),
    ("秋季初三英语冲刺班", "英语", "陈老师", "active", 20, 14, date(2026, 7, 12), date(2026, 11, 29), "周六", "14:00-15:30", "401"),
    ("暑期初一语文阅读班", "语文", "赵老师", "completed", 18, 18, date(2026, 7, 1), date(2026, 8, 20), "周五", "19:00-20:30", "201"),
    ("秋季初二物理实验班", "物理", "刘老师", "active", 15, 8, date(2026, 8, 16), date(2026, 12, 13), "周日", "15:00-16:30", "501"),
    ("待开初三数学培优班", "数学", "李老师", "pending_start", 20, 6, date(2026, 10, 19), date(2027, 1, 25), "周六", "16:00-17:30", "303"),
    ("满员初二英语听说班", "英语", "陈老师", "active", 12, 12, date(2026, 8, 9), date(2026, 12, 6), "周日", "10:00-11:30", "402"),
    ("停办初一化学启蒙班", "化学", "刘老师", "closed", 10, 2, date(2026, 6, 7), date(2026, 8, 30), "周六", "19:00-20:30", "502"),
    ("秋季初二语文作文班", "语文", "赵老师", "active", 16, 9, date(2026, 8, 23), date(2026, 12, 27), "周日", "14:00-15:30", "202"),
    ("秋季初三物理竞赛班", "物理", "李老师", "active", 10, 7, date(2026, 8, 5), date(2026, 12, 16), "周三", "19:00-20:30", "503"),
    ("秋季初一数学基础班", "数学", "王老师", "pending_start", 24, 5, date(2026, 10, 25), date(2027, 2, 7), "周六", "09:00-10:30", "304"),
    ("秋季初二化学同步班", "化学", "刘老师", "active", 14, 10, date(2026, 8, 8), date(2026, 12, 12), "周六", "15:00-16:30", "504"),
    ("线上初三英语语法班", "英语", "陈老师", "active", 30, 18, date(2026, 8, 3), date(2026, 12, 21), "周二", "19:00-20:00", "线上A"),
    ("秋季初一语文启蒙班", "语文", "赵老师", "pending_start", 20, 4, date(2026, 11, 1), date(2027, 2, 14), "周日", "09:00-10:30", "203"),
    ("秋季初三数学压轴班", "数学", "李老师", "active", 12, 11, date(2026, 7, 26), date(2026, 11, 22), "周日", "16:00-17:30", "305"),
    ("秋季初二生物会考班", "生物", "冯老师", "active", 16, 8, date(2026, 8, 15), date(2026, 12, 19), "周六", "10:00-11:30", "601"),
    ("结课初二英语专项班", "英语", "陈老师", "completed", 16, 16, date(2026, 3, 8), date(2026, 7, 12), "周六", "14:00-15:30", "403"),
    ("秋季初一物理入门班", "物理", "刘老师", "pending_start", 18, 3, date(2026, 10, 18), date(2027, 1, 31), "周日", "15:00-16:30", "505"),
    ("秋季初三语文作文班", "语文", "赵老师", "active", 14, 9, date(2026, 8, 1), date(2026, 12, 5), "周五", "19:00-20:30", "204"),
    ("调课演示初二数学晚班", "数学", "王老师", "active", 16, 10, date(2026, 8, 10), date(2026, 12, 14), "周一", "19:00-20:30", "306"),
]


async def _col_exists(db, table: str, column: str) -> bool:
    n = (
        await db.execute(
            text(
                """
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = :t AND COLUMN_NAME = :c
                """
            ),
            {"t": table, "c": column},
        )
    ).scalar_one()
    return n > 0


async def _add_column(db, table: str, column: str, ddl: str) -> None:
    if await _col_exists(db, table, column):
        print(f"skip column {table}.{column}")
        return
    await db.execute(text(f"ALTER TABLE `{table}` ADD COLUMN {ddl}"))
    print(f"added {table}.{column}")


async def _exists_order(db, order_no: str) -> bool:
    n = (
        await db.execute(
            text("SELECT COUNT(*) FROM enrollment WHERE order_no = :o"),
            {"o": order_no},
        )
    ).scalar_one()
    return n > 0


async def _class_id_by_name(db, name: str) -> int | None:
    row = (
        await db.execute(
            text("SELECT id FROM crm_class WHERE name = :n LIMIT 1"),
            {"n": name},
        )
    ).first()
    return int(row[0]) if row else None


async def _student_id_by_phone(db, phone: str) -> int | None:
    row = (
        await db.execute(
            text("SELECT id FROM student WHERE phone = :p LIMIT 1"),
            {"p": phone},
        )
    ).first()
    return int(row[0]) if row else None


async def migrate_schema() -> None:
    async with AsyncSessionLocal() as db:
        await _add_column(db, "crm_class", "end_date", "end_date DATE NULL COMMENT '结课日'")
        await _add_column(db, "crm_class", "weekday", "weekday VARCHAR(20) NULL")
        await _add_column(db, "crm_class", "time_slot", "time_slot VARCHAR(40) NULL")
        await _add_column(db, "crm_class", "classroom", "classroom VARCHAR(50) NULL")
        await _add_column(
            db,
            "enrollment",
            "coupon_amount",
            "coupon_amount DECIMAL(10,2) NOT NULL DEFAULT 0",
        )
        await _add_column(
            db,
            "enrollment",
            "has_unpaid_installment",
            "has_unpaid_installment INT NOT NULL DEFAULT 0",
        )
        await db.execute(text(CREATE_LESSON))
        await db.execute(text(CREATE_CHANGE))
        await db.execute(text(CREATE_INSTALL))
        await db.execute(text(CREATE_CRF))
        await db.commit()
        print("schema ready")


def _lessons_for(class_id: int, start: date, n: int, weekday_offset: int, classroom: str):
    rows = []
    d = start
    for i in range(1, n + 1):
        status = "done" if d < date(2026, 9, 8) else "scheduled"
        if i == n and start < date(2026, 8, 1):
            status = "done"
        rows.append(
            ClassLesson(
                class_id=class_id,
                lesson_no=i,
                lesson_date=d,
                start_time=time(9, 0) if i % 2 else time(14, 0),
                end_time=time(10, 30) if i % 2 else time(15, 30),
                status=status,
                classroom=classroom,
                updated_at=NOW,
            )
        )
        d = d + timedelta(days=7)
    return rows


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        if await _exists_order(db, "ENR20250921C01"):
            print("skip seed: ENR20250921C01 already exists")
            return

        # students 20
        students = []
        for i, name in enumerate(STUDENT_NAMES, start=1):
            phone = f"1390001{i:04d}"
            if await _student_id_by_phone(db, phone):
                continue
            students.append(
                Student(
                    name=name,
                    phone=phone,
                    guardian_phone=f"1380001{i:04d}",
                    verified=True,
                    updated_at=NOW,
                )
            )
        if students:
            db.add_all(students)
            await db.flush()
            print(f"seeded students {len(students)}")

        # classes 20
        new_classes = []
        for spec in CLASS_SPECS:
            name = spec[0]
            if await _class_id_by_name(db, name):
                continue
            new_classes.append(
                CrmClass(
                    name=spec[0],
                    subject=spec[1],
                    teacher_name=spec[2],
                    status=spec[3],
                    max_seats=spec[4],
                    enrolled_count=spec[5],
                    start_date=spec[6],
                    end_date=spec[7],
                    weekday=spec[8],
                    time_slot=spec[9],
                    classroom=spec[10],
                    updated_at=NOW,
                )
            )
        if new_classes:
            db.add_all(new_classes)
            await db.flush()
            print(f"seeded classes {len(new_classes)}")

        name_to_id = {}
        for spec in CLASS_SPECS:
            cid = await _class_id_by_name(db, spec[0])
            name_to_id[spec[0]] = cid

        phones = [f"1390001{i:04d}" for i in range(1, 21)]
        stu_ids = []
        for p in phones:
            sid = await _student_id_by_phone(db, p)
            stu_ids.append(sid)

        # 20 enrollments — 场景编号 C01-C20
        enroll_specs = [
            ("ENR20250921C01", 0, name_to_id["秋季初二数学提高A班"], "pending_start", "3600", 16, "225.00", 0, 0, "0", 0, "offline"),
            ("ENR20250921C02", 1, name_to_id["秋季初二数学提高B班"], "active", "3500", 16, "218.75", 4, 0, "100.00", 0, "douyin"),
            ("ENR20250921C03", 2, name_to_id["秋季初三英语冲刺班"], "active", "4200", 20, "210.00", 15, 1, "0", 0, "offline"),
            ("ENR20250921C04", 3, name_to_id["暑期初一语文阅读班"], "completed", "2800", 16, "175.00", 16, 0, "80.00", 0, "renewal"),
            ("ENR20250921C05", 4, name_to_id["秋季初二物理实验班"], "active", "3900", 16, "243.75", 3, 0, "0", 0, "referral"),
            ("ENR20250921C06", 5, name_to_id["待开初三数学培优班"], "pending_start", "4800", 20, "240.00", 0, 0, "0", 1, "offline"),
            ("ENR20250921C07", 6, name_to_id["满员初二英语听说班"], "active", "3600", 16, "225.00", 5, 1, "50.00", 0, "phone"),
            ("ENR20250921C08", 3, name_to_id["结课初二英语专项班"], "completed", "3200", 16, "200.00", 8, 0, "200.00", 0, "renewal"),
            ("ENR20250921C09", 7, name_to_id["停办初一化学启蒙班"], "active", "2600", 12, "216.67", 4, 0, "0", 0, "offline"),
            ("ENR20250921C10", 8, name_to_id["秋季初二语文作文班"], "active", "3400", 16, "212.50", 2, 0, "0", 0, "douyin"),
            ("ENR20250921C11", 9, name_to_id["秋季初三物理竞赛班"], "active", "5100", 16, "318.75", 6, 0, "0", 0, "offline"),
            ("ENR20250921C12", 10, name_to_id["秋季初一数学基础班"], "pending_start", "3000", 16, "187.50", 0, 0, "0", 0, "referral"),
            ("ENR20250921C13", 11, name_to_id["秋季初二化学同步班"], "active", "3700", 16, "231.25", 7, 0, "60.00", 0, "offline"),
            ("ENR20250921C14", 12, name_to_id["线上初三英语语法班"], "active", "2800", 20, "140.00", 8, 0, "0", 0, "douyin"),
            ("ENR20250921C15", 13, name_to_id["秋季初一语文启蒙班"], "pending_start", "2600", 16, "162.50", 0, 0, "0", 0, "phone"),
            ("ENR20250921C16", 14, name_to_id["秋季初三数学压轴班"], "active", "5600", 16, "350.00", 12, 1, "0", 0, "offline"),
            ("ENR20250921C17", 15, name_to_id["秋季初二生物会考班"], "active", "3100", 16, "193.75", 3, 0, "0", 0, "renewal"),
            ("ENR20250921C18", 16, name_to_id["结课初二英语专项班"], "refunded", "3200", 16, "200.00", 10, 0, "0", 0, "offline"),
            ("ENR20250921C19", 17, name_to_id["秋季初一物理入门班"], "pending_start", "2900", 16, "181.25", 0, 0, "0", 0, "offline"),
            ("ENR20250921C20", 19, name_to_id["调课演示初二数学晚班"], "active", "3600", 16, "225.00", 5, 0, "0", 0, "offline"),
        ]
        enrolls = []
        for spec in enroll_specs:
            sid = stu_ids[spec[1]]
            enrolls.append(
                Enrollment(
                    order_no=spec[0],
                    student_id=sid,
                    class_id=spec[2],
                    status=spec[3],
                    paid_amount=Decimal(spec[4]),
                    total_lessons=spec[5],
                    unit_price=Decimal(spec[6]),
                    consumed_lessons=spec[7],
                    free_transfer_used=spec[8],
                    coupon_amount=Decimal(spec[9]),
                    has_unpaid_installment=spec[10],
                    order_source=spec[11],
                    updated_at=NOW,
                )
            )
        db.add_all(enrolls)
        await db.flush()
        print(f"seeded enrollments {len(enrolls)}")

        # lessons: 每班 8 节，约 160 行（课表要能查下次课）
        lessons = []
        for spec in CLASS_SPECS:
            cid = name_to_id[spec[0]]
            lessons.extend(_lessons_for(cid, spec[6], 8, 0, spec[10]))
        db.add_all(lessons)
        print(f"seeded lessons {len(lessons)}")

        # 20 条调课
        demo_cls = name_to_id["调课演示初二数学晚班"]
        math_b = name_to_id["秋季初二数学提高B班"]
        eng = name_to_id["秋季初三英语冲刺班"]
        phy = name_to_id["秋季初二物理实验班"]
        reasons = [
            ("teacher_leave", "老师家中有事请假"),
            ("teacher_conflict", "与区教研活动撞档"),
            ("force_majeure", "台风停课顺延"),
            ("classroom", "原教室维修改场地"),
            ("other", "校历调整"),
        ]
        changes = []
        for i in range(20):
            cls = [demo_cls, math_b, eng, phy][i % 4]
            code, label = reasons[i % 5]
            old = date(2026, 9, 8) + timedelta(days=(i % 7) * 7)
            changes.append(
                ScheduleChange(
                    change_no=f"SCH20250921{i + 1:03d}",
                    class_id=cls,
                    lesson_no=(i % 8) + 1,
                    teacher_name=["王老师", "陈老师", "刘老师"][i % 3],
                    old_date=old,
                    new_date=old + timedelta(days=7 if code != "force_majeure" else 3),
                    reason_code=code,
                    reason=label,
                    notify_hours=48 if code == "teacher_leave" else (0 if code == "force_majeure" else 24),
                    status="notified" if i < 16 else "done",
                    remark="演示调课",
                    updated_at=NOW,
                )
            )
        db.add_all(changes)
        print("seeded schedule_change 20")

        wo_rows = [
            ("WO20250921001", "change_class", "ENR20250921C05", 5, name_to_id["秋季初二物理实验班"], name_to_id["秋季初二数学提高B班"], "pending", "同校区换时段", "0", "0"),
            ("WO20250921002", "withdraw", "ENR20250921C02", 2, name_to_id["秋季初二数学提高B班"], None, "pending", "开课后试算退班", "2625.00", "175.00"),
            ("WO20250921003", "transfer_class", "ENR20250921C03", 3, name_to_id["秋季初三英语冲刺班"], name_to_id["秋季初三数学压轴班"], "rejected", "进度超70%不可转班", "0", "0"),
            ("WO20250921004", "settle_refund", "ENR20250921C08", 4, name_to_id["结课初二英语专项班"], None, "approved", "结课不转新班", "1440.00", "0"),
            ("WO20250921005", "settle_transfer", "ENR20250921C04", 4, name_to_id["暑期初一语文阅读班"], name_to_id["秋季初一语文启蒙班"], "pending", "暑期班结转换班", "0", "0"),
            ("WO20250921006", "withdraw", "ENR20250921C06", 6, name_to_id["待开初三数学培优班"], None, "rejected", "分期未结清不可退", "0", "0"),
            ("WO20250921007", "change_class", "ENR20250921C01", 1, name_to_id["秋季初二数学提高A班"], name_to_id["秋季初二数学提高B班"], "pending", "开课前换班", "0", "0"),
            ("WO20250921008", "change_class", "ENR20250921C07", 7, name_to_id["满员初二英语听说班"], name_to_id["线上初三英语语法班"], "rejected", "目标班满员", "0", "50"),
            ("WO20250921009", "transfer_class", "ENR20250921C10", 9, name_to_id["秋季初二语文作文班"], name_to_id["秋季初二物理实验班"], "pending", "换科目转班", "400.00", "0"),
            ("WO20250921010", "withdraw", "ENR20250921C09", 8, name_to_id["停办初一化学启蒙班"], None, "approved", "停办退班", "1733.36", "0"),
            ("WO20250921011", "settle_refund", "ENR20250921C18", 17, name_to_id["结课初二英语专项班"], None, "completed", "已结转退班打款", "1080.00", "0"),
            ("WO20250921012", "change_class", "ENR20250921C13", 12, name_to_id["秋季初二化学同步班"], name_to_id["秋季初二生物会考班"], "pending", "进度差过大待审", "0", "50"),
            ("WO20250921013", "withdraw", "ENR20250921C16", 15, name_to_id["秋季初三数学压轴班"], None, "rejected", "进度过高建议结转", "0", "0"),
            ("WO20250921014", "settle_transfer", "ENR20250921C08", 4, name_to_id["结课初二英语专项班"], name_to_id["线上初三英语语法班"], "cancelled", "学员改选退班", "0", "0"),
            ("WO20250921015", "change_class", "ENR20250921C20", 20, demo_cls, math_b, "approved", "调课后换时段", "0", "50"),
            ("WO20250921016", "withdraw", "ENR20250921C14", 13, name_to_id["线上初三英语语法班"], None, "pending", "线上班不适应", "1680.00", "140.00"),
            ("WO20250921017", "transfer_class", "ENR20250921C17", 16, name_to_id["秋季初二生物会考班"], name_to_id["秋季初二化学同步班"], "pending", "会考后转化学", "0", "0"),
            ("WO20250921018", "settle_refund", "ENR20250921C04", 4, name_to_id["暑期初一语文阅读班"], None, "rejected", "已选结转换班", "0", "0"),
            ("WO20250921019", "change_class", "ENR20250921C11", 10, name_to_id["秋季初三物理竞赛班"], phy, "pending", "竞赛班压力大", "0", "50"),
            ("WO20250921020", "withdraw", "ENR20250921C12", 11, name_to_id["秋季初一数学基础班"], None, "pending", "开课前退班", "3000.00", "0"),
        ]
        wos = []
        for w in wo_rows:
            sid = (
                await db.execute(
                    text("SELECT student_id FROM enrollment WHERE order_no=:o"),
                    {"o": w[2]},
                )
            ).scalar_one()
            wos.append(
                WorkOrder(
                    work_no=w[0],
                    apply_type=w[1],
                    order_no=w[2],
                    student_id=int(sid),
                    from_class_id=w[4],
                    to_class_id=w[5],
                    order_source="offline",
                    status=w[6],
                    reason=w[7],
                    amount=Decimal(w[8]),
                    fee_amount=Decimal(w[9]),
                    applicant="顾问小周",
                    updated_at=NOW,
                )
            )
        db.add_all(wos)
        print("seeded work_orders 20")

        coupons = []
        for i in range(20):
            used = i < 8
            order = f"ENR20250921C{i + 1:02d}" if used else None
            coupons.append(
                Coupon(
                    coupon_no=f"CPN20250921{i + 1:03d}",
                    student_id=stu_ids[i],
                    name=["秋季满减100", "续报立减50", "转介绍80", "抖音券60"][i % 4],
                    amount=Decimal(["100.00", "50.00", "80.00", "60.00"][i % 4]),
                    status="used" if used else ("expired" if i > 16 else "unused"),
                    order_no=order,
                    order_source=["douyin", "renewal", "referral", "offline"][i % 4],
                    updated_at=NOW,
                )
            )
        db.add_all(coupons)
        print("seeded coupons 20")

        # 分期：C06 未结清（不可退班）
        inst = []
        for p in range(1, 4):
            inst.append(
                Installment(
                    order_no="ENR20250921C06",
                    student_id=stu_ids[5],
                    period_no=p,
                    amount=Decimal("1600.00"),
                    due_date=date(2026, 8, 1) + timedelta(days=30 * p),
                    status="paid" if p == 1 else "pending",
                    paid_at=NOW if p == 1 else None,
                    updated_at=NOW,
                )
            )
        for i in range(17):
            inst.append(
                Installment(
                    order_no=f"ENR20250921C{(i % 5) + 10:02d}",
                    student_id=stu_ids[(i % 5) + 9],
                    period_no=(i % 3) + 1,
                    amount=Decimal("1000.00"),
                    due_date=date(2026, 9, 1) + timedelta(days=30 * (i % 3)),
                    status="paid" if i % 2 == 0 else "overdue",
                    paid_at=NOW if i % 2 == 0 else None,
                    updated_at=NOW,
                )
            )
        db.add_all(inst)
        print(f"seeded installment {len(inst)}")

        crfs = []
        for i in range(20):
            cash = Decimal("1440.00") if i == 0 else Decimal(str(800 + i * 20))
            cpn = Decimal("200.00") if i < 6 else Decimal("0")
            crfs.append(
                CouponRefund(
                    refund_no=f"CRF20250921{i + 1:03d}",
                    order_no="ENR20250921C08" if i == 0 else f"ENR20250921C{(i % 18) + 2:02d}",
                    student_id=stu_ids[min(i, 19)],
                    work_no="WO20250921004" if i == 0 else None,
                    cash_refund=cash,
                    coupon_amount=cpn,
                    coupon_refundable=Decimal("0"),
                    total_refund=cash,
                    policy="settle_no_coupon" if i < 10 else "withdraw_cash_only",
                    status=["pending", "approved", "paid"][i % 3],
                    remark="结转退班不退券" if i < 10 else "开课后退班只退现金",
                    updated_at=NOW,
                )
            )
        db.add_all(crfs)
        print("seeded coupon_refund 20")

        extra_rf = []
        for i in range(8):
            extra_rf.append(
                RefundOrder(
                    refund_no=f"RF20250921{i + 1:03d}",
                    order_no=f"ENR20250921C{i + 2:02d}",
                    student_id=stu_ids[i + 1],
                    work_no=f"WO20250921{i + 1:03d}",
                    amount=Decimal(str(1000 + i * 50)),
                    status=["pending", "approved", "paid", "rejected"][i % 4],
                    channel="original",
                    reason="场景扩写退款单",
                    updated_at=NOW,
                )
            )
        db.add_all(extra_rf)

        await db.commit()
        print("seed ok")


async def main() -> None:
    await migrate_schema()
    await seed()


if __name__ == "__main__":
    asyncio.run(main())
