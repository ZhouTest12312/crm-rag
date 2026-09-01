"""
Day 4 · L3：工具节点 + conditional_edges（查订单）

跑法（项目根）：
  $env:PYTHONPATH="."; .venv\\Scripts\\python.exe practice\\practice_l3.py

目标：
  问「ENR20250801001 什么状态？」→ 走 lookup 节点 → reply 含 active 等
  问普通问题 → 走 call_llm（可简单 echo 或调 chat）

图示意：
  START ──route──→ lookup_order ──→ END
              └──→ call_llm     ──→ END
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TypedDict

# 从 practice/ 跑脚本时，把项目根加入路径，才能 import services
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.constants import END, START
from langgraph.graph import StateGraph

from services.llm import chat
from services.tools import extract_order_no, lookup_order


class State(TypedDict):
    user_message: str
    reply: str


def route(state: State) -> str:
    """条件边：根据 user_message 决定下一站 node 名（字符串）。"""
    # extract_order_no 有值 → 走查单；None → 走 LLM
    if extract_order_no(state["user_message"]):
        return "lookup_order"
    return "call_llm"


def lookup_order_node(state: State) -> dict:
    """工具节点：调 mock 查单，不经过 LLM，直接拼 reply。"""
    order_no = extract_order_no(state["user_message"])
    result = lookup_order(order_no or "")
    if not result.get("ok"):
        return {"reply": result.get("error", "查询失败")}
    return {
        "reply": (
            f"订单 {result['order_no']} 状态 {result['status']}，"
            f"学员 {result['student_name']}"
        )
    }


def call_llm(state: State) -> dict:
    """普通问答：没有 ENR 时走这里。"""
    answer = chat([{"role": "user", "content": state["user_message"]}])
    return {"reply": answer}


# --- 建图 ---
g = StateGraph(State)

# add_node 第一个参数 = 站名；第二个参数 = 干活的函数
g.add_node("lookup_order", lookup_order_node)
g.add_node("call_llm", call_llm)

# 条件边：START 出来后先跑 route()，返回值决定下一站
# path_map 的 key 必须和 route  return 的字符串一致
g.add_conditional_edges(
    START,
    route,
    {
        "lookup_order": "lookup_order",
        "call_llm": "call_llm",
    },
)

# 两个分支都接到 END
g.add_edge("lookup_order", END)
g.add_edge("call_llm", END)

app = g.compile()

if __name__ == "__main__":
    print("=== ENR 查单 ===")
    print(app.invoke({"user_message": "ENR20250801001 什么状态？"}))
    print("=== 普通问题 ===")
    print(app.invoke({"user_message": "1+1等于几？"}))
