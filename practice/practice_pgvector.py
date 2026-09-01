"""
pgvector 从零练习 — 按步骤填空，每步跑通再下一步。

运行方式（在项目根目录）：
  .\\.venv\\Scripts\\python.exe practice/practice_pgvector.py

或只跑某一步：
  .\\.venv\\Scripts\\python.exe practice/practice_pgvector.py --step 1
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from services.embeddings import embed_texts, embed_query
from services.rag import load_policy_chunks
# 保证能 import 项目包
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.vector_db import EMBEDDING_DIM, connect_vector_db  # noqa: E402
from pgvector.psycopg import register_vector  # noqa: E402


# ---------------------------------------------------------------------------
# 第 1 步：建表
# ---------------------------------------------------------------------------
def step1_create_table() -> None:
    """
    SQL 必须写在 ddl 的三引号字符串里，不能写在函数体当 Python 代码。

    错误示范（会 SyntaxError）：
        CREATE TABLE policy_chunks (...);   # ← 这不是 Python

    正确示范：
        ddl = '''
        CREATE EXTENSION IF NOT EXISTS vector;
        CREATE TABLE ...
        '''
        conn.execute(ddl)
    """
    ddl = """
    CREATE EXTENSION IF NOT EXISTS vector;

    CREATE TABLE IF NOT EXISTS policy_chunks (
        id        TEXT PRIMARY KEY,
        source    TEXT NOT NULL,
        content   TEXT NOT NULL,
        embedding vector(512) NOT NULL
    );
    """

    with connect_vector_db() as conn:
        conn.execute(ddl)
        register_vector(conn)  # EXTENSION 建好后注册 vector 类型
    print("[OK] step1: policy_chunks created")


# ---------------------------------------------------------------------------
# 第 2 步：查表是否存在
# ---------------------------------------------------------------------------
def step2_count_rows() -> None:
    """SELECT COUNT(*) FROM policy_chunks — 现在应该是 0"""
    with connect_vector_db() as conn:
        n = conn.execute("SELECT COUNT(*) FROM policy_chunks").fetchone()[0]
    print(f"[OK] step2: row count = {n} (new table should be 0)")


# ---------------------------------------------------------------------------
# 第 3 步：测 embedding —— 你来写 step3_test_embedding 函数体
# ---------------------------------------------------------------------------
def step3_test_embedding() -> None:
    """
    目标：把一句话变成 512 个浮点数，并 print 长度。

    提示见 BUILD 或对话里的第 3 步引导；不要抄完整答案，自己敲。
    """
    text = "开课后退班怎么扣费"
    # TODO 你写：
    from services.embeddings import embed_query
    vec = embed_query(text)
    print(len(vec))
    # 1. from services.embeddings import embed_query   （先实现 embeddings.py）
    # 2. vec = embed_query("开课后退班怎么扣费")
    # 3. print(len(vec))  应为 512


# ---------------------------------------------------------------------------
# 第 4 步：INSERT 一条 —— 下一课再开
# ---------------------------------------------------------------------------
def step4_insert_one_row() -> None:
    pairs = load_policy_chunks()
    source,body = pairs[0]
    content = f'[{source}]\n{body}'
    chunk_id = f'{source}-0'
    vec = embed_texts([content])[0]
    sql = 'insert into policy_chunks (id,source,content,embedding) values (%s,%s,%s,%s)'
    with connect_vector_db() as conn:
        conn.execute(sql,(chunk_id,source,content,vec))
    print("[OK] step4: inserted 1 row")
# ---------------------------------------------------------------------------
# 第 5 步：向量检索 —— 再下一课
# ---------------------------------------------------------------------------
def step5_vector_search() -> None:
    question = "开课后退班怎么扣费"
    q_vec = embed_query(question)
    sql='select source,content from policy_chunks order by embedding <=> %s::vector LIMIT 1'
    with connect_vector_db() as conn:
        row =conn.execute(sql, (q_vec,)).fetchone()
    if row is None:
        print("no rows — 先跑 step4 插数据，或 step2 看 count 是否 > 0")
    else:
        source, content = row
        print("question:", question)
        print("source:", source)
        print("content:", content)
        print("[OK] step5 done")
def step6_seed_all():
    pairs = load_policy_chunks()
    documents = [f'[{src}]\n{text}' for src,text in pairs]
    ids = [f"{src}-{i}"for i,(src,text) in enumerate(pairs)]
    vec = embed_texts(documents)
    source = [src for src,text in pairs]
    sql_del='DELETE FROM policy_chunks'
    sql = 'insert into policy_chunks (id,source,content,embedding) values (%s,%s,%s,%s)'
    with connect_vector_db() as conn:
        conn.execute(sql_del)
        for cid, src, doc, v in zip(ids, source, documents, vec):
            conn.execute(sql, (cid, src, doc, v))
    print(f"[OK] step6: inserted {len(documents)} rows")
STEPS = {
    1: ("建表", step1_create_table),
    2: ("数行数", step2_count_rows),
    3: ("测 embedding", step3_test_embedding),
    4: ("插 1 条", step4_insert_one_row),
    5: ("向量检索", step5_vector_search),
6: ("灌全库", step6_seed_all),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=int, default=1, help="只跑第 N 步，默认 1")
    args = parser.parse_args()
    title, fn = STEPS.get(args.step, ("?", lambda: print("未知步骤")))
    print(f"--- 第 {args.step} 步：{title} ---")
    fn()


if __name__ == "__main__":
    main()
