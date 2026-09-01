# edu-crm-langgraph · 搭建路线（唯一入口）

> **规则**
> - 每天约 **5 小时**；只推进 **当前 Day / 当前步**，跑绿再下一步。
> - **你亲手写业务代码**；助手只给：本步目标、对照、卡住时下一行提示（不整文件代写，除非你说「给对照一小段」）。
> - 卡住只报：**Day几 + 文件 + 行号/报错**。
> - 对照仓（手写版，只读）：`D:\workspace\edu-crm-agent`  
> - 学习入口：本文件。总路线见 `D:\workspace\learningAi\LEARNING.md`。

---

## 项目一句话

教培 CRM 教务助手（**LangGraph 编排**）：制度 RAG + 工具查单 + FastAPI；与手写版同业务，框架换成图编排。

---

## 时间重算（按每天 5 小时）

| 阶段 | 内容 | 日历 |
|------|------|------|
| **Day 1** | 环境 + L0 最小图（无 LLM）+ health | 1 天 |
| **Day 2** | L1：State + DeepSeek 一问一答节点 | 1 天 |
| **Day 3** | L2：retrieve 节点 + 制度进 State | 1 天 |
| **Day 4** | L3：工具节点 + conditional_edges（查订单） | 1 天 |
| **Day 5** | L3 收尾 + FastAPI `POST /api/chat` 跑通图 | 1 天 |
| **Day 6** | Redis 会话 / 多轮；可选 checkpointer | 1 天 |
| **Day 7** | 前端最小页 + Compose Redis + README | 1 天 |
| **Day 8**（缓冲） | 修坑、半页对照表、1 条 golden | 1 天 |

**弄懂并主链路可演示：约 7～8 天（35～40 小时）。**  
JWT/RBAC/取消确认/完整 golden：放到 **Day 9+**，不挡「会用 LangGraph」。

背面试题：建议 **Day 8 之后**或每天收工前 30 分钟，不与写图抢同一整块时间。

**学习计时：** 说「开始学习了」/「收工」→ 助手更新 [`docs/STUDY_LOG.md`](docs/STUDY_LOG.md) 并汇报时长。

---

## 目标技术栈

| 层 | 技术 |
|----|------|
| 编排 | **LangGraph**（主框架） |
| Web | FastAPI |
| 模型 | DeepSeek（OpenAI 兼容） |
| 检索 | **Postgres + pgvector**（制度）；本地 BGE embedding |
| 业务库 | MySQL（与 edu-crm-agent 共用 edu_crm_agent） |
| 会话 | Redis |
| 配置 | pydantic-settings + `.env` |

---

## 目标目录（搭完后）

```
edu-crm-langgraph/
├── BUILD.md                 # 本文件
├── README.md
├── requirements.txt
├── .env.example
├── docker-compose.yml       # Redis + pgvector
├── main.py
├── config/
├── utils/
│   └── setting.py
├── routers/
│   ├── health.py
│   └── chat.py              # Day 5：调 graph
├── schemas/
├── services/
│   ├── llm.py               # Day 2
│   └── rag.py               # Day 3
├── graph/                   # LangGraph 核心
│   ├── state.py
│   ├── nodes.py
│   └── build.py             # 编译 StateGraph
├── practice/                # Day 1～4 练习脚本
│   └── practice_l0.py
├── data/
│   ├── policies/            # 已从手写仓拷贝制度
│   └── mock/                # 订单 mock（Day 4）
├── static/
├── evals/
└── docs/
    └── VS_HAND.md           # 手写 vs LangGraph 对照
```

---

## 当前进度

