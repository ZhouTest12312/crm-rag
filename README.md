# edu-crm-langgraph

教培 CRM 教务助手 · **LangGraph** 编排版。

**每天只打开 [`BUILD.md`](BUILD.md)。**

手写对照仓：`D:\workspace\edu-crm-agent`（只读参考，勿混改）。

## 启动

### 1. Redis（多轮会话）

```powershell
cd D:\workspace\edu-crm-langgraph
docker compose up -d
```

### 2. 后端

```powershell
.\.venv\Scripts\uvicorn.exe main:app --host 127.0.0.1 --port 8001
```

### 3. 前端（二选一）

**开发（热更新，推荐）：**

```powershell
cd frontend
npm install
npm run dev
```

浏览器：http://127.0.0.1:5173（Vite 代理 `/api` → 8001）

**生产（由 FastAPI 托管静态页）：**

```powershell
cd frontend
npm install
npm run build
```

再启动后端，浏览器：http://127.0.0.1:8001/

## 接口

- Health: http://127.0.0.1:8001/health
- Chat API: `POST /api/chat` · body `{"question":"...", "session_id":"..."}`
- Swagger: http://127.0.0.1:8001/docs
