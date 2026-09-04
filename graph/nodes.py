"""图节点：从 practice_l2 / practice_l3 搬逻辑过来。"""
from __future__ import annotations

import json
import re

from langgraph.constants import END

from langgraph.types import interrupt

from services.tools import (
    extract_order_no,
    lookup_order,
    estimate_refund,
    max_paid,
    count_orders,
    list_orders,
    lookup_teachers,
    lookup_classes,
    count_students_tool,
    crm_overview,
    lookup_work_orders,
    lookup_coupons,
    lookup_cash_vouchers,
    lookup_refunds,
    lookup_students,
    lookup_student_orders,
    count_orders_by_source,
    count_work_orders_tool,
    count_coupons_tool,
    count_cash_vouchers_tool,
    count_refunds_tool,
    set_work_order_status,
    mark_refund_paid,
    apply_enrollment_refund,
    cancel_order,
)
from utils.rbac import (
    has_perm,
    assert_perm,
    PERM_ORDER_READ,
    PERM_ORDER_WRITE,
    PERM_ORDER_CANCEL,
)

# TODO 1：from graph.state import State
from graph.state import State
# TODO 2：from services.rag import retrieve
from services.rag import retrieve
# TODO 3：from services.llm import chat
from services.llm import chat, chat_message

# TODO 5：def route(state) -> str
_ENR_PATTERN = re.compile(r"ENR\d+", re.I)
_WO_PATTERN = re.compile(r"WO\d+", re.I)
_RF_PATTERN = re.compile(r"RF\d+", re.I)
_SUBJECT_IN_Q = re.compile(r"(数学|英语|语文|物理|化学|生物)")


