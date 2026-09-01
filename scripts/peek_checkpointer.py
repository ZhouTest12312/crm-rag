"""
Day20 · 看见 Checkpointer（MemorySaver）

用法（项目根目录）:
  .\\.venv\\Scripts\\python.exe scripts\\peek_checkpointer.py
  .\\.venv\\Scripts\\python.exe scripts\\peek_checkpointer.py --thread-id 你的session_id

说明:
  - MemorySaver 存在「当前进程内存」里，和 uvicorn 不是同一进程时，
    用浏览器里的 session_id 来 peek 往往是空的——这很正常。
  - 默认模式会在本脚本里 invoke 两轮，再打印 get_state，用来确认 checkpointer 真的在续状态。
  - Redis 存的是给人看的对话；checkpointer 存的是图 State（messages 等通道）。
"""
from __future__ import annotations

import argparse
import json
from typing import Any


def _msg_brief(m: Any) -> str:
    if isinstance(m, dict):
        role = m.get("role") or m.get("type") or "?"
        content = (m.get("content") or "")[:60]
        tools = m.get("tool_calls")
        extra = f" tool_calls={len(tools)}" if tools else ""
        return f"  [{role}]{extra} {content!r}"
    role = getattr(m, "type", None) or getattr(m, "role", "?")
    content = (getattr(m, "content", None) or "")[:60]
    return f"  [{role}] {content!r}"


def peek(thread_id: str) -> None:
    from graph.build import graph_app

    cfg = {"configurable": {"thread_id": thread_id}}
    snap = graph_app.get_state(cfg)
    values = snap.values or {}
    msgs = values.get("messages") or []
    print("=== get_state ===")
    print(f"thread_id     : {thread_id}")
    print(f"next          : {snap.next}")
    print(f"user_message : {(values.get('user_message') or '')[:80]!r}")
    print(f"reply         : {(values.get('reply') or '')[:80]!r}")
    print(f"messages 条数  : {len(msgs)}")
    start = max(0, len(msgs) - 8)
    for i, m in enumerate(msgs[start:], start=start + 1):
        print(f"#{i}", _msg_brief(m).lstrip())
    if not msgs:
        print(
            "（空）若这是浏览器里的 session_id：MemorySaver 不在 uvicorn 进程里，"
            "跨进程看不到；请直接跑本脚本的默认 demo。"
        )


def demo_two_turns(thread_id: str) -> None:
    from graph.build import graph_app

    cfg = {
        "recursion_limit": 8,
        "configurable": {"thread_id": thread_id},
    }

    def run(q: str) -> None:
        state = {
            "user_message": q,
            "messages": [],  # 刻意不塞 Redis 历史，看 checkpointer 是否自己续
            "reply": "",
            "role": "tutor",
            "context": "",
        }
        out = graph_app.invoke(state, config=cfg)
        print(f"\n--- invoke: {q!r} ---")
        print(f"reply: {(out.get('reply') or '')[:120]!r}")

    print(f"=== demo 两轮 invoke（同一 thread_id={thread_id}）===")
    run("我叫小明")
    peek(thread_id)
    run("我叫什么？")
    peek(thread_id)
    print(
        "\n若第二轮后 messages 条数明显多于第一轮，说明 checkpointer 在按 thread_id 续状态。"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Peek LangGraph MemorySaver state")
    parser.add_argument(
        "--thread-id",
        default="",
        help="只查看该 thread；不传则跑本地两轮 demo",
    )
    parser.add_argument(
        "--demo-id",
        default="day20-checkpointer-demo",
        help="demo 使用的 thread_id",
    )
    args = parser.parse_args()

    if args.thread_id.strip():
        peek(args.thread_id.strip())
    else:
        demo_two_turns(args.demo_id)


if __name__ == "__main__":
    main()
