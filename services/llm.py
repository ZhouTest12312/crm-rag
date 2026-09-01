"""
Day 2 · DeepSeek 调用（OpenAI 兼容）

对照（只读）：D:\\workspace\\edu-crm-agent\\services\\llm.py
Day 2 只需 chat()；tools / stream 后面再用。
"""
from __future__ import annotations

# TODO 1：from openai import OpenAI
from openai import OpenAI
from langchain_core.messages import convert_to_openai_messages
# TODO 2：from utils.setting import settings
from utils.setting import settings

# TODO 3：检查 settings.DEEPSEEK_API_KEY 为空则 raise（或 import 时 SystemExit 提示填 .env）

if not settings.DEEPSEEK_API_KEY:
    raise SystemExit(
        '没有获取到DEEPSEEK_API_KEY'
    )
# TODO 4：_client = OpenAI(api_key=..., base_url=settings.DEEPSEEK_BASE_URL)
_client = OpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_BASE_URL)


# TODO 5：def chat(messages: list[dict], model: str | None = None, temperature: float = 0) -> str:
def chat(messages: list[dict], model: str | None = None, temperature: float = 0) -> str:
    data = _client.chat.completions.create(
        messages=messages,
        model=model or settings.DEEPSEEK_MODEL,
        temperature=temperature,
    )
    return data.choices[0].message.content or ''

# Day 9：返回完整 message（含 tool_calls），对照 edu-crm-agent chat_message
def chat_message(messages, tools=None, model=None, temperature=0):
    # LangGraph add_messages 会把 dict 变成 HumanMessage/AIMessage，API 需要 OpenAI dict
    openai_messages = convert_to_openai_messages(messages)
    kwargs = {
        "model": model or settings.DEEPSEEK_MODEL,
        "messages": openai_messages,
        "temperature": temperature,
    }
    if tools:
        kwargs["tools"] = tools
    return _client.chat.completions.create(**kwargs).choices[0].message
def stream_chat(messages, tools=None,model=None, temperature: float = 0):
    # LangGraph add_messages 会把 dict 变成 HumanMessage/AIMessage，API 需要 OpenAI dict
    openai_messages = convert_to_openai_messages(messages)
    kwargs = {
        "model": model or settings.DEEPSEEK_MODEL,
        "messages": openai_messages,
        "temperature": temperature,
        'stream':True
    }
    if tools:
        kwargs["tools"] = tools
    chunks =  _client.chat.completions.create(**kwargs)
    for chunk in chunks:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta

#调 _client.chat.completions.create，return 助手 content 字符串

