"""POST /api/chat 请求/响应模型。"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: str | None = None  # Day 6 再用


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict] = []  # 可选：retrieve 命中时可填


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[dict] = []

