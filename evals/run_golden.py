"""
LangGraph 仓 golden 评测（最小 3 条）。

前置（缺一会报错）：
  1. 终端 1 已启动：uvicorn main:app --host 127.0.0.1 --port 8001
  2. .env 里 DEEPSEEK_API_KEY 有效（lg01、lg03 会调模型）
  3. lg03 多轮依赖 session；Redis 可选（无则走内存兜底）

跑法（项目根）：
  .venv\\Scripts\\python.exe evals\\run_golden.py
"""
from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent
GOLDEN_PATH = ROOT / "golden.json"


def load_golden() -> dict:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def chat(client: httpx.Client, base: str, question: str, session_id: str,headers=None) -> dict:
    """调 POST /api/chat；失败时抛出带 response 正文的异常，方便排查 500。"""
    try:
        r = client.post(
            f"{base}/api/chat",
            json={"question": question, "session_id": session_id},
            headers={"Content-Type": "application/json", **(headers or {})},
            timeout=120.0,
        )
    except httpx.ConnectError as e:
        raise RuntimeError(
            f"连不上 {base}，请先启动：uvicorn main:app --host 127.0.0.1 --port 8001"
        ) from e

    if r.status_code >= 400:
        body = r.text[:500]
        raise RuntimeError(f"HTTP {r.status_code}: {body}")

    return r.json()

def contains_none(text: str, forbidden: list[str] | None) -> bool:
    if not forbidden:
        return True
    return not any(f in text for f in forbidden)
def contains_any(text: str, needles: list[str] | None) -> bool:
    if not needles:
        return True
    return any(n in text for n in needles)


def run_case(client: httpx.Client, base: str, case: dict) -> tuple[bool, str]:
    headers = case.get("headers") or {}
    cid = case["id"]
    expect = case.get("expect") or {}
    session_id = f"golden-{cid}-{uuid.uuid4().hex[:8]}"

    try:
        if case.get("follow_up"):
            # lg03：同一 session 问两句，测多轮
            chat(client, base, case["question"], session_id,headers)
            resp = chat(client, base, case["follow_up"], session_id,headers)
        else:
            resp = chat(client, base, case["question"], session_id,headers)
    except RuntimeError as e:
        return False, str(e)

    answer = resp.get("answer") or ""
    if not contains_any(answer, expect.get("answer_contains_any")):
        return False, f"answer 未命中关键词: {answer[:200]}"
    if not contains_none(answer, expect.get("answer_must_not_contain")):
        return False, f"answer 含禁词: {answer[:200]}"
    return True, "ok"


def main() -> int:
    data = load_golden()
    base = data.get("base_url", "http://127.0.0.1:8000")
    cases = data.get("cases") or []
    passed = 0
    with httpx.Client() as client:
        for case in cases:
            ok, msg = run_case(client, base, case)
            mark = "PASS" if ok else "FAIL"
            print(f"[{mark}] {case['id']}: {msg}")
            if ok:
                passed += 1
            time.sleep(0.5)

    print(f"\n=== {passed}/{len(cases)} passed ===")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