| 项 | 状态 |
|----|------|
| 目录脚手架 | ✅ 已建 |
| Day 1 | ✅ L0 + health 过关 |
| Day 2 | ✅ L1 单节点调模型过关 |
| Day 3 | ✅ L2 retrieve + 两节点图跑通 |
| Day 4 | ✅ L3 条件边 + mock 查单 |
| Day 5 | ✅ graph + POST /api/chat |
| Day 6 | ✅ Redis 多轮 session |
| Day 7 | ✅ Vue3 聊天页（助手生成，你跑通即可） |
| Day 8 | ✅ 对照 + 自测 + golden |
| Day 9 | ✅ L4 tool loop（practice） |
| 复习 | ✅ Day2–9 `*_review` 全通（8/27） |
| Day 10 | ✅ tool loop 并入主 graph + golden 3/3 |
| Day 11 | ✅ SSE stream_chat + /chat/stream + 前端流式/表格 |
| Day 12 | ✅ 最小 RBAC：X-Role + 入口早回 + tools 硬拦 |
| Day 13 | ✅ JWT login + Bearer 接 chat；企业风前端 + 历史会话 |
| Day 14 | ✅ 共用 edu_crm_agent 库 + 取消确认态 |
| Day 15 | ✅ 并入 14 |
| Day 16 | ✅ RBAC 纵深 |
| Day 17 | ✅ golden + RBAC 禁词 |
| Day 18 | ✅ 检索质量 / 退班试算 / 前端多表 |
| Day 19 | ✅ 可观测（ms、path、used_tools、hit_chunks、粗 token） |
| Day 20 | ✅ MemorySaver checkpointer |
| P2 | ✅ interrupt 取消 + 流式统一走图 |
| **之后** | **面试背诵** → `D:\workspace\learningAi\面试题汇总.md`（唯一文件） |

---

## 复习路线（觉得过得生疏就从这开始）

> 详细分步提示：**[`docs/PRACTICE_REVIEW.md`](docs/PRACTICE_REVIEW.md)**  
> 空白练习文件（**别看**已写好的 `practice_l1.py` 答案，先自己写）：

| 顺序 | 文件 | 过关口令 |
|------|------|----------|
| 1 | `practice/practice_l1_review.py` | 「Day2 复习过了」 |
| 2 | `practice/practice_l2_review.py` | 「Day3 复习过了」 |
| 3 | `practice/practice_l3_review.py` | 「Day4 复习过了」 |
| 4 | `practice/practice_l4_review.py` | 「Day9 复习过了」 |

**规则：** 卡住只报「Day X 复习 · 第 N 步 · 报错」；过关后再开下一文件。

---

## Day 10 · tool loop 并入主 graph（约 4～5h）· **今天**

> **为什么做这步：** practice 里已会「模型选工具」；`POST /api/chat` 仍是 Day4 **正则 ENR 分流**。并入后演示/面试口径一致：图上是 agent ↔ tools，不是规则查单。  
> **对照：** `practice/practice_l4_tool_loop.py`（逻辑搬迁，别整文件粘贴）；手写 `run_tool_loop`。  
> **规则：** 你写；卡住报「Day10 · 第 N 步 · 文件 · 报错」。

### 目标图

```
START → retrieve → agent ──有 tool_calls──→ tools → agent
                         └──无 tool_calls──→ END
```

- **retrieve**：照旧写 `context`（制度）
- **agent**：`chat_message(..., tools=...)`；system/user 里带上 `context`；往 `messages` 追加 assistant
- **tools**：执行 `lookup_order`，追加 `role: tool`
- **reply**：图结束时用最后一条 assistant 的 `content` 填 `reply`（可在 agent 无 tool_calls 时顺手写，或单独 finalize 节点——先简单）

### ① State（约 0.5h）· **先做这步**

打开 `graph/state.py`：确认至少有 `messages`、`user_message`、`context`、`reply`。  
`messages` 建议 `Annotated[list, add_messages]`（和 L4 一致），避免多轮被整表覆盖。

过关：能 `from graph.state import State`，类型里能看到上述字段。

### ② 节点（约 2h）

改 `graph/nodes.py`：

1. 从 L4 搬 `TOOLS_SCHEMA`、`agent_node`、`tools_node`、`should_continue`（可改名）
2. **agent** 要读 `state["context"]`：有制度就拼进本轮 user/system，再 `chat_message`
3. **删掉或停用** `route` + `lookup_order_node` 的规则分流（本 Day 以 LLM 选工具为准）
4. `retrieve_node` 可保留；入口改为固定 `START → retrieve → agent`

### ③ 接线（约 0.5h）

改 `graph/build.py`：按上方目标图 `compile`。  
过关：脚本或临时 invoke —— ENR 问单能出订单信息；退班问题能挂上制度且不瞎调工具。

