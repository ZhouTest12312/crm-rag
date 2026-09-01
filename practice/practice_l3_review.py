"""
Day 4 复习 · L3：条件边 + mock 查单

跑法（项目根）：
  $env:PYTHONPATH="."
  .venv\\Scripts\\python.exe practice\\practice_l3_review.py

目标：
  ENR20250801001 → lookup_order 分支 → reply 含 active
  1+1等于几 → call_llm 分支

图：
  START ──route──→ lookup_order → END
              └──→ call_llm     → END

卡住报：「Day4 复习 · 第 N 步 · …」
详细提示：docs/PRACTICE_REVIEW.md → Day4 小节
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.constants import END, START
from langgraph.graph import StateGraph

# ── 第 1 步：State ─────────────────────────────────────────
class State(TypedDict):
    user_message:str
    reply:str


# ── 第 2 步：import tools + llm ─────────────────────────────
# 提示：from services.tools import extract_order_no, lookup_order
#       from services.llm import chat
# TODO
from services.tools import extract_order_no, lookup_order
from services.llm import chat
# ── 第 3 步：route（条件边判断函数）──────────────────────────
# 提示：return 字符串节点名，必须和后面 path_map 的 key 一致
#   有 ENR → "lookup_order"
#   无 ENR → "call_llm"
def route(state: State) -> str:
    if extract_order_no(state['user_message']):
        return 'lookup_order'
    else:
        return 'call_llm'

# ── 第 4 步：lookup_order_node ──────────────────────────────
# 提示：extract_order_no → lookup_order → 拼 reply 字符串
def lookup_order_node(state: State) -> dict:
    order_no = extract_order_no(state['user_message'])
    orders = lookup_order(order_no or '')
    if orders.get('ok'):
        return {
            "reply":(
                f"订单 {orders['order_no']} 状态 {orders['status']}，"
                f"学员 {orders['student_name']}"
            )
        }
    else:
        return {"reply":'查询失败'}

# ── 第 5 步：call_llm ───────────────────────────────────────
def call_llm(state: State) -> dict:
    messages = [
        {
            'role': 'user',
            'content':
                       f"「用户问题：」+ {state['user_message']}"
        }
    ]
    answer = chat(messages)
    return {'reply': answer}


# ── 第 6 步：建图 ───────────────────────────────────────────
# 提示：
g = StateGraph(State)
g.add_node("lookup_order", lookup_order_node)
g.add_node("call_llm", call_llm)
g.add_conditional_edges(START, route, {"lookup_order":"lookup_order", "call_llm":"call_llm"})
g.add_edge("lookup_order", END)
g.add_edge("call_llm", END)
app = g.compile()
# TODO


# ── 第 7 步：测两个问题 ─────────────────────────────────────
if __name__ == "__main__":
    print("=== ENR 查单 ===")
    print(app.invoke({"user_message": "ENR20250801001 什么状态？"}))
    print("=== 普通问题 ===")
    print(app.invoke({"user_message": "1+1等于几？"}))
