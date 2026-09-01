"""
Day 2 · L1：单节点调模型（一问一答）

跑法：
  .venv\\Scripts\\python.exe practice\\practice_l1.py

目标：
  输入 {"user_message": "1+1等于几？"}
  经过一个 call_llm 节点
  输出里 reply 是模型回答

和 L0 的差别：节点里调 services.llm.chat，不是改字符串。
"""
from __future__ import annotations

from typing import TypedDict

from langgraph.constants import START,END
from langgraph.graph import StateGraph


# TODO 1：TypedDict 定义 State：user_message: str, reply: str
class State(TypedDict):
    user_message: str
    reply: str
# TODO 2：from services.llm import chat
from services.llm import chat
# TODO 3：def call_llm(state) -> dict:
#         messages = [{"role": "user", "content": state["user_message"]}]
#         answer = chat(messages)
#         return {"reply": answer}
def call_llm(state:State):
    message = [
        {
            'role':'user',
            'content':state['user_message']
        }
    ]
    answer = chat(message)
    return {'reply':answer}
# TODO 4：StateGraph 接线：START → call_llm → END，compile
g = StateGraph(State)
g.add_node('call_llm',call_llm)
g.add_edge(START,'call_llm')
g.add_edge('call_llm',END)
a = g.compile()
# TODO 5：invoke({"user_message": "1+1等于几？"}) 并 print reply
print(a.invoke({"user_message": "1+1等于几？"}))