### ④ API（约 0.5h）

改 `routers/chat.py`：

- `invoke` 时：`messages` = 历史 + 本轮 `{"role":"user","content": question}`
- 仍用 `result["reply"]` 回写 Redis
- 跑 `evals/run_golden.py`（先看 PASS/FAIL，FAIL 记下原因）

### ⑤ 口述 30 秒（约 0.5h）

更新一句：Day4 规则分流 → 现已并入 LLM tool loop。可写在 `docs/day8_自测.md` 末尾一行。

**Day10 收工口令：** 「Day10 过了」+ 贴一次 ENR / 一次退班的 API 或 invoke 结果摘要

---

## Day 11 · SSE 流式（约 3～4h）· **今天接着做**

> **对齐手写仓：** `edu-crm-agent` 的 `/chat/stream` **不跑 tool loop**，只 retrieve + `stream_chat` 吐 token。  
> 本仓 Day11 同样：**流式管制度问答手感**；ENR 查单仍走非流式 `POST /api/chat`（或流式里检测到 ENR 就提示用普通聊天）。  
> 卡住报：「Day11 · 第 N 步 · 文件 · 报错」。

### ① `services/llm.py` · `stream_chat`（约 0.5h）· **先做**

对照手写 `stream_chat`：

```python
def stream_chat(messages, model=None, temperature=0):
    # create(..., stream=True)
    # for chunk in stream:
    #     delta = chunk.choices[0].delta.content
    #     if delta: yield delta
```

小测：

```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -c "from services.llm import stream_chat; print(''.join(stream_chat([{'role':'user','content':'用五个字打个招呼'}])))"
```

### ② `routers/chat.py` · `POST /api/chat/stream`（约 1.5h）

1. `StreamingResponse` + `media_type="text/event-stream"`
2. 校验 question；`load_messages`；`retrieve` 拼 context
3. 组 messages（system/制度 + history + 本轮 user）
4. `for piece in stream_chat(...): yield f"data: {piece}\n\n"`
5. 最后 `yield "data: [DONE]\n\n"`；拼完整 answer 后 `save_messages`
6. **诚实：** 此路径暂不调 graph / 不查 ENR（和手写一致）；查单用现有 `/api/chat`

过关：Swagger 或 curl 能看到一段段吐字，最后 `[DONE]`。

### ③ 前端接流式（约 1h）

对照手写 `frontend/src/api/client.js` 的 `streamChat`：`fetch` + `ReadableStream` 读 `data:` 行，`onToken` 追加气泡。  
`ChatPanel` 发送时走 stream（或加开关）；loading 时气泡逐字变长。

### ④ 口述 30 秒

流式和非流式差在哪？为啥 tool loop 难直接 SSE？

**Day11 收工口令：** 「Day11 过了」+ 描述你看到的逐字效果

---

## Day 12 · 最小 RBAC（约 3h）· **接着做**

> **目标：** 面试能说清「权限不能只靠 prompt」——**入口早回 + 工具硬拦**。  
> **对照：** 手写仓 `utils/rbac.py`（只读）；本仓先做 **Header 演示角色**，JWT 完整登录放到下一步。  
> 卡住报：「Day12 · 第 N 步 · 文件 · 报错」。

### 演示角色（先这 3 个够）

| Header `X-Role` | 能做什么 |
|-----------------|----------|
| 无 / `guest` | 只制度问答，**不能查单** |
| `lecturer` | 制度，不能查单 |
| `tutor` / `admin` | 制度 + 查单（`order:read`） |

### ① `utils/rbac.py`（约 1h）· **先做**

自己写（可对照手写仓精简，别整文件粘）：

- 权限码：`policy:ask`、`order:read`
- `ROLE_PERMS`：guest/lecturer 只有 ask；tutor/admin 有 ask+read
- `has_perm(user, perm) -> bool`
- `assert_perm(user, perm) -> str | None`（无权返回中文说明，有权返回 `None`）
- `user` 形态：`{"role": "guest"}` 或 `None`（当 guest）

过关：

```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -c "from utils.rbac import has_perm, assert_perm; u={'role':'guest'}; print(has_perm(u,'order:read'), assert_perm(u,'order:read')[:40])"
```

