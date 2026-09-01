"""
制度 RAG（正在从 pgvector 从零搭）

当前只保留：读 txt、切段、关键词检索。
向量部分在 practice/practice_pgvector.py 里一步步写，写完再合并进本文件。
"""
from __future__ import annotations
from config.vector_db import connect_vector_db
from services.embeddings import embed_query
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
POLICIES_DIR = BASE_DIR / "data" / "policies"


def split_policy(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    raw = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    for part in raw:
        if chunks and len(part) < 40:
            chunks[-1] = chunks[-1] + "\n\n" + part
        else:
            chunks.append(part)
    return chunks


def load_policy_chunks() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    POLICIES_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(POLICIES_DIR.glob("*.txt")):
        body = path.read_text(encoding="utf-8")
        for chunk in split_policy(body):
            pairs.append((path.name, chunk))
    return pairs


def _keyword_score(question: str, text: str) -> int:
    q = question.strip().lower()
    t = text.lower()
    score = 0
    for i in range(len(q)):
        gram = q[i : i + 2]
        if len(gram) < 2:
            continue
        if gram in t:
            score += 1
    for token in (
        "退班", "换班", "转班", "结转", "买班", "早鸟",
        "消课", "排课", "开课前", "开课后",
        "工单", "退款", "优惠券", "现金券", "订单来源", "资源申请",
    ):
        if token in q and token in t:
            score += 5
    return score
MAX_VECTOR_DIST = 0.45
MIN_KEYWORD_SCORE = 3  # 文件顶部常量
def _rank_by_keyword(question: str, top_k: int) -> list[dict]:
    q = question.strip().lower()
    pairs = load_policy_chunks()
    list1 = []

    for src,text in pairs:
        score = _keyword_score(q,text)
        list1.append((score,src,text))
    list1.sort(key=lambda x:x[0],reverse=True)
    results = []
    for score,src,text in list1[:top_k]:
        if score<MIN_KEYWORD_SCORE:
            continue
        results.append({
            'source':src,
            'text':f'[{src}]\n{text}'
        })
        if len(results) >= top_k:
            break
    return results
def _rank_by_vector(question: str, top_k: int) -> list[dict]:
    """向量检索；连接/查询失败时返回空，由关键词兜底。"""
    try:
        q_vec = embed_query(question)
        sql = (
            "select source,content,embedding <=> %s::vector as dist "
            "from policy_chunks order by dist LIMIT %s"
        )
        results = []
        with connect_vector_db() as conn:
            row = conn.execute(sql, (q_vec, top_k)).fetchall()
            for src, text, dist in row:
                if dist > MAX_VECTOR_DIST:
                    continue
                results.append({"source": src, "text": text})
        return results
    except Exception:
        return []


def retrieve(question: str, top_k: int = 4) -> list[dict]:
    """关键词 + 向量（向量失败则只用关键词，避免整链超时）。"""
    keyword_hits = _rank_by_keyword(question, top_k)
    vector_hits = _rank_by_vector(question, top_k)
    if not vector_hits and not keyword_hits:
        return []
    merged = []
    seen = set()
    for key in keyword_hits + vector_hits:
        chunk = key["text"]
        if chunk in seen:
            continue
        merged.append(key)
        seen.add(chunk)
        if len(merged) >= top_k:
            break
    return merged
