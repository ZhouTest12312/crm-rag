-- edu_crm_vectors · pgvector 建库脚本（仅结构，不含向量数据）
-- 若要从本机完整拷贝含 22 条制度向量，请用 pg_edu_crm_vectors.sql

CREATE DATABASE edu_crm_vectors;
\c edu_crm_vectors

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS policy_chunks (
    id        TEXT PRIMARY KEY,
    source    TEXT NOT NULL,
    content   TEXT NOT NULL,
    embedding vector(512) NOT NULL
);

-- 灌向量数据（在项目根目录、.env 配好 VECTOR_DATABASE_URL 后）：
--   python practice/practice_pgvector.py --step 6
