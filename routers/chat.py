"""Day 5：POST /api/chat → graph.invoke"""
from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from fastapi import APIRouter, Header, Depends
from fastapi.responses import StreamingResponse

from langgraph.types import Command

from schemas.chat import ChatRequest, ChatResponse, HistoryResponse
from services.chat_session import load_messages, save_messages
from services.tools import extract_order_no, estimate_refund
from services.format_answer import clean_assistant_text
from utils.auth import get_optional_user
from utils.rbac import PERM_ORDER_READ, has_perm, assert_perm

router = APIRouter(prefix="/api", tags=["chat"])

from graph.build import graph_app

logger = logging.getLogger(__name__)

GRAPH_TIMEOUT_SEC = 45
GRAPH_RECURSION_LIMIT = 8
_REFUND_KW = ("退班", "退款", "试算", "能退")
_FOLLOWUP_TAIL = re.compile(r"[呢吗？?]$")
_CONFIRM = frozenset({"确认", "是的", "是", "好的", "ok", "yes"})
_STREAM_CHUNK = 12


def _graph_config(session_id: str) -> dict:
    return {
        "recursion_limit": GRAPH_RECURSION_LIMIT,
        "configurable": {"thread_id": session_id},
    }


def _graph_state(q: str, history: list, user: dict) -> dict:
    return {
        "user_message": q,
        "messages": history,
        "reply": "",
        "role": user["role"],
        "context": "",
    }


def _hit_chunks_from_result(result: dict) -> int:
    ctx = (result.get("context") or "").strip()
    if not ctx:
        return 0
    return len([p for p in ctx.split("\n\n") if p.strip()])


def _iter_answer_chunks(answer: str, chunk_size: int = _STREAM_CHUNK):
    for i in range(0, len(answer), chunk_size):
        yield answer[i:i + chunk_size]


def _run_graph_turn(
        session_id: str,
        q: str,
        user: dict,
        history: list,
) -> tuple[str, dict, int]:
    cfg = _graph_config(session_id)
    snap = graph_app.get_state(cfg)
    graph_state = _graph_state(q, history, user)
    if snap.next and q in _CONFIRM:
        result = _invoke_graph(graph_state, session_id, Command(resume=q))
    else:
        result = _invoke_graph(graph_state, session_id)
    answer = _reply_from_graph_result(result)
    used_tools = _used_tools(result.get("messages"))
    return answer, result, used_tools


