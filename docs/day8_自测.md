# Day 8 自测（你自己写，别抄 VS_HAND）

> 对照 `docs/VS_HAND.md` 和两边代码写。**白话即可**，每题 2～5 句。

## 1. compile 和 invoke 区别？

（你的答案：）
compile设计好执行规则，invoke把执行对话

<!-- 批改：invoke 更准确是「带着 State 跑一遍图」，不是「执行对话」 -->


## 2. route 返回的字符串必须和什么一致？
因为有建图->选择方法->从某个方法开始执行到某个方法结束->完成设计的图纸->执行
因为这样用stateGraph的时候需要在第三部的时候可以找到相对应的方法

<!-- 批改：直接答——route 返回值 = add_node 站名 = path_map 的 key，三处字符串要一致 -->


## 3. 为什么 retrieve 和 call_llm 是两个节点，不是一个？
route返回的字符串需要和add_edge中一一对应

<!-- 批改：这题答的是第2题。第3题应答：retrieve 只检索写 context；call_llm 只调模型；分工 + retrieve→call_llm 固定顺序 -->


## 4. 多轮记忆存在哪？什么时候 load、什么时候 save？
多轮记忆存储在redis中，启动redis后，通过获取当前对话中的session_id加载到历史对话
然后再用户执行对话后同时把历史对话和新的对话同时拼接后，获得新的对话，这个时候保存新的

<!-- 批改：✅ load 在 graph invoke 前（routers/chat.py）；save 在 invoke 后；Redis 无则内存兜底 -->


## 5. 手写 → LangGraph：映射是什么意思？

**映射** = 手写仓里的**一块逻辑/函数**，在本仓**对应哪一块**（不是文件名）。

`run_tool_loop` **不是文件**，是手写仓函数：
- 路径：`D:\workspace\edu-crm-agent\services\crm_tools.py`（约 422 行）
- 在 `routers/chat.py` 里：`from services.crm_tools import run_tool_loop`

（你的答案：）
```
run_tool_loop（crm_tools.py 里的 while+tools 循环）
  → graph/build.py：route 条件边 + lookup_order 节点 + retrieve → call_llm
```


## 6. 30 秒项目介绍（口述稿）

> 下面带注释，面试时只说**正文**，注释帮助你看懂在说什么。

### 手写版（edu-crm-agent）

<!-- 项目是什么 -->
教培 CRM **教务助手**：顾问问制度（退班/换班）、查订单、查学员。

<!-- 技术栈 -->
FastAPI + DeepSeek + Chroma RAG + MySQL + Redis 多轮。

<!-- 核心编排：run_tool_loop 是函数名，在 crm_tools.py -->
用户 POST `/api/chat` → 先 **retrieve** 制度 → 再进 **`run_tool_loop`**：
while 循环调模型，模型可返回 **tool_calls**（查库工具）→ 执行工具 → 结果塞回 messages → 直到出最终文字。

<!-- 其它 -->
有 JWT/RBAC；前端 Vue3。

### LangGraph 版（edu-crm-langgraph）

<!-- 同一业务，换编排 -->
**同一业务**，用 **LangGraph StateGraph** 代替 while loop。

<!-- API 层 -->
`POST /api/chat`：**load_messages**（Redis）→ **graph_app.invoke** → **save_messages** → 返 answer。

<!-- 图上怎么走 -->
**START → route**：
- 问题里含 **ENR** → **lookup_order**（mock JSON 查单，不调模型）
- 否则 → **retrieve**（RAG 写 context）→ **call_llm**（带 context + history）

<!-- State -->
State：`user_message`、`context`、`messages`、`reply`。

<!-- 边界 -->
本阶段无 RBAC；查单用**规则分叉**（Day4），不是 LLM 自选工具。

### 图上的节点

| 站名 | 干什么 |
|------|--------|
| `route` | 分流函数（不是 node） |
| `retrieve` | RAG |
| `call_llm` | 调 DeepSeek |
| `lookup_order` | mock 查单 |

### 30 秒合一版（面试照着说）

我做了一个教培教务助手，**两个版本**：手写版用 **OpenAI tool loop**（`run_tool_loop`），模型自己决定何时调工具查库；LangGraph 版把 **检索、查单、生成** 拆成 **图节点**，用 **条件边** 处理 ENR 查单，**State** 在节点间传递，API 负责 **Redis 多轮**。业务都是 **制度 RAG + 查订单**，LangGraph 版流程更直观，方便扩展和演示。


## 7. golden 跑完记录（跑 evals/run_golden.py 后填）

**先起后端**，再跑：`.\.venv\Scripts\python.exe evals\run_golden.py`

| 用例 id | 测什么 | PASS/FAIL | 一句话原因 |
|---------|--------|-----------|------------|
| lg01 | 制度退班扣费 | PASS（修后） | 曾因旧进程/State 字段 typo `message`→500 |
| lg02 | ENR 查单 | PASS（Day10 后再跑仍 PASS） | 现为 agent↔tools，不再是 route→lookup_order |
| lg03 | 多轮「我叫什么」 | PASS（修后） | call_llm 要「结合历史」；改代码后**必须重启 uvicorn** |

<!-- FAIL 常见原因：
  - ConnectError → 后端没起
  - HTTP 500 → 重启 uvicorn；查 graph/state.py 是否 messages（不是 message）
  - lg03 不命中 → call_llm 只认制度不认 history（已改 nodes.py）
  - Graph 思考 200s+ / 查单报错 → 见 docs/ISSUES.md
-->

---

## Day10 口述（并入 tool loop 后改一句）

**旧（Day4）：** 条件边正则 ENR → `lookup_order` 节点。  
**现（Day10）：** `retrieve → agent ↔ tools`，模型决定是否调 `lookup_order`。

用自己的话在下面写一行（面试用）：

> 