应打印 `False` 和一段「没有…权限」文案。

### ② 读角色（约 0.5h）

在 `routers/chat.py`（或新建 `utils/auth_demo.py`）：从请求头读 `X-Role`，拼成 `user = {"role": ...}`；没有则 guest。

### ③ 入口早回（约 0.5h）

`POST /api/chat`：若问题像查单（含 `ENR` 或「订单」）且 `not has_perm(user, order:read)` → **直接** `ChatResponse(answer=assert_perm(...))`，**不要** `graph.invoke`。

### ④ 工具硬拦（约 0.5h）

`tools_node`：执行 `lookup_order` 前再查一次权限（State 或闭包传入 user）。无权则 tool 结果写无权 JSON，不查 mock。  
（面试重点：模型就算发了 tool_calls 也执行不了。）

### ⑤ 自测

- `X-Role: guest` + ENR 问单 → 无权文案，不调模型更好  
- `X-Role: tutor` + ENR → 能查到订单  
- 退班制度（guest）→ 仍可答  

curl 示例（PowerShell）：

```powershell
$h = @{ "Content-Type"="application/json"; "X-Role"="guest" }
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/chat" -Method POST -Headers $h -Body '{"question":"ENR20250801001 什么状态？","session_id":"rbac1"}'
```

**Day12 收工口令：** 「Day12 过了」+ guest/tutor 各测一次结果摘要

---

## Day 13 · 演示 JWT（约 2～3h）· **接着做**

> Day12 用 `X-Role` 演示权限；Day13 换成 **登录发 JWT，请求带 Bearer**，更接近手写仓。  
> 对照：`edu-crm-agent` 的 `utils/jwt_util.py`、`routers/auth.py`、`utils/auth.py`（只读精简）。  
> 卡住报：「Day13 · 第 N 步 · 报错」。

### ① `utils/jwt_util.py`（约 0.5h）· **先做**

- `create_access_token(user_id, role, username) -> str`（用 `PyJWT` / `jose`，密钥可先写 settings 或常量）
- `verify_token(token) -> dict | None`（解出 id/role/username；失败返回 None）

小测：encode 再 decode，role 对得上。

### ② `POST /api/auth/login`（约 0.5h）

- 用 `DEMO_USERS`（可从 rbac 里加几个账号密码，或对照手写）
- 校验密码 → `create_access_token` → 返回 `{access_token, user}`

### ③ `get_optional_user`（约 0.5h）

- 读 `Authorization: Bearer ...`
- 有则 `verify_token`，无/坏则 `None`（当 guest）
- `chat` 里：优先用 JWT 用户；没有再回退 `X-Role`（兼容 Day12）

### ④ 自测

```powershell
# 登录
$login = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/auth/login" -Method POST -ContentType "application/json" -Body '{"username":"tutor","password":"tutor123"}'
$token = $login.access_token
# 带 Token 查单
$h = @{ "Content-Type"="application/json"; "Authorization"="Bearer $token" }
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/chat" -Method POST -Headers $h -Body '{"question":"ENR20250801001 什么状态？","session_id":"jwt1"}').answer
```

无 Token 查 ENR → 仍无权。

**Day13 收工口令：** 「Day13 过了」

---

## 企业向补齐线 · P0 → P1（部署不做）

> 目标：作品从「会 LangGraph」→「业务写操作 + 实库 + 评测 + 可观测」可讲。  
> **每天只推进当前 Day**；对照手写仓只读。

| 阶段 | Day | 交付 |
|------|-----|------|
| P0 | 14 | mock 上 **取消订单 + 确认态**（确定性路径，不靠模型嘴炮） |
| P0 | 15 | **MySQL** 替换 mock 查单/取消 |
| P0 | 16 | RBAC：`order:cancel` + 越权意图早回 |
| P1 | 17 | golden 扩写 + 禁词（不得「已为您取消」） |
| P1 | 18 | 检索：切段/top_k + 几条固定问回归 |
| P1 | 19 | 日志：ms、是否用 tool、粗 token |

---

## Day 14 · P0①+② 取消确认态 + **共用 edu_crm_agent MySQL**（约 5h）· **当前**

