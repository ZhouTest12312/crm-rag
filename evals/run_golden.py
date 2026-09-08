"""
LangGraph 仓 golden 评测：固定题单 + 弱断言 + 量化汇总。

前置：
  1. 后端已起：uvicorn main:app --host 127.0.0.1 --port 8000（或 golden.json base_url）
  2. .env 里 DEEPSEEK_API_KEY 有效（制度/多轮会调模型）
  3. 多轮依赖 session；Redis 可选（无则内存兜底）

跑法（项目根）：
  .venv\\Scripts\\python.exe evals\\run_golden.py
  .venv\\Scripts\\python.exe evals\\run_golden.py --tag policy
  .venv\\Scripts\\python.exe evals\\run_golden.py --id lg01_policy_refund
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from collections import defaultdict
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent
GOLDEN_PATH = ROOT / "golden.json"


def load_golden() -> dict:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def chat(client: httpx.Client, base: str, question: str, session_id: str, headers=None) -> dict:
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
            f"连不上 {base}，请先启动：uvicorn main:app --host 127.0.0.1 --port 8000"
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


def keyword_hits(text: str, needles: list[str] | None) -> tuple[int, int]:
    """返回 (命中数, 期望数)；无期望则 (0, 0)。"""
    if not needles:
        return 0, 0
    hit = sum(1 for n in needles if n in text)
    return hit, len(needles)


def source_names(resp: dict) -> list[str]:
    sources = resp.get("sources") or []
    return [str(s.get("source") or "") for s in sources]


def sources_text(resp: dict) -> str:
    sources = resp.get("sources") or []
    return " ".join(str(s.get("text") or "") for s in sources)


def check_retrieval(resp: dict, expect: dict) -> dict:
    """
    企业口径：文档召回 / 片段召回分开；缺期望则不计入分母。
    默认只看 source 文件名，不扫正文（避免虚高）。
    """
    out = {
        "doc_ok": None,
        "chunk_ok": None,
        "msg": "n/a",
        "n_sources": len(resp.get("sources") or []),
    }
    src_needles = expect.get("sources_source_contains_any")
    text_any = expect.get("sources_text_contains_any")
    text_all = expect.get("sources_text_contains_all")
    if not src_needles and not text_any and not text_all:
        return out

    names = source_names(resp)
    blob_names = " ".join(names)
    text = sources_text(resp)
    msgs: list[str] = []

    if src_needles:
        if not names:
            out["doc_ok"] = False
            msgs.append("sources 为空")
        else:
            hit = any(n in blob_names for n in src_needles)
            out["doc_ok"] = hit
            if not hit:
                msgs.append(f"文档未命中 {src_needles!r}；实际={names!r}")

    if text_any or text_all:
        if not text.strip():
            out["chunk_ok"] = False
            msgs.append("chunk 正文为空")
        else:
            ok_any = True if not text_any else any(n in text for n in text_any)
            ok_all = True if not text_all else all(n in text for n in text_all)
            out["chunk_ok"] = bool(ok_any and ok_all)
            if not out["chunk_ok"]:
                msgs.append(
                    f"片段未覆盖事实 any={text_any!r} all={text_all!r}"
                )

    out["msg"] = "; ".join(msgs) if msgs else "ok"
    return out


def run_case(client: httpx.Client, base: str, case: dict) -> dict:
    headers = case.get("headers") or {}
    cid = case["id"]
    expect = case.get("expect") or {}
    session_id = f"golden-{cid}-{uuid.uuid4().hex[:8]}"
    t0 = time.perf_counter()
    row = {
        "id": cid,
        "tag": case.get("tag") or "untagged",
        "ok": False,
        "ms": 0,
        "msg": "",
        "kw_hit": 0,
        "kw_total": 0,
        "doc_ok": None,
        "chunk_ok": None,
        "retrieval_ok": None,  # True/False/None 综合（有一项期望则须全过）
        "retrieval_msg": "n/a",
        "n_sources": 0,
    }

    try:
        if case.get("follow_up"):
            chat(client, base, case["question"], session_id, headers)
            resp = chat(client, base, case["follow_up"], session_id, headers)
        else:
            resp = chat(client, base, case["question"], session_id, headers)
    except RuntimeError as e:
        row["ms"] = int((time.perf_counter() - t0) * 1000)
        row["msg"] = str(e)
        return row

    answer = resp.get("answer") or ""
    row["ms"] = int((time.perf_counter() - t0) * 1000)
    row["kw_hit"], row["kw_total"] = keyword_hits(
        answer, expect.get("answer_contains_any")
    )

    errors: list[str] = []
    if not contains_any(answer, expect.get("answer_contains_any")):
        errors.append(f"answer 未命中关键词: {answer[:200]}")
    if not contains_none(answer, expect.get("answer_must_not_contain")):
        errors.append(f"answer 含禁词: {answer[:200]}")

    ret = check_retrieval(resp, expect)
    row["doc_ok"] = ret["doc_ok"]
    row["chunk_ok"] = ret["chunk_ok"]
    row["n_sources"] = ret["n_sources"]
    scored = [v for v in (ret["doc_ok"], ret["chunk_ok"]) if v is not None]
    if scored:
        row["retrieval_ok"] = all(scored)
        row["retrieval_msg"] = ret["msg"]
    else:
        row["retrieval_ok"] = None
        row["retrieval_msg"] = "n/a"

    # 默认：检索失败不挡答案通过率（企业两套指标）。显式打开才挡。
    if expect.get("fail_on_retrieval_miss") and row["retrieval_ok"] is False:
        errors.append(f"检索召回失败: {row['retrieval_msg']}")

    if errors:
        row["msg"] = "; ".join(errors)
        row["ok"] = False
    else:
        row["msg"] = "ok"
        row["ok"] = True
    return row


def _pct(num: int, den: int) -> float:
    return (num / den * 100.0) if den else 0.0


def print_metrics(rows: list[dict]) -> None:
    total = len(rows)
    passed = sum(1 for r in rows if r["ok"])
    failed = total - passed
    ms_list = [r["ms"] for r in rows]
    avg_ms = int(sum(ms_list) / total) if total else 0

    by_tag: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_tag[r["tag"]].append(r)

    doc_rows = [r for r in rows if r.get("doc_ok") is not None]
    doc_ok = sum(1 for r in doc_rows if r.get("doc_ok"))
    chunk_rows = [r for r in rows if r.get("chunk_ok") is not None]
    chunk_ok = sum(1 for r in chunk_rows if r.get("chunk_ok"))
    ret_rows = [r for r in rows if r["retrieval_ok"] is not None]
    ret_ok = sum(1 for r in ret_rows if r["retrieval_ok"])
    kw_hit = sum(r["kw_hit"] for r in rows)
    kw_total = sum(r["kw_total"] for r in rows)

    print("\n=== 量化结果（答案通过率 ≠ 检索召回率） ===")
    print(f"总用例           {total}")
    print(f"通过率 pass_rate {passed}/{total}  {_pct(passed, total):.1f}%")
    print(f"失败             {failed}")
    print(f"平均耗时         {avg_ms} ms")
    if doc_rows:
        print(
            f"文档召回 doc_recall   {doc_ok}/{len(doc_rows)}  "
            f"{_pct(doc_ok, len(doc_rows)):.1f}%"
            "  （只比 source 文件名，不扫正文）"
        )
    if chunk_rows:
        print(
            f"片段召回 chunk_recall {chunk_ok}/{len(chunk_rows)}  "
            f"{_pct(chunk_ok, len(chunk_rows)):.1f}%"
            "  （top_k 正文须含关键事实，贴近企业 RAG）"
        )
    if ret_rows:
        print(
            f"综合检索召回         {ret_ok}/{len(ret_rows)}  "
            f"{_pct(ret_ok, len(ret_rows)):.1f}%"
        )
    if not doc_rows and not chunk_rows:
        print("检索召回率           n/a  （本批无 sources 期望）")
    if kw_total:
        print(
            f"关键词命中率     {kw_hit}/{kw_total}  "
            f"{_pct(kw_hit, kw_total):.1f}%"
            "  （answer_contains_any 微平均）"
        )

    print("\n分 tag 通过率:")
    for tag in sorted(by_tag.keys()):
        group = by_tag[tag]
        ok = sum(1 for r in group if r["ok"])
        print(f"  {tag:<10} {ok}/{len(group)}  {_pct(ok, len(group)):.1f}%")

    failed_ids = [r["id"] for r in rows if not r["ok"]]
    if failed_ids:
        print("\n失败用例 id:")
        for cid in failed_ids:
            print(f"  - {cid}")
    miss_ret = [r["id"] for r in rows if r.get("retrieval_ok") is False]
    if miss_ret:
        print("\n检索未命中（不挡 pass_rate，除非 fail_on_retrieval_miss）:")
        for cid in miss_ret:
            print(f"  - {cid}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run edu-crm-langgraph golden eval")
    parser.add_argument("--base", default=None, help="API base URL")
    parser.add_argument("--tag", default=None, help="只跑某个 tag")
    parser.add_argument("--id", default=None, help="只跑某个 case id")
    parser.add_argument("--fail-fast", action="store_true", help="第一例失败就停")
    parser.add_argument(
        "--json-out",
        default=None,
        help="把逐条结果与汇总写到 JSON 文件",
    )
    args = parser.parse_args()

    data = load_golden()
    base = (args.base or data.get("base_url") or "http://127.0.0.1:8000").rstrip("/")
    cases = list(data.get("cases") or [])
    if args.tag:
        cases = [c for c in cases if c.get("tag") == args.tag]
    if args.id:
        cases = [c for c in cases if c.get("id") == args.id]
    if not cases:
        print("没有匹配的用例")
        return 1

    print(f"=== Golden 评测 · {len(cases)} 例 · {base} ===")
    rows: list[dict] = []
    with httpx.Client() as client:
        try:
            h = client.get(f"{base}/health", timeout=5.0)
            h.raise_for_status()
        except Exception as e:
            print(f"[FATAL] 无法连接 {base}/health：{e}")
            return 2

        for i, case in enumerate(cases, 1):
            row = run_case(client, base, case)
            rows.append(row)
            mark = "PASS" if row["ok"] else "FAIL"
            ret = ""
            if row["retrieval_ok"] is not None:
                bits = []
                if row.get("doc_ok") is not None:
                    bits.append("doc=" + ("Y" if row["doc_ok"] else "N"))
                if row.get("chunk_ok") is not None:
                    bits.append("chunk=" + ("Y" if row["chunk_ok"] else "N"))
                ret = " " + " ".join(bits)
            print(
                f"[{i}/{len(cases)}] [{mark}] {row['id']} "
                f"({row['ms']}ms) tag={row['tag']}{ret}: {row['msg']}"
            )
            if not row["ok"] and args.fail_fast:
                break
            time.sleep(0.3)

    print_metrics(rows)

    if args.json_out:
        payload = {
            "base_url": base,
            "total": len(rows),
            "passed": sum(1 for r in rows if r["ok"]),
            "pass_rate": _pct(sum(1 for r in rows if r["ok"]), len(rows)),
            "retrieval": {
                "doc_scored": sum(1 for r in rows if r.get("doc_ok") is not None),
                "doc_ok": sum(1 for r in rows if r.get("doc_ok") is True),
                "chunk_scored": sum(1 for r in rows if r.get("chunk_ok") is not None),
                "chunk_ok": sum(1 for r in rows if r.get("chunk_ok") is True),
                "scored": sum(1 for r in rows if r["retrieval_ok"] is not None),
                "ok": sum(1 for r in rows if r["retrieval_ok"] is True),
            },
            "cases": rows,
        }
        out = Path(args.json_out)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n已写入 {out}")

    return 0 if all(r["ok"] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
