"""
Day 3 复习 · L2：retrieve + call_llm 两节点

跑法（项目根）：
  $env:PYTHONPATH="."
  .venv\\Scripts\\python.exe practice\\practice_l2_review.py

目标：问「开课后退班怎么扣费？」→ context 有制度 → reply 提到扣费相关

图：START → retrieve_node → call_llm → END

卡住报：「Day3 复习 · 第 N 步 · …」
详细提示：docs/PRACTICE_REVIEW.md → Day3 小节
"""
from __future__ import annotations

from typing import TypedDict

from langgraph.constants import END, START
from langgraph.graph import StateGraph

# ── 第 1 步：State 三个字段 ────────────────────────────────
# 提示：user_message, context, reply
class State(TypedDict):
    user_message:str
    context:str
    reply:str


# ── 第 2 步：import ───────────────────────────────────────
# 提示：from services.rag import retrieve
#       from services.llm import chat
# TODO
from services.rag import retrieve
from services.llm import chat
# ── 第 3 步：retrieve_node ──────────────────────────────────
# 提示：
#   hits = retrieve(state["user_message"])
#   context = "\n\n".join(h["text"] for h in hits)
#   return {"context": context}
def retrieve_node(state: State) -> dict:
    hits = retrieve(state['user_message'])
    context = '\n\n'.join(hit['text'] for hit in hits)
    return {"context": context}

# ── 第 4 步：call_llm ───────────────────────────────────────
# 提示：一条 user 消息，content 里拼：
#   「仅依据以下制度回答，不要编造：」+ context + 「用户问题：」+ user_message
def call_llm(state: State) -> dict:
    messages = [
        {
            'role':'user',
            'content':f"「仅依据以下制度回答，不要编造：」"
                      f"{state['context']}"
                      f"「用户问题：」+ {state['user_message']}"
        }
    ]
    answer = chat(messages)
    return {'reply':answer}

# ── 第 5 步：建图（三条边，缺一不可）────────────────────────
# 提示：
#   START → retrieve_node → call_llm → END
# TODO
g = StateGraph(State)
g.add_node('retrieve_node',retrieve_node)
g.add_node('call_llm',call_llm)
g.add_edge(START,'retrieve_node')
g.add_edge('retrieve_node','call_llm')
g.add_edge('call_llm',END)
app = g.compile()

# ── 第 6 步：测试 ───────────────────────────────────────────
if __name__ == "__main__":
    print(app.invoke({"user_message": "开课后退班怎么扣费？"}))