> 按你的选择：**直接连手写仓同一库** `edu_crm_agent`，不再先写 mock 取消。  
> 对照：`edu-crm-agent` 的 `config/db_conf.py`、`models/enrollment.py`、`crud/enrollments.py`。  
> **不要** `import` 手写仓包（两仓 PYTHONPATH 别混）；本仓自建精简 db/model/crud。

### ① 配置与依赖（约 0.5h）

1. `pip install sqlalchemy aiomysql pymysql`（写入 requirements）
2. `utils/setting.py` 增加 `DATABASE_URL`，`.env` 写成与手写仓**相同**：
   ```
   DATABASE_URL=mysql+aiomysql://root:123456@127.0.0.1:3306/edu_crm_agent?charset=utf8mb4
   ```
   （账号密码以你本机手写仓 `.env` 为准）
3. 确认 MySQL 里已有库和报名数据（用手写仓起过 / seed 过）

### ② 本仓最小 ORM（约 1h）

新建（对照拷贝精简，表名/字段与手写一致）：

- `models/base.py`：`DeclarativeBase`
- `models/enrollment.py`：`Enrollment`（至少 `order_no`, `status`, `consumed_lessons`, `student_id` 等手写已有列）
- `config/db_conf.py`：`async_engine` + `AsyncSessionLocal` + `get_database`（可先只要 `session_scope` 异步上下文）

图节点目前是**同步**的，工具层建议提供：

```python
def run_async(coro):
    import asyncio
    return asyncio.run(coro)
```

在 `lookup_order` / `cancel_order` 里 `run_async(_xxx(...))`，内部用 `AsyncSessionLocal`。

### ③ 改 `services/tools.py`（约 1.5h）

- `lookup_order`：查库 `Enrollment`，拼 `{"ok", "order_no", "status", "consumed_lessons", "student_name"?}`  
  （student_name 若在别的表，可先返回 `student_id`）
- `cancel_order`：把该行 `status="cancelled"`，`commit`，返回结果  
- **mock JSON 可保留作 fallback**，但默认走 DB

小测（项目根）：

```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -c "from services.tools import lookup_order; print(lookup_order('ENR20250801001'))"
```

### ④ pending + chat 确定性路径（约 1.5h）

同原 Day14：`set/peek/clear_pending_cancel` + chat 里取消意图 / 「确认」硬拦。  
权限：`order:cancel`（admin 有，tutor 无）。

### ⑤ 自测

admin 登录 →「取消 ENR…」→「确认」→ 用手写仓或 SQL 看 status 已是 cancelled。

**Day14 收工口令：** 「Day14 过了」

> 原计划 Day15「接 MySQL」并入本日；Day15 可改为：多字段查单展示 / 学员名 join，或直接进 Day16 RBAC 纵深。

---

## Day 9 · LLM 工具循环（约 5h）

> **和 Day4 差别：** Day4 用**规则**（正则 ENR）分流；Day9 让**模型**决定是否调 `lookup_order`，更接近手写 `run_tool_loop`。  
> **先在 `practice/` 练**，过关后再考虑并入 `graph/build.py`。

### ① 扩展 `services/llm.py`（约 1h）

对照手写仓 `chat_message`：

```python
def chat_message(messages, tools=None, model=None, temperature=0):
    # completions.create(..., tools=tools)
    # return response.choices[0].message   # 含 .content / .tool_calls
```

小测：能 print 出 message 对象。

### ② 写 `practice/practice_l4_tool_loop.py`（约 3h）

打开文件内 TODO。核心图：

```
START → agent ──tool_calls?──→ tools → agent
              └── END
```

- **agent_node**：`chat_message(..., tools=...)`, 把 assistant message 追加进 `messages`
- **tools_node**：解析 `tool_calls`，调 `lookup_order`，追加 `role: tool` 消息
- **should_continue**：有 tool_calls → `"tools"`，否则 `END`

过关：ENR 问题最终 reply 含订单信息；普通问题不瞎调工具也能答。

### ③ 口述（约 0.5h）

Day4 规则分流 vs Day9 模型选工具，各适合什么场景？

**Day9 收工口令：** 「Day9 过了」或「Day9 卡在 practice_l4 第 x 行」

