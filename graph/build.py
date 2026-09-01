"""编译 StateGraph，对外暴露 graph app。"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import END, START
from langgraph.graph import StateGraph

from graph.nodes import (
    agent_node,
    cancel_confirm_node,
    write_confirm_node,
    retrieve_node,
    route_entry,
    should_continue,
    tools_node,
)
from graph.state import State


def build_graph():
    memory = MemorySaver()
    g = StateGraph(State)
    g.add_node("retrieve", retrieve_node)
    g.add_node("agent", agent_node)
    g.add_node("tools", tools_node)
    g.add_node("cancel_confirm", cancel_confirm_node)
    g.add_node("write_confirm", write_confirm_node)
    # START 只能有一条出路：用条件边分流，不要再 add_edge(START, ...)
    g.add_conditional_edges(START, route_entry, {
        "cancel_confirm": "cancel_confirm",
        "write_confirm": "write_confirm",
        "retrieve": "retrieve",
    })
    g.add_edge("retrieve", "agent")
    g.add_conditional_edges("agent", should_continue, {
        "tools": "tools",
        END: END,
    })
    g.add_edge("tools", "agent")
    g.add_edge("cancel_confirm", END)
    g.add_edge("write_confirm", END)
    return g.compile(checkpointer=memory)


graph_app = build_graph()
