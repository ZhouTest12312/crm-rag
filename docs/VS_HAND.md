# 手写 vs LangGraph 对照

> **Day8 用法：** 先自己做 `docs/day8_自测.md`，再回来对照本文。  
> 本文是参考草稿，**不等于你已经学完**。

---

## 一句话

| 手写 | LangGraph |
|------|-----------|
| Python `while` + `if` 控制 tool loop | **StateGraph**：节点 + 边 + 条件边 |
| 流程藏在代码顺序里 | 流程画在图上，节点只改 State |

---

## 架构对照

| 层 | 手写 `edu-crm-agent` | 本仓 LangGraph |
|----|----------------------|----------------|
| Web | FastAPI `routers/chat.py` | 同 · `routers/chat.py` → `graph_app.invoke` |
| 编排 | `services/crm_tools.run_tool_loop` | `graph/build.py` 编译的 StateGraph |
| 模型 | `services/llm.chat` / `chat_message` | 同 · `call_llm` 节点内调 `chat` |
| RAG | `services/rag.retrieve` + 拼 system | `retrieve_node` → `context` 进 State |
| 查单 | Tool `lookup_enrollment` + LLM 决定是否调 | `route` 条件边 → `lookup_order_node`（规则分流，Day4） |
| 会话 | `services/chat_session` + Redis | 同 · router 里 load/save，State 带 `messages` |
| 前端 | Vue3 `frontend/` | 同结构 · `frontend/` |
| 权限 | JWT/RBAC + 工具裁剪 | **Day9+**，本阶段 mock 查单无 RBAC |

---

## 流程对照（用户问一句话时）

### 手写：tool loop

```
chat 路由
  → retrieve → 拼 system/messages
  → while:
       LLM（带 tools）
       有 tool_calls → execute_tool → 再喂回 messages
       无 tool_calls → 返回答案
  → save Redis
```

### LangGraph：图

```
POST /api/chat
  → load_messages(session_id)
  → graph_app.invoke({ user_message, messages })
       START
         → route（有 ENR？）
              ├─ lookup_order → END
              └─ retrieve → call_llm → END
  → save_messages
  → return answer
```

**差别：** 手写让 **模型决定** 何时调工具；本仓 Day4 用 **规则**（正则 ENR）走查单分支——更简单，面试要说清这是演示取舍，生产可换 `ToolNode` + LLM 选工具。

---

## 文件映射

| 手写 | 本仓 | 说明 |
|------|------|------|
| `run_tool_loop` | `graph/nodes.py` + `graph/build.py` | 循环 → 有向图 |
| `retrieve` + 拼 prompt | `retrieve_node` + `call_llm` | 制度先进 State.context |
| `lookup_enrollment` tool | `services/tools.lookup_order` | mock JSON，无 MySQL |
| `chat.py` 大段逻辑 | `chat.py` 薄封装 + `nodes` | API 只 invoke |
| — | `practice/practice_l0~l3.py` | 分级练习（手写无） |

---

## State 里有什么

| 字段 | 谁写 | 用途 |
|------|------|------|
| `user_message` | API 传入 | 本轮问题 |
| `messages` | router load | 多轮历史 |
| `context` | `retrieve_node` | RAG 制度片段 |
| `reply` | `call_llm` / `lookup_order_node` | 最终答案 |

手写等价物：分散在 `messages` 列表和 `system` 字符串里，没有显式 TypedDict。

---

## 关键 API 对照

| 概念 | LangGraph | 你练过的 |
|------|-----------|----------|
| 登记步骤 | `add_node(name, fn)` | L0 hello/bye |
| 固定顺序 | `add_edge(A, B)` | L0、L2 |
| 分叉 | `add_conditional_edges(START, route, map)` | L3 ENR |
| 可执行 | `compile()` | 出厂 |
| 运行 | `invoke(state)` | 发车 |

---

## 本仓尚未移植 / 仍弱（诚实边界 · 8/28 更新）

**已补相对 VS_HAND 旧稿：** JWT 演示登录、最小 RBAC（查单）、SSE（制度）、agent↔tools、前端历史。

**仍缺或很浅（部署除外）：**
- 写操作：取消订单确认态 / 意图早拦全套（手写仓有）
- MySQL 实库（现 mock JSON）
- 多工具 + 权限细码（仅 lookup_order）
- checkpointer / 断点续跑
- 完整 golden（手写 12+；本仓约 3 条，缺 RBAC 禁词用例）
- 可观测：tracing、token 计量、审计日志
- 检索质量：切段策略、混合检索、评测集
- 水平权限（按班级/数据范围），现只有角色垂直权限
- 流式路径与 tool loop 统一（现分流）

---

## 面试怎么讲（30 秒版）

「手写版是 OpenAI tool loop，模型自己决定调什么工具；LangGraph 版把 retrieve、查单、生成拆成节点，用条件边做 ENR 分流，State 在节点间传递。业务一样，编排从隐式 while 变成显式图，方便加步骤、做可视化，后面还可以上 checkpointer 做断点续跑。」

---

## 自测：你能回答吗？

1. `compile` 和 `invoke` 区别？  
2. `route` 返回的字符串必须和什么一致？  
3. 为什么 retrieve 和 call_llm 是两个节点而不是一个？  
4. 多轮记忆存在哪、什么时候 load/save？

（答案见 BUILD Day1～6 与本文「流程对照」）