---

## 今天第一件事 · Day 1

### ① 环境（约 1h）

```powershell
cd D:\workspace\edu-crm-langgraph
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# 编辑 .env：填入 DEEPSEEK_API_KEY（可先空，L0 不用）
```

过关：`python -c "import langgraph; print('ok')"`

### ② 配置可读（约 0.5h）

确认 `utils/setting.py` 能：

```powershell
.\.venv\Scripts\python.exe -c "from utils.setting import settings; print(settings.DEEPSEEK_MODEL)"
```

### ③ health（约 0.5h）

```powershell
.\.venv\Scripts\uvicorn.exe main:app --reload --port 8001
```

浏览器：`http://127.0.0.1:8001/health` → 200。  
（端口 **8001**，避免和手写仓 8000 冲突。）

### ④ L0 最小图（约 2～3h · 你写）

打开 `practice/practice_l0.py`，按文件内 TODO 写完：

- 定义 State（至少 `text: str`）
- 两个 node：`add_hello`、`add_bye`
- `StateGraph` → `add_node` → `set_entry_point` → `add_edge` → `compile`
- `invoke({"text": "同学"})` 打印结果

过关：终端看到类似 `你好，同学……再见`。

**Day 1 收工口令：** 「Day1 过了」或「Day1 卡在 practice_l0 第 x 行：…」

---

## 后续 Day 速览（细节到当天再展开）

| Day | 你写什么 | 过关 |
|-----|----------|------|
| 2 | `services/llm.py` + `practice_l1.py` 单节点调模型 | 一问一答 |
| 3 | `services/rag.py` + retrieve 节点 | 问退班能挂上制度 |
| 4 | mock 订单 + tools 节点 + 条件边 | 问 ENR 能查到状态 |
| 5 | `graph/build.py` + `routers/chat.py` | POST `/api/chat` 走图 |
| 6 | Redis `session_id` | 多轮有记忆 |
| 7 | `static/chat.html` + Compose | 浏览器能聊 |
| 8 | `docs/VS_HAND.md` + 可选 3 条 golden | 能讲清映射 |

---

## Day 8 · 今天你要做的（约 3～4h）

> 助手已写好 `docs/VS_HAND.md` 草稿和 `evals/`，**不算你学过**。  
> Day8 = **对照、弄懂、能讲**，不是抄文件。

### ① 对照阅读（约 1.5h）

1. 打开手写 `D:\workspace\edu-crm-agent\routers\chat.py`（看主流程）
2. 打开本仓 `routers/chat.py` + `graph/build.py` + `graph/nodes.py`
3. 读 `docs/VS_HAND.md`，**每段用自己的话**在 `docs/day8_自测.md` 里答 4 题（见该文件）

### ② 找一条映射（约 0.5h）

在 `docs/day8_自测.md` 第 5 题：自己写一行「手写 X → LangGraph Y」，  
例如：`run_tool_loop` → `route + lookup_order_node + call_llm`（不要照抄表，写你理解的）

### ③ 跑 golden（约 0.5h）

```powershell
# 终端 1
.\.venv\Scripts\uvicorn.exe main:app --host 127.0.0.1 --port 8001
# 终端 2
.\.venv\Scripts\python.exe evals\run_golden.py
```

看输出，**记下**哪条 PASS/FAIL；FAIL 的说说可能原因（不用修也行，Day8 先会看）

### ④ 30 秒口述（约 0.5h）

对着镜子/录音说一遍（写在 `day8_自测.md` 第 6 题）：

「手写是 tool loop，LangGraph 是……，我这个项目图上有哪几个节点……」

**Day8 收工口令：** 「Day8 过了」+ 贴 `day8_自测.md` 里你写的答案（不用完美）

---

## 助手怎么带

1. 你说：**「开始 Day1」** / **「Day1 过了，进 Day2」** / **「卡在 …」**  
2. **复习模式：** **「开始 Day2 复习」** / **「Day3 复习 · 第 4 步 · …」** → 只给该步提示，不整文件代写  
3. 我只给本步提示与批改  
4. **不**在本仓重做手写 tool loop 当主线；手写逻辑去对照 `edu-crm-agent`