def _subject_from_user_message(q: str) -> str | None:
    m = _SUBJECT_IN_Q.search(q or "")
    return m.group(1) if m else None
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": "按订单号查询报名订单：状态、已消课时、金额等",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_no": {
                        "type": "string",
                        "description": "订单号，例如 ENR20250801001",
                    },
                },
                "required": ["order_no"],
            },
        },

    },
    {
        "type": "function",
        "function": {
            "name": "estimate_refund",
            "description": "按照消费课次进行退费退班试算（未落地的金额测算）",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_no": {
                        "type": "string",
                        "description": "订单号，例如 ENR20250820005",
                    },
                },
                "required": ["order_no"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "max_paid",
            "description": (
                "查询库里实付金额最高的报名订单（最贵的一单/课）。"
                "用户问「最贵」「最高消费」「哪单金额最大」时调用；无需订单号。"
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_orders",
            "description": (
                "统计报名订单数量。用户问「有多少订单」「订单总数」时调用；"
                "可按 status 过滤。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "active/pending_start/completed/refunded/cancelled；不传则返回各状态明细与总计",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_orders",
            "description": (
                "列出报名订单摘要。默认不含已取消；可按 status 过滤。"
                "用户问订单列表时调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "limit": {"type": "integer", "description": "最多返回条数，默认20"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_teachers",
            "description": (
                "统计并列出主讲老师（班级表去重）及各自带班数。"
                "用户问「多少老师」「老师列表」「有几位老师」时必须调用。"
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_classes",
            "description": (
                "统计并列出班级（名称、科目、主讲、状态、人数）。"
                "可按 status / subject / teacher_name 过滤。"
                "用户问「多少班级」「数学班有几个」「某老师带哪些班」时调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "subject": {"type": "string", "description": "科目，如数学/英语"},
                    "teacher_name": {"type": "string", "description": "主讲老师姓名模糊匹配"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_students",
            "description": "统计学员总数。用户问「多少学员」「学员有几个」时调用。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_students",
            "description": "按姓名或手机号查学员。问「张三是谁」「查学员」时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_student_orders",
            "description": (
                "查某学员的全部报名订单。可传 student_id 或 name。"
                "问「张三的订单」「学员5有哪些单」时调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {"type": "integer"},
                    "name": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_orders_by_source",
            "description": (
                "按订单来源统计报名单数量（线下/抖音/转介绍等）。"
                "问「抖音来了多少单」「订单来源分布」时调用。"
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_work_orders",
            "description": "统计工单数量；可按 status、apply_type 过滤。",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "apply_type": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_coupons",
            "description": "统计优惠券数量；可按 status 过滤。",
            "parameters": {
                "type": "object",
                "properties": {"status": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_cash_vouchers",
            "description": "统计现金券数量；可按 status 过滤。",
            "parameters": {
                "type": "object",
                "properties": {"status": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_refunds",
            "description": "统计退款单数量；可按 status 过滤。",
            "parameters": {
                "type": "object",
                "properties": {"status": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crm_overview",
            "description": (
                "一次返回订单/班级/老师/学员/工单/券/退款数量概览。"
                "用户笼统问「系统里有多少数据」「概况」时调用。"
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_work_orders",
            "description": (
                "查询教务工单（换班/转班/退班/结转换/结转退）。"
                "可按 status、apply_type、order_no、student_id 过滤；"
                "用户问工单列表、待审核工单、某单关联工单时调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "pending/approved/rejected/completed/cancelled",
                    },
                    "apply_type": {
                        "type": "string",
                        "description": (
                            "change_class换班 / transfer_class转班 / withdraw退班 / "
                            "settle_transfer结转换 / settle_refund结转退"
                        ),
                    },
                    "order_no": {"type": "string"},
                    "student_id": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_coupons",
            "description": "查询优惠券；可按学员、状态、订单号过滤。问优惠券时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {"type": "integer"},
                    "status": {
                        "type": "string",
                        "description": "unused/used/expired",
                    },
                    "order_no": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_cash_vouchers",
            "description": "查询现金券余额与状态；可按学员、状态过滤。",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {"type": "integer"},
                    "status": {
                        "type": "string",
                        "description": "active/used_up/frozen/expired",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_refunds",
            "description": (
                "查询退款单进度与金额；可按订单号、学员、状态、退款号过滤。"
                "与 estimate_refund（试算）不同，本工具查已建退款单。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_no": {"type": "string"},
                    "student_id": {"type": "integer"},
                    "status": {
                        "type": "string",
                        "description": "pending/approved/paid/rejected",
                    },
                    "refund_no": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_work_order_status",
            "description": (
                "写操作：审批工单状态为 approved/rejected/completed/cancelled。"
                "仅 admin；会触发确认。参数 work_no + status。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "work_no": {"type": "string"},
                    "status": {"type": "string"},
                    "remark": {"type": "string"},
                },
                "required": ["work_no", "status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mark_refund_paid",
            "description": (
                "写操作：退款单标记已打款 paid，并同步报名单为 refunded。"
                "仅 admin；会触发确认。"
            ),
            "parameters": {
                "type": "object",
                "properties": {"refund_no": {"type": "string"}},
                "required": ["refund_no"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_enrollment_refund",
            "description": (
                "写操作：报名订单退班落地，状态改为 refunded。仅 admin；会触发确认。"
            ),
            "parameters": {
                "type": "object",
                "properties": {"order_no": {"type": "string"}},
                "required": ["order_no"],
            },
        },
    },
]
_CONFIRM = frozenset({"确认", "是的", "是", "好的", "ok", "yes"})
# 明显闲聊：跳过 retrieve，避免硬塞制度把模型逼成「我是教务助手」拒答
_CHITCHAT_RE = re.compile(
    r"^\s*("
    r"你好|您好|嗨|哈喽|hello|hi|hey|在吗|在不在|"
    r"早上好|中午好|下午好|晚上好|晚安|"
    r"谢谢|感谢|多谢|拜拜|再见|"
    r"今天天气怎么样|天气怎么样|你是谁|你叫什么|你能做什么|你会什么"
    r")[\s。！？.!？]*$",
    re.I,
)
_BUSINESS_HINT = (
    "退班", "退款", "换班", "转班", "结转", "订单", "学员", "老师", "班级",
    "工单", "优惠券", "现金券", "制度", "消课", "排课", "买班", "报名",
    "ENR", "WO", "RF",
)
AGENT_SYSTEM = (
    "你是教培 CRM 教务助手，帮顾问处理制度、订单、学员、工单等教务问题。"
    "闲聊（问候、感谢、天气等）请简短自然回应，可顺带一句「有教务问题随时问」；"
    "不要只回「我是教务助手」或机械自报身份。"
    "业务事实（数量、金额、状态、单号）必须调用工具查库，禁止编造；"
    "制度/规则优先依据摘录，摘录不足就说明依据不足，不要编造条款。"
)


def _is_confirm(answer) -> bool:
    normalized = str(answer).strip().lower()
    return answer in _CONFIRM or normalized in {x.lower() for x in _CONFIRM}


def _extract_work_no(text: str) -> str | None:
    m = _WO_PATTERN.search(text or "")
    return m.group(0).upper() if m else None


def _extract_refund_no(text: str) -> str | None:
    m = _RF_PATTERN.search(text or "")
    return m.group(0).upper() if m else None


def _is_chitchat(q: str) -> bool:
    s = (q or "").strip()
    if not s or len(s) > 40:
        return False
    if extract_order_no(s) or _WO_PATTERN.search(s) or _RF_PATTERN.search(s):
        return False
    if any(k.lower() in s.lower() for k in _BUSINESS_HINT):
        return False
    return bool(_CHITCHAT_RE.match(s))


def route_entry(state) -> str:
    q = state.get("user_message") or ""
    enr = extract_order_no(q)
    wo = _extract_work_no(q)
    rf = _extract_refund_no(q)
    if enr and any(k in q for k in ("取消", "作废", "退单")):
        return "cancel_confirm"
    if wo and any(k in q for k in ("通过", "驳回", "完成", "撤销")):
        return "write_confirm"
    if rf and any(k in q for k in ("打款", "确认退款", "通过退款", "已退")):
        return "write_confirm"
    if enr and any(k in q for k in ("确认退班", "落地退款", "执行退班", "退班落地")):
        return "write_confirm"
    if _is_chitchat(q):
        return "agent"
    return "retrieve"


def write_confirm_node(state) -> dict:
    """自然语言写操作确认：审工单 / 退款打款 / 退班落地。"""
    user = {"role": state.get("role") or "guest"}
    if not has_perm(user, PERM_ORDER_WRITE):
        deny = assert_perm(user, PERM_ORDER_WRITE) or "无权写操作"
        return {"reply": deny}
    q = state["user_message"]
    wo = _extract_work_no(q)
    rf = _extract_refund_no(q)
    enr = extract_order_no(q)

    if wo:
        if "驳回" in q:
            status = "rejected"
        elif "完成" in q:
            status = "completed"
        elif "撤销" in q:
            status = "cancelled"
        else:
            status = "approved"
        answer = interrupt({
            "action": "set_work_order_status",
            "work_no": wo,
            "status": status,
            "prompt": (
                f"将把工单 {wo} 改为 {status}。请回复「确认」执行；"
                "其他内容则取消。"
            ),
        })
        if not _is_confirm(answer):
            return {"reply": "未确认，工单未改动。"}
        result = set_work_order_status(wo, status)
        if result.get("ok"):
            return {"reply": f"工单 {result['work_no']} 已更新为 {result['status']}。"}
        return {"reply": result.get("error") or "更新失败"}

    if rf:
        answer = interrupt({
            "action": "mark_refund_paid",
            "refund_no": rf,
            "prompt": (
                f"将把退款单 {rf} 标记为已打款，并同步订单为 refunded。"
                "请回复「确认」执行。"
            ),
        })
        if not _is_confirm(answer):
            return {"reply": "未确认，退款单未改动。"}
        result = mark_refund_paid(rf)
        if result.get("ok"):
            return {
                "reply": (
                    f"退款单 {result['refund_no']} 已打款 "
                    f"{result['amount']} 元，订单 {result['order_no']} 已 refunded。"
                )
            }
        return {"reply": result.get("error") or "操作失败"}

    if enr:
        answer = interrupt({
            "action": "apply_enrollment_refund",
            "order_no": enr,
            "prompt": (
                f"将把订单 {enr} 状态改为 refunded（退班落地）。"
                "请回复「确认」执行。"
            ),
        })
        if not _is_confirm(answer):
            return {"reply": "未确认，订单未改动。"}
        result = apply_enrollment_refund(enr)
        if result.get("ok"):
            return {"reply": f"订单 {result['order_no']} 已退班落地，状态 {result['status']}。"}
        return {"reply": result.get("error") or "操作失败"}

    return {"reply": "请提供工单号 WO… / 退款号 RF… / 订单号 ENR…"}
def _message_role(msg) -> str:
    if isinstance(msg, dict):
        return msg.get("role") or ""
    return getattr(msg, "type", "") or ""


def _last_is_tool(messages: list) -> bool:
    return bool(messages) and _message_role(messages[-1]) == "tool"


def agent_node(state):
    user = {"role": state.get("role") or "guest"}
    history = list(state.get("messages") or [])
    parts = []
    if state.get('context'):
        parts.append("以下制度摘录（业务规则问题时优先依据，不要编造）：\n\n"
                     + state["context"])
    parts.append(f'用户问题:{state["user_message"]}')
    if _is_chitchat(state.get("user_message") or ""):
        parts.append(
            "【本轮是闲聊】请自然简短回应，不要调工具，不要只自报身份。"
        )
    parts.append(
        "【硬规则】问数量/列表/金额/状态等事实，必须调用对应工具查库，"
        "禁止只根据制度摘录回答「查不到/材料没有」。"
        "制度摘录只用于规则解释（怎么退、能不能换），不用于统计人数订单。"
    )
    parts.append(
        "多轮追问时以【当前】用户问题为准。"
        "例如上一轮数学班、本轮只说「英语班/语文班」→ 必须 lookup_classes(subject=英语或语文)，"
        "禁止沿用上一轮科目或编造。"
        "subject 传科目名即可（英语/数学/语文），不要传「英语班」整词；工具会自动去掉「班」后缀。"
        "工具返回若带 answer_hint，必须遵守，只答当前科目。"
    )
    parts.append(
        "若用户问退班/退款金额且消息含订单号，优先调用 estimate_refund，"
        "不要自己算数。"
    )
    parts.append(
        "若用户问最贵的课/最高实付/哪单金额最大，调用 max_paid，不要猜数字。"
    )
    parts.append(
        "问有多少订单 → count_orders；订单列表 → list_orders；"
        "订单来源分布 → count_orders_by_source；"
        "问多少老师 → lookup_teachers；问班级/某科目班 → lookup_classes；"
        "问多少学员 → count_students；按姓名查学员 → lookup_students；"
        "某人的订单 → lookup_student_orders；"
        "问概况 → crm_overview；"
        "工单数量 → count_work_orders；工单列表 → lookup_work_orders；"
        "优惠券数量 → count_coupons；列表 → lookup_coupons；"
        "现金券 → count_cash_vouchers / lookup_cash_vouchers；"
        "退款单数量 → count_refunds；列表 → lookup_refunds；"
        "审批工单 → set_work_order_status；退款打款 → mark_refund_paid；"
        "退班落地 → apply_enrollment_refund；"
        "报名详情 → lookup_order。禁止编造单号与数量。"
        "统计/分布类回答：先一句总数，再换行列出「- 中文名（code）：数量」，"
        "便于前端渲染表格；不要全挤在一行用顿号串。"
    )
    # tool 执行完后续问模型：带上「只答当前问题」提醒，避免粘上轮科目
    if _last_is_tool(history):
        messages = history + [
            {
                "role": "user",
                "content": (
                    f"请仅根据刚刚的工具结果回答当前问题：「{state.get('user_message') or ''}」。"
                    "若工具 JSON 含 answer_hint，必须遵守；"
                    "不要复述或混入上一轮其他科目/订单的结论。"
                ),
            }
        ]
    else:
        messages = history + [
            {
                'role': 'user',
                'content': '\n\n'.join(parts)
            }
        ]
    # 闲聊不挂工具，避免模型硬调；业务题按权限挂 schema
    chitchat = _is_chitchat(state.get("user_message") or "")
    tools = None if chitchat else (
        TOOLS_SCHEMA if has_perm(user, PERM_ORDER_READ) else None
    )
    rsp = chat_message(
        [{"role": "system", "content": AGENT_SYSTEM}] + messages,
        tools=tools,
    )
    assistant = {
        'role': 'assistant',
        'content': rsp.content or ''
    }
    if rsp.tool_calls:
        assistant['tool_calls'] = [
            {
                'id': tc.id,
                'type': 'function',
                'function': {
                    'name': tc.function.name,
                    'arguments': tc.function.arguments
                }
            }
            for tc in rsp.tool_calls
        ]
    out = {"messages": [assistant]}
    if not rsp.tool_calls:
        out["reply"] = assistant["content"]
    return out


def tools_node(state) -> dict:
    user = {"role": state.get("role") or "guest"}
    last = state['messages'][-1]
    out = []
    for tc in _tool_calls(last):
        if "function" in tc:
            tc_id = tc["id"]
            raw_args = tc["function"]["arguments"] or "{}"
            name = tc["function"]["name"]
        else:
            tc_id = tc["id"]
            raw_args = tc.get("args") or {}
            name = tc.get("name") or getattr(tc, "name", "")
        if isinstance(raw_args, dict):
            args = raw_args
        else:
            try:
                args = json.loads(raw_args or "{}")
            except json.JSONDecodeError:
                out.append({
                    "role": "tool",
                    "content": json.dumps(
                        {"ok": False, "error": "工具参数不是合法 JSON"},
                        ensure_ascii=False,
                    ),
                    "tool_call_id": tc_id,
                })
                continue
        if not has_perm(user, PERM_ORDER_READ):
            out.append({
                "role": "tool",
                "content": "当前无权限",
                "tool_call_id": tc_id,
            })
            continue
        order_no = args.get("order_no")
        try:
            if name == "lookup_order":
                result = lookup_order(order_no)
            elif name == "estimate_refund":
                result = estimate_refund(order_no)
            elif name == "max_paid":
                result = max_paid()
            elif name == "count_orders":
                result = count_orders(status=args.get("status"))
            elif name == "list_orders":
                result = list_orders(
                    status=args.get("status"),
                    limit=args.get("limit") or 20,
                )
            elif name == "lookup_teachers":
                result = lookup_teachers()
            elif name == "lookup_classes":
                # 短追问「英语班」时以当前用户话里的科目为准，避免沿用上轮数学
                subj = args.get("subject")
                hint = _subject_from_user_message(state.get("user_message") or "")
                if hint:
                    subj = hint
                result = lookup_classes(
                    status=args.get("status"),
                    subject=subj,
                    teacher_name=args.get("teacher_name"),
                )
                if isinstance(result, dict) and result.get("ok"):
                    fs = (result.get("filter") or {}).get("subject")
                    if fs:
                        result["answer_hint"] = (
                            f"本次只查了「{fs}」班，请只汇报该科目，"
                            "不要提及其他科目或上一轮结果。"
                        )
            elif name == "count_students":
                result = count_students_tool()
            elif name == "lookup_students":
                result = lookup_students(
                    name=args.get("name"), phone=args.get("phone")
                )
            elif name == "lookup_student_orders":
                result = lookup_student_orders(
                    student_id=args.get("student_id"),
                    name=args.get("name"),
                )
            elif name == "count_orders_by_source":
                result = count_orders_by_source()
            elif name == "count_work_orders":
                result = count_work_orders_tool(
                    status=args.get("status"),
                    apply_type=args.get("apply_type"),
                )
            elif name == "count_coupons":
                result = count_coupons_tool(status=args.get("status"))
            elif name == "count_cash_vouchers":
                result = count_cash_vouchers_tool(status=args.get("status"))
            elif name == "count_refunds":
                result = count_refunds_tool(status=args.get("status"))
            elif name == "crm_overview":
                result = crm_overview()
            elif name == "lookup_work_orders":
                result = lookup_work_orders(
                    status=args.get("status"),
                    apply_type=args.get("apply_type"),
                    order_no=args.get("order_no"),
                    student_id=args.get("student_id"),
                )
            elif name == "lookup_coupons":
                result = lookup_coupons(
                    student_id=args.get("student_id"),
                    status=args.get("status"),
                    order_no=args.get("order_no"),
                )
            elif name == "lookup_cash_vouchers":
                result = lookup_cash_vouchers(
                    student_id=args.get("student_id"),
                    status=args.get("status"),
                )
            elif name == "lookup_refunds":
                result = lookup_refunds(
                    order_no=args.get("order_no"),
                    student_id=args.get("student_id"),
                    status=args.get("status"),
                    refund_no=args.get("refund_no"),
                )
            elif name == "set_work_order_status":
                if not has_perm(user, PERM_ORDER_WRITE):
                    result = {"ok": False, "error": "无权审批工单（需要 admin）"}
                else:
                    wn = (args.get("work_no") or "").upper()
                    st = args.get("status") or ""
                    answer = interrupt({
                        "action": "set_work_order_status",
                        "work_no": wn,
                        "status": st,
                        "prompt": (
                            f"将把工单 {wn} 改为 {st}。请回复「确认」执行；"
                            "其他内容则取消。"
                        ),
                    })
                    if _is_confirm(answer):
                        result = set_work_order_status(
                            wn, st, remark=args.get("remark")
                        )
                    else:
                        result = {"ok": False, "error": "未确认，工单未改动"}
            elif name == "mark_refund_paid":
                if not has_perm(user, PERM_ORDER_WRITE):
                    result = {"ok": False, "error": "无权操作退款（需要 admin）"}
                else:
                    rn = (args.get("refund_no") or "").upper()
                    answer = interrupt({
                        "action": "mark_refund_paid",
                        "refund_no": rn,
                        "prompt": (
                            f"将把退款单 {rn} 标记为已打款，并同步订单为 refunded。"
                            "请回复「确认」执行。"
                        ),
                    })
                    if _is_confirm(answer):
                        result = mark_refund_paid(rn)
                    else:
                        result = {"ok": False, "error": "未确认，退款单未改动"}
            elif name == "apply_enrollment_refund":
                if not has_perm(user, PERM_ORDER_WRITE):
                    result = {"ok": False, "error": "无权退班落地（需要 admin）"}
                else:
                    on = extract_order_no(args.get("order_no") or "") or (
                        args.get("order_no") or ""
                    ).upper()
                    answer = interrupt({
                        "action": "apply_enrollment_refund",
                        "order_no": on,
                        "prompt": (
                            f"将把订单 {on} 状态改为 refunded（退班落地）。"
                            "请回复「确认」执行。"
                        ),
                    })
                    if _is_confirm(answer):
                        result = apply_enrollment_refund(on)
                    else:
                        result = {"ok": False, "error": "未确认，订单未改动"}
            else:
                result = {"ok": False, "error": f"未知工具 {name}"}
        except Exception as e:
            result = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        out.append({
            "role": "tool",
            "content": json.dumps(result, ensure_ascii=False, default=str),
            "tool_call_id": tc_id,
        })

    return {'messages': out}


def should_continue(state):
    last = state['messages'][-1]
    if _tool_calls(last):
        return 'tools'
    return END


def route(state) -> str:
    if extract_order_no(state['user_message']):
        return 'lookup_order'
    else:
        return 'retrieve'


def _tool_calls(last):
    if isinstance(last, dict):
        return last.get("tool_calls") or []
    return getattr(last, "tool_calls", None) or []


#         有 ENR → "lookup_order"；否则 → "retrieve"（或直 call_llm，先做简单版也行）
#
# TODO 6：def retrieve_node(state) -> dict   （Day3）
def retrieve_node(state) -> dict:
    hits = retrieve(state['user_message'])
    content = '\n\n'.join(hit['text'] for hit in hits)
    return {'context': content}


# TODO 7：def call_llm(state) -> dict        （带 context）
def call_llm(state) -> dict:
    history = state.get("messages") or []
    content_parts = []
    if history:
        content_parts.append("请结合上方对话历史回答。")
    if state.get("context"):
        content_parts.append(
            f"以下制度摘录（业务规则问题时优先依据，不要编造）：\n\n{state['context']}"
        )
    content_parts.append(f"用户问题：{state['user_message']}")
    message = [{"role": "user", "content": "\n\n".join(content_parts)}]
    all_msg = history + message
    answer = chat(all_msg)
    return {"reply": answer}


# TODO 8：def lookup_order_node(state) -> dict （Day4）
def lookup_order_node(state) -> dict:
    order_no = extract_order_no(state['user_message'])
    row = lookup_order(order_no)
    if not row.get('ok'):
        return {
            'reply': row.get('error', '查询失败')
        }
    else:
        return {"reply": (
            f"订单 {row['order_no']} 状态 {row['status']}，"
            f"学员 {row['student_name']}"
        )}
# 对照：practice/practice_l2.py、practice/practice_l3.py

def cancel_confirm_node(state) -> dict:
    user = {"role": state.get("role") or "guest"}
    if not has_perm(user, PERM_ORDER_CANCEL):
        deny = assert_perm(user, PERM_ORDER_CANCEL) or "无权取消"
        return {"reply": deny}
    order_no = extract_order_no(state["user_message"])
    if not order_no:
        return {"reply": "请提供订单号"}
    answer = interrupt({
        "order_no": order_no,
        "prompt": (
            f"将取消订单 {order_no}。请回复「确认」后执行；"
            "回复其他内容则不取消。"
        ),
    })
    normalized = str(answer).strip().lower()
    if _is_confirm(answer):
        result = cancel_order(order_no)
        if result.get("ok"):
            return {
                "reply": (
                    f"已取消订单 {result['order_no']}，状态 {result['status']}。"
                )
            }
        return {"reply": result.get("error") or "取消失败"}
    return {"reply": "未确认，订单未取消。"}