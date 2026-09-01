"""
Day 1 · L0：最小 StateGraph（无 LLM）

跑法：
  .venv\\Scripts\\python.exe practice\\practice_l0.py

目标：
  输入 {"text": "同学"}
  经过 add_hello → add_bye
  输出里带「你好」和「再见」

口诀：State → 两个 node 函数 → StateGraph 接线 → compile → invoke
"""
from __future__ import annotations

from typing import TypedDict

# TODO 1：从 langgraph.graph 导入 StateGraph、END（或 START，视你安装的文档）
from langgraph.graph import StateGraph, END, START


# TODO 2：用 TypedDict 定义 State，字段至少 text: str
class State(TypedDict):
    text: str


# TODO 3：写 def add_hello(state) -> dict:  在 text 前加「你好，」
def add_hello(state: State) -> dict:
    return {'text': '你好，' + state['text']}


# TODO 4：写 def add_bye(state) -> dict:    在 text 后加「。再见」
def add_bye(state: State) -> dict:
    return {"text":state['text'] + '。再见'}


# TODO 5：建图：add_node ×2，入口 hello，边 hello→bye→END，compile
g = StateGraph(State)
g.add_node("add_hello", add_hello)
g.add_node("add_bye", add_bye)
g.add_edge(START, "add_hello")
g.add_edge("add_hello", "add_bye")
g.add_edge("add_bye", END)
app = g.compile()
# TODO 6：invoke 并 print
print(app.invoke({"text": "同学"}))
