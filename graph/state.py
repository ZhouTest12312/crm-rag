"""LangGraph State 定义。Day 5 从 practice 迁到这里。"""
from __future__ import annotations

from typing import TypedDict, Annotated

from langgraph.graph import add_messages


# TODO：字段至少 user_message, reply
#       若合并 Day3+Day4，还可加 context: str
class State(TypedDict):
    user_message:str
    reply:str
    context:str
    role:str
    messages: Annotated[list,add_messages]