"""
Day 2 复习 · L1：单节点调模型

跑法（项目根）：
  $env:PYTHONPATH="."
  .venv\\Scripts\\python.exe practice\\practice_l1_review.py

目标：{"user_message": "1+1等于几？"} → call_llm 节点 → reply 是模型回答

卡住报：「Day2 复习 · 第 N 步 · …」
详细提示：docs/PRACTICE_REVIEW.md → Day2 小节
"""
from __future__ import annotations

from typing import TypedDict

from langgraph.constants import END, START
from langgraph.graph import StateGraph

# ── 第 1 步：State ─────────────────────────────────────────
# 提示：两个字段 user_message（用户问什么）、reply（模型答什么）
class State(TypedDict):
    user_message: str
    reply: str


# ── 第 2 步：import chat ───────────────────────────────────
# 提示：from services.llm import chat
# TODO
from services.llm import chat

# ── 第 3 步：call_llm 节点 ─────────────────────────────────
# 提示：
#   messages = [{"role": "user", "content": state["user_message"]}]
#   answer = chat(messages)
#   return {"reply": answer}    ← 必须 return dict，键名和 State 字段一致
def call_llm(state: State) -> dict:
    messages = [
        {
            'role':'user',
            'content':state['user_message']
        }
    ]
    answer = chat(messages)
    return {'reply':answer}

# ── 第 4 步：建图 ───────────────────────────────────────────
# 提示：
g = StateGraph(State)
g.add_node("call_llm", call_llm)
g.add_edge(START, "call_llm")
g.add_edge("call_llm", END)
app = g.compile()
# TODO


# ── 第 5 步：invoke 测试 ───────────────────────────────────
# 提示：print(app.invoke({"user_message": "1+1等于几？"}))
# 过关：终端能看到 reply 里是「2」或类似回答
if __name__ == "__main__":
    print(app.invoke({"user_message": "1+1等于几？"}))
