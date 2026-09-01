"""第 1 步起：Postgres + pgvector 连接（你先补 ensure_schema 里的建表 SQL）。"""
from __future__ import annotations

import psycopg
from pgvector.psycopg import register_vector

from utils.setting import settings

# BAAI/bge-small-zh-v1.5 输出 512 维；换模型要改这里和表里的 vector(N)
EMBEDDING_DIM = 512


def connect_vector_db(*, autocommit: bool = True) -> psycopg.Connection:
    # connect_timeout：向量库挂了时别拖死整条问答
    conn = psycopg.connect(
        settings.VECTOR_DATABASE_URL,
        autocommit=autocommit,
        connect_timeout=3,
    )
    try:
        register_vector(conn)
    except psycopg.ProgrammingError:
        # 第 1 步 CREATE EXTENSION 之前库里还没有 vector 类型，先忽略
        pass
    return conn


def ensure_schema(conn: psycopg.Connection | None = None) -> None:
    """第 1 步：在这里写 CREATE EXTENSION + CREATE TABLE。"""
    own = conn is None
    if own:
        conn = connect_vector_db()
    try:
        sql='''
        CREATE EXTENSION IF NOT EXISTS vector;
        CREATE TABLE IF NOT EXISTS policy_chunks (
            id Text primary key,
            source Text not null,
            content Text not null,
            embedding vector(512) not null
        )
        '''
        conn.execute(sql)
        # TODO 你写：CREATE EXTENSION IF NOT EXISTS vector;
        # TODO 你写：CREATE TABLE IF NOT EXISTS policy_chunks (...)
    finally:
        if own:
            conn.close()
