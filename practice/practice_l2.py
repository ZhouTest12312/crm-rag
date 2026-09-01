"""
Day 3 · L2：retrieve 节点 + 制度进 State + 再调 LLM

跑法：
  .venv\\Scripts\\python.exe practice\\practice_l2.py

目标：
  问「开课后退班怎么扣费？」
  retrieve 把制度片段写入 State.context
  call_llm 带着 context 回答，reply 里能提到扣费/服务费等制度要点

图：START → retrieve → call_llm → END
"""
from __future__ import annotations

from typing import TypedDict

from langgraph.graph import StateGraph,START,END


# TODO 1：State 字段：user_message: str, context: str, reply: str
class State(TypedDict):
    user_message: str
    context: str
    reply: str
# TODO 2：from services.rag import retrieve
from services.rag import retrieve
# TODO 3：from services.llm import chat
from services.llm import chat
# TODO 4：def retrieve_node(state) -> dict:
#         hits = retrieve(state["user_message"])
#         context = "\\n\\n".join(h["text"] for h in hits)  或类似
#         return {"context": context}
def retrieve_node(state) -> dict:
    hits = retrieve(state['user_message'])
    context = '\n\n'.join(h['text'] for h in hits)
    return {'context':context}
# TODO 5：def call_llm(state) -> dict:
#         把 context 拼进 prompt（system 或 user 里写清「仅依据以下制度回答」）
#         answer = chat(messages)
#         return {"reply": answer}
def call_llm(state) -> dict:
#         把 context 拼进 prompt（system 或 user 里写清「仅依据以下制度回答」）
        messages = [
            {
                'role': 'user',
                'content':(
                    f"仅依据以下制度回答，不要编造：\n\n"
                    f"{state['context']}\n\n"
                    f"用户问题：{state['user_message']}"
                )
            }

        ]
        answer = chat(messages)
        return {"reply": answer}
# TODO 6：StateGraph 两节点接线，compile
g = StateGraph(State)
g.add_node('retrieve_node',retrieve_node)
g.add_node('call_llm',call_llm)
g.add_edge(START,'retrieve_node')
g.add_edge('retrieve_node','call_llm')
g.add_edge('call_llm',END)
app = g.compile()
# TODO 7：invoke 退班问题，print reply（可顺带 print context 自检）
print(app.invoke({'user_message':'退班问题'}))
