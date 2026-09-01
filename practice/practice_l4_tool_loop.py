"""
Day 9 · L4：LLM 决定是否调工具（mini tool loop）

跑法（项目根）：
  $env:PYTHONPATH="."
  .venv\\Scripts\\python.exe practice\\practice_l4_tool_loop.py

目标：
  问「ENR20250801001 什么状态？」→ 模型返回 tool_call → 执行 lookup → 再调模型 → 最终 reply
  问「开课后退班怎么扣费？」→ 无 tool_call → 直接文字回答（可先不调 RAG，Day9 只练 loop）

对照手写：edu-crm-agent/services/crm_tools.py → run_tool_loop
LangGraph 做法：agent 节点 ↔ tools 节点 用条件边循环（比 Day4 规则分流更接近手写）

图示意：
  START → agent ──有 tool_calls──→ tools ──→ agent
              └──无 tool_calls──→ END
"""
from __future__ import annotations

import json
from typing import TypedDict, Annotated

from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages

from services.tools import lookup_order


# TODO 1：State 至少含 messages: list（每条 OpenAI 格式 dict）
#         可用 TypedDict，或 from langgraph.graph.message import add_messages 的 Annotated
class State(TypedDict):
    messages:  Annotated[list, add_messages]


from services.llm import chat_message

# TODO 2：from services.llm import chat_message  （Day9 先在 llm.py 实现）
# TODO 3：定义 tools  schema（OpenAI 格式 list[dict]），工具名 lookup_order，参数 order_no
#         执行仍调 services.tools.lookup_order
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
]


# TODO 4：def agent_node(state) -> dict:
#         resp = chat_message(state["messages"], tools=TOOLS_SCHEMA)
#         return {"messages": [resp 转成 dict]}   # 含 tool_calls 或 content
def agent_node(state) -> dict:
    resp = chat_message(state["messages"], tools=TOOLS_SCHEMA)
    assistant = {
        'role':'assistant',
        'content':resp.content or ''
    }
    if resp.tool_calls:
        assistant['tool_calls'] =  [
                {
                    'id': tc.id,
                    'type': 'function',
                    'function': {
                        'name': tc.function.name,
                        'arguments': tc.function.arguments
                    }
                }
                for tc in resp.tool_calls
            ]

    return {"messages": [assistant]}  # 含 tool_calls 或 content


# TODO 5：def tools_node(state) -> dict:
#         读最后一条 assistant 的 tool_calls，执行 lookup_order，return ToolMessage 格式 dict
def _tool_calls(last):
    if isinstance(last, dict):
        return last.get("tool_calls") or []
    return getattr(last, "tool_calls", None) or []


def tools_node(state) -> dict:
    last = state['messages'][-1]
    list1 = []
    for tc in _tool_calls(last):
        if "function" in tc:
            args = json.loads(tc["function"]["arguments"] or "{}")
            tc_id = tc["id"]
        else:
            args = tc.get("args") or {}
            tc_id = tc["id"]
        order_no = args.get('order_no')
        result = lookup_order(order_no)
        list1.append({
            'role': 'tool',
            'content': json.dumps(result, ensure_ascii=False),
            'tool_call_id': tc_id
        })
    return {'messages': list1}


# TODO 6：def should_continue(state) -> str:
#         最后一条 message 有 tool_calls → "tools"，否则 END
def should_continue(state) -> str:
    if _tool_calls(state['messages'][-1]):
        return 'tools'
    return END


# TODO 7：接线 + compile，invoke 测 ENR 问题
g = StateGraph(State)
g.add_node('agent_node', agent_node)
g.add_node('tools_node', tools_node)
g.add_edge(START,'agent_node')
g.add_conditional_edges('agent_node',should_continue,{
    'tools':'tools_node',
    END:END
})
g.add_edge("tools_node", "agent_node")
app = g.compile()
print(app.invoke(
    {'messages':
        [
            {
                "role": "user",
                "content": "ENR20250801001 什么状态？"
            }
        ]
    }
))
