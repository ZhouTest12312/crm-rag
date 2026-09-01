# 数据库导出与服务器导入

本目录 SQL 由本机当前库导出，可直接在香港 ECS 上执行。

## 文件说明

| 文件 | 说明 |
|------|------|
| `mysql_edu_crm_agent.sql` | MySQL 全量：建库 + 7 张表结构 + 演示数据（24 订单等） |
| `pg_edu_crm_vectors.sql` | PostgreSQL 全量：pgvector 扩展 + policy_chunks + 22 条向量 |
| `init_pgvector_schema.sql` | 仅 PG 建表（无数据）；数据用 `practice_pgvector.py --step 6` 灌 |

## 本机重新导出

```powershell
cd D:\workspace\edu-crm-langgraph
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe scripts\export_mysql_sql.py

docker exec edu-crm-langgraph-pgvector-1 pg_dump -U postgres edu_crm_vectors --no-owner --no-privileges -f /tmp/pg_dump.sql
docker cp edu-crm-langgraph-pgvector-1:/tmp/pg_dump.sql scripts/out/pg_edu_crm_vectors.sql
```

---

## 服务器执行 · MySQL

```bash
# 1. 安装 MySQL 8 并启动后
mysql -u root -p < mysql_edu_crm_agent.sql

# 2. 验证
mysql -u root -p -e "USE edu_crm_agent; SELECT COUNT(*) FROM enrollment;"
# 期望：24
```

`.env` 示例：

```env
DATABASE_URL=mysql+aiomysql://root:你的密码@127.0.0.1:3306/edu_crm_agent?charset=utf8mb4
```

---

## 服务器执行 · PostgreSQL (pgvector)

**方式 A：docker compose（推荐，与项目一致）**

```bash
cd ~/crm-rag
docker compose up -d pgvector
# 等 pg 就绪
docker exec -i edu-crm-langgraph-pgvector-1 psql -U postgres < pg_edu_crm_vectors.sql
```

若库名不存在，先：

```bash
docker exec -i edu-crm-langgraph-pgvector-1 psql -U postgres -c "CREATE DATABASE edu_crm_vectors;"
docker exec -i edu-crm-langgraph-pgvector-1 psql -U postgres -d edu_crm_vectors < pg_edu_crm_vectors.sql
```

**方式 B：仅建表 + Python 灌向量**

```bash
docker exec -i ... psql -U postgres < init_pgvector_schema.sql
cd ~/crm-rag && source .venv/bin/activate
export PYTHONPATH=.
python practice/practice_pgvector.py --step 6
```

`.env` 示例：

```env
VECTOR_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/edu_crm_vectors
```

---

## 迁移脚本（空库从零搭，不用 dump 时）

若 MySQL 已有手写仓基础表，只需补扩展表：

```bash
cd ~/crm-rag && source .venv/bin/activate
export PYTHONPATH=.
python scripts/migrate_enrollment_lessons.py
python scripts/migrate_order_source.py
python scripts/migrate_work_orders.py
python scripts/migrate_crm_finance.py
```

基础 student/class/enrollment 需先用手写仓 `POST /api/seed/seed` 或本目录 `mysql_edu_crm_agent.sql`。
