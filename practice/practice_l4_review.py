"""
Day 9 复习 · L4：LLM 决定是否调工具（mini tool loop）

前置：Day4 复习过关再做本文件。

跑法（项目根）：
  $env:PYTHONPATH="."
  .venv\\Scripts\\python.exe practice\\practice_l4_review.py

目标：
  ENR20250801001 什么状态？ → tool_call → lookup → 再 agent → 人话回复
  开课后退班怎么扣费？     → 无 tool_call → 直接文字答

图：
  START → agent_node ──有 tool_calls──→ tools_node ──→ agent_node
                    └──无 tool_calls──→ END

卡住报：「Day9 复习 · 第 N 步 · …」
详细提示：docs/PRACTICE_REVIEW.md → Day9 小节
"""
from __future__ import annotations

import json
from typing import Annotated, TypedDict

from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages


# ── 第 1 步：State ─────────────────────────────────────────
# 提示：messages: Annotated[list, add_messages]
class State(TypedDict):
    messages: Annotated[list, add_messages]


# ── 第 2 步：import ───────────────────────────────────────
# 提示：from services.llm import chat_message
#       from services.tools import lookup_order
# TODO
from services.tools import lookup_order
from services.llm import chat_message

# ── 第 3 步：TOOLS_SCHEMA ───────────────────────────────────
# 提示：OpenAI function 格式，name=lookup_order，参数 order_no
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
]  # TODO


# ── 第 4 步：agent_node ─────────────────────────────────────
# 提示：
#   msg = chat_message(state["messages"], tools=TOOLS_SCHEMA)
#   assistant = {"role":"assistant", "content": msg.content or ""}
#   if msg.tool_calls: 才加 tool_calls 列表（tc.id, tc.function.name/arguments）
#   return {"messages": [assistant]}
def agent_node(state: State) -> dict:
    msg = chat_message(state['messages'],tools=TOOLS_SCHEMA)
    assistant = {
        'role':'assistant',
        'content':msg.content or ''
    }
    if msg.tool_calls:
        assistant['tool_calls'] = [
            {
               'id':tc.id,
                'type':'function',
                'function':{
                    'name':tc.function.name,
                    'arguments':tc.function.arguments
                }
            }
            for tc in msg.tool_calls
        ]
    return {'messages':[assistant]}
# ── 第 5 步：读 tool_calls 的小 helper（建议写）──────────────
# 提示：AIMessage 没有 .get()，用 getattr(last, "tool_calls", None) or []
def _tool_calls(last) -> list:
    if isinstance(last, dict):
        return last.get("tool_calls") or []
    return getattr(last, "tool_calls", None) or []


# ── 第 6 步：tools_node ─────────────────────────────────────
# 提示：遍历 tool_calls → lookup_order → role:tool, content=json.dumps(...), tool_call_id
def tools_node(state: State) -> dict:
    last = state['messages'][-1]
    list1 = []
    for tc in _tool_calls(last):
       if 'function' in tc:
           args = json.loads(tc["function"]["arguments"] or "{}")
           tc_id = tc["id"]
       else:
           args = tc.get("args") or {}
           tc_id = tc["id"]
       order_no = args.get('order_no')
       result = lookup_order(order_no)
       list1.append({
           'role':'tool',
           'content':json.dumps(result),
           'tool_call_id':tc_id
       })
    return {'messages':list1}

# ── 第 7 步：should_continue ─────────────────────────────────
# 提示：有 tool_calls → return "tools"（和 path_map key 一致）；否则 END
def should_continue(state: State) -> str:
    if _tool_calls(state['messages'][-1]):
        return 'tools'
    else:
        return END

# ── 第 8 步：接线（5 行，缺一行都不对）──────────────────────
# 提示：
#   START → agent_node
#   add_conditional_edges(agent_node, should_continue, {"tools":"tools_node", END:END})
#   tools_node → agent_node   （只要这一条，不要 tools → END）
# TODO
g = StateGraph(State)
g.add_node('agent_node',agent_node)
g.add_node('tools_node',tools_node)
g.add_edge(START,'agent_node')
g.add_conditional_edges('agent_node', should_continue, {"tools":"tools_node", END:END})
g.add_edge('tools_node','agent_node')
app = g.compile()


# ── 第 9 步：invoke ──────────────────────────────────────────
# 提示：{"messages": [{"role":"user", "content":"ENR20250801001 什么状态？"}]}
if __name__ == "__main__":
    # 1. 应触发 tool loop
    print("=== ENR ===")
    print(app.invoke({"messages": [{"role": "user", "content": "ENR20250801001 什么状态？"}]}))

    # 2. 不应调工具
    print("=== 制度 ===")
    print(app.invoke({"messages": [{"role": "user", "content": "开课后退班怎么扣费？"}]}))