def _sse_data(payload: str) -> str:
    """一段 SSE：payload 用 JSON 包一层，避免正文里的换行拆坏帧。"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _user_facing_error(exc: BaseException) -> str:
    """给用户看的短提示；完整异常只打日志，不进聊天气泡。"""
    name = type(exc).__name__
    text = str(exc)
    low = text.lower()
    if name == "GraphRecursionError" or "recursion limit" in low:
        return "这个问题处理步骤过多，请换个更具体的问法再试一次。"
    if "insufficient balance" in low or "402" in text:
        return "模型服务暂时不可用，请稍后再试。"
    if "rate limit" in low or "429" in text:
        return "请求太频繁，请稍后再试。"
    if "timeout" in low or name.endswith("Timeout"):
        return "响应超时，请稍后再试。"
    if "connect" in low or "connection" in low:
        return "网络异常，请检查网络后重试。"
    return "暂时无法回答，请稍后再试或换个问法。"


def _wants_refund_estimate(q: str, history: list) -> bool:
    if any(k in q for k in _REFUND_KW):
        return True
    if not _FOLLOWUP_TAIL.search(q.strip()):
        return False
    for m in reversed(history[-8:]):
        if m.get("role") != "user":
            continue
        if any(k in (m.get("content") or "") for k in _REFUND_KW):
            return True
    return False


def _format_refund_answer(result: dict) -> str:
    if result.get("ok"):
        return (
            f"订单 {result['order_no']} 退班试算：实付 {result['paid_amount']} 元，"
            f"已消 {result['consumed_lessons']} 节（单价 {result['unit_price']} 元），"
            f"应退 {result['refund_amount']} 元。"
        )
    return result.get("error") or "试算失败"


def _invoke_graph(state: dict, session_id: str, command: Command | None = None) -> dict:
    cfg = {
        "recursion_limit": GRAPH_RECURSION_LIMIT,
        "configurable": {"thread_id": session_id},
    }
    if command is not None:
        return graph_app.invoke(command, config=cfg)
    return graph_app.invoke(state, config=cfg)


def _reply_from_graph_result(result: dict) -> str:
    reply = result.get("reply")
    if reply:
        return reply
    interrupts = result.get("__interrupt__") or []
    if interrupts:
        item = interrupts[0]
        val = item.value if hasattr(item, "value") else item.get("value", item)
        if isinstance(val, dict):
            return val.get("prompt") or str(val)
        return str(val)
    return "（空回复）"


def _append_turn(session_id: str, history: list, question: str, answer: str) -> None:
    save_messages(session_id, history + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": clean_assistant_text(answer)},
    ])
def _approx_tokens(*texts: str) -> int:
    n = sum(len(t or "") for t in texts)
    return max(1, n // 2)  # 中文粗估

def _used_tools(messages) -> int:
    for m in messages or []:
        role = m.get("role") if isinstance(m, dict) else getattr(m, "type", None)
        # LangGraph 里 tool 消息常见 role="tool" 或 type="tool"
        if role in ("tool",) or getattr(m, "type", None) == "tool":
            return 1
        if isinstance(m, dict) and m.get("tool_calls"):
            return 1
        if getattr(m, "tool_calls", None):
            return 1
    return 0
# TODO 2：@router.post("/chat", response_model=ChatResponse)
#         def chat(req: ChatRequest):
#             result = graph_app.invoke({"user_message": req.question})
#             return ChatResponse(answer=result["reply"], sources=[])

@router.get("/chat/history", response_model=HistoryResponse)
def chat_history(session_id: str):
    """按 session_id 拉取 Redis/内存里的多轮消息（侧栏点历史用）。"""
    msgs = load_messages(session_id)
    cleaned = []
    for m in msgs:
        if (m.get("role") == "assistant") and m.get("content"):
            cleaned.append({**m, "content": clean_assistant_text(m["content"])})
        else:
            cleaned.append(m)
    return HistoryResponse(session_id=session_id, messages=cleaned)


@router.post("/chat", response_model=ChatResponse)
def chat(
        req: ChatRequest,
        x_role: str | None = Header(default=None, alias="X-Role"),
        user_jwt=Depends(get_optional_user),
):
    t0 = time.perf_counter()
    if user_jwt:
        user = user_jwt
    else:
        user = {"role": (x_role or "guest").strip().lower()}
    used_tools = 0
    q = req.question.strip()
    enr = extract_order_no(q)
    if (enr or "订单" in q) and not has_perm(user, PERM_ORDER_READ):
        deny = assert_perm(user, PERM_ORDER_READ) or "无权查单"
        return ChatResponse(answer=deny, sources=[])
    if enr and _wants_refund_estimate(q, load_messages(req.session_id)):
        result = estimate_refund(enr)
        answer = _format_refund_answer(result)
        history = load_messages(req.session_id)
        _append_turn(req.session_id, history, q, answer)
        return ChatResponse(answer=answer, sources=[])
    history = load_messages(req.session_id)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_run_graph_turn, req.session_id, q, user, history)
            answer, result, used_tools = fut.result(timeout=GRAPH_TIMEOUT_SEC)
    except FuturesTimeoutError:
        answer = (
            f"处理超时（{GRAPH_TIMEOUT_SEC} 秒）。"
            "订单试算建议用：ENR20250820005 退班能退多少钱"
        )
    except Exception as e:
        logger.exception("chat graph failed")
        answer = _user_facing_error(e)
    _append_turn(req.session_id, history, req.question, answer)
    ms = (time.perf_counter() - t0) * 1000
    approx = _approx_tokens(q, answer)
    print(
        f"[chat] ms={ms:.2f} path=graph used_tools={used_tools} "
        f"approx_tokens={approx} session={req.session_id} role={user['role']}"
    )
    return ChatResponse(answer=answer, sources=[])



@router.post("/chat/stream")
def chat_stream(
        req: ChatRequest,
        x_role: str | None = Header(default=None, alias="X-Role"),
        user_jwt=Depends(get_optional_user),
):
    t0 = time.perf_counter()
    if user_jwt:
        user = user_jwt
    else:
        user = {"role": (x_role or "guest").strip().lower()}
    text = req.question.strip()
    enr = extract_order_no(text)
    if (enr or "订单" in text) and not has_perm(user, PERM_ORDER_READ):
        deny = assert_perm(user, PERM_ORDER_READ) or "无权查单"
        def deny_gen(msg: str):
            yield _sse_data(msg)
            yield "data: [DONE]\n\n"
        return StreamingResponse(deny_gen(deny), media_type="text/event-stream")
    history = load_messages(req.session_id)

    def event_gen():
        used_tools = 0
        hit_chunks = 0
        try:
            if enr and _wants_refund_estimate(text, history):
                answer = _format_refund_answer(estimate_refund(enr))
            else:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    fut = pool.submit(_run_graph_turn, req.session_id, text, user, history)
                    answer, result, used_tools = fut.result(timeout=GRAPH_TIMEOUT_SEC)
                    hit_chunks = _hit_chunks_from_result(result)
            for piece in _iter_answer_chunks(answer):
                yield _sse_data(piece)
            _append_turn(req.session_id, history, text, answer)
            yield "data: [DONE]\n\n"
            ms = (time.perf_counter() - t0) * 1000
            approx = _approx_tokens(text, answer)
            print(
                f"[chat] ms={ms:.2f} path=stream-graph used_tools={used_tools} "
                f"hit_chunks={hit_chunks} approx_tokens={approx} "
                f"session={req.session_id} role={user['role']}"
            )
        except FuturesTimeoutError:
            answer = (
                f"处理超时（{GRAPH_TIMEOUT_SEC} 秒）。"
                "订单试算建议用：ENR20250820005 退班能退多少钱"
            )
            yield _sse_data(answer)
            _append_turn(req.session_id, history, text, answer)
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.exception("chat stream failed")
            yield _sse_data(f"[ERROR] {_user_facing_error(e)}")
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
# 过关：curl 或 /docs 里 POST question，能拿到 answer
