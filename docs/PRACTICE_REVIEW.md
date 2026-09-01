# 从 Day2 开始 · 复习带提示

> 觉得 Day9「过得生疏」很正常——图、条件边、messages 格式叠在一起，一次很难吃透。  
> **用法：** 按 Day 顺序，打开 `practice/practice_l*_review.py`，**自己从零写**；卡住只看对应「提示阶梯」，不要先翻旧文件答案。

---

## 怎么练（重要）

1. **只开复习文件**（`*_review.py`），先别看 `practice_l1.py` 等已写好的版本。
2. 每步写 1～3 行就 **保存 → 运行**，别一口气写完。
3. 卡住报：**「Day X 复习 · 第 N 步 · 报错/现象」**。
4. 某 Day 复习过关后再进下一 Day；Day4 过关再练 Day9 tool loop。

**跑法（项目根）：**

```powershell
cd D:\workspace\edu-crm-langgraph
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe practice\practice_l1_review.py
```

---

## 复习顺序总览

| 顺序 | 文件 | 练什么 | 过关标准 |
|------|------|--------|----------|
| 1 | `practice_l1_review.py` | State + 单节点 + 调 LLM | print 出模型对「1+1」的回答 |
| 2 | `practice_l2_review.py` | 两节点串联 + RAG context | 退班问题 reply 提到扣费/服务费 |
| 3 | `practice_l3_review.py` | 条件边 + mock 查单 | ENR 走查单；普通问题走 LLM |
| 4 | `practice_l4_review.py` | LLM 决定调工具 + 回环 | ENR 两轮 agent；普通问题不调工具 |

**口诀（每天念一遍）：**

- **node = 登记站**（函数写在这）
- **edge = 画路线**（谁连谁）
- **compile = 出厂**（图定型）
- **invoke = 发车**（传入 State 初始值）

---

## Day2 复习 · L1 单节点调模型

**文件：** `practice/practice_l1_review.py`

| 步 | 你要写什么 | 提示 |
|----|-----------|------|
| 1 | `State` 两个字段 | `user_message: str`, `reply: str` |
| 2 | `from services.llm import chat` | 先确认 `.env` 有 `DEEPSEEK_API_KEY` |
| 3 | `call_llm(state)` | `messages = [{"role":"user","content": state["user_message"]}]` → `chat(messages)` → `return {"reply": answer}` |
| 4 | 建图 | `START → call_llm → END`（三条：`add_node` + 两条 `add_edge`） |
| 5 | invoke | `{"user_message": "1+1等于几？"}`，print 整个结果或 `["reply"]` |

**和 L0 的唯一差别：** 节点里调 `chat()`，不是拼字符串。

**常错：**

- `return answer` 忘了包成 `{"reply": ...}`
- `add_edge` 写反方向
- 没激活 venv / 没 API Key → `SystemExit`

**对照（只读）：** `edu-crm-agent/services/llm.py` 的 `chat`

---

## Day3 复习 · L2 retrieve + call_llm

**文件：** `practice/practice_l2_review.py`

| 步 | 你要写什么 | 提示 |
|----|-----------|------|
| 1 | `State` 三个字段 | `user_message`, `context`, `reply` |
| 2 | `retrieve_node` | `hits = retrieve(state["user_message"])` → `"\n\n".join(h["text"] for h in hits)` → `return {"context": ...}` |
| 3 | `call_llm` | user 一条消息里拼：`仅依据以下制度…` + `state["context"]` + `用户问题：…` |
| 4 | 建图 | **固定顺序：** `START → retrieve → call_llm → END`（中间不能断） |
| 5 | 测 | 问「开课后退班怎么扣费？」；可先 `print(state["context"])` 自检有没有检索到字 |

**常错：**

- 忘了 `retrieve → call_llm` 这条边（只有 START→retrieve 会没 reply）
- context 空 → 检查 `data/policies/` 是否在、`services/rag.py` 能否 import

**对照：** `services/rag.py` 的 `retrieve`

---

## Day4 复习 · L3 条件边 + 查单

**文件：** `practice/practice_l3_review.py`

| 步 | 你要写什么 | 提示 |
|----|-----------|------|
| 1 | `route(state) -> str` | `extract_order_no(...)` 有值 → 返回 `"lookup_order"`，否则 `"call_llm"` |
| 2 | `lookup_order_node` | 调 `lookup_order(order_no)`，拼人话 `reply`（含 status、student_name） |
| 3 | `call_llm` | 普通 `chat([{"role":"user",...}])` |
| 4 | **条件边** | `add_conditional_edges(START, route, {"lookup_order":"lookup_order", "call_llm":"call_llm"})` |
| 5 | 收尾 | 两个节点各 `add_edge(..., END)` |

**条件边三件套（背）：**

1. **从哪分叉：** 常是 `START` 或某个 node 名  
2. **判断函数：** return 的字符串  
3. **path_map：** key 必须和 return 完全一致  

**常错：**

- path_map 的 key 和 `route` return 拼写不一致 → 运行时报找不到节点
- 正则写错：`ENR\d+` 不是 `ENR\\d+`（Python 字符串里一个反斜杠就够）
- 只有条件边、忘记 `lookup_order → END`

**和 Day9 对比（先记 Day4）：** Day4 **规则**（正则）分流；Day9 **模型**决定是否调工具。

---

## Day9 复习 · L4 tool loop（Day4 过关后再做）

**文件：** `practice/practice_l4_review.py`

| 步 | 你要写什么 | 提示 |
|----|-----------|------|
| 1 | `State` | `messages: Annotated[list, add_messages]` |
| 2 | `TOOLS_SCHEMA` | 照抄 function 名 `lookup_order`、参数 `order_no` |
| 3 | `chat_message` | 已在 `llm.py`；内部会 `convert_to_openai_messages` |
| 4 | `agent_node` | `chat_message(..., tools=TOOLS_SCHEMA)` → 转 assistant dict → `return {"messages": [assistant]}`；**有 tool_calls 才加该字段** |
| 5 | `tools_node` | 读最后一条的 tool_calls → `lookup_order` → `role:tool` + `json.dumps` + `tool_call_id` |
| 6 | `should_continue` | 有 tool_calls → `"tools"`，否则 `END` |
| 7 | 接线 | `START→agent` + **条件边** + `tools→agent`（**不要** tools→END） |

**图（必画在纸上）：**

```
START → agent_node
           ├─ tool_calls? → tools_node → agent_node → END
           └─ 无 tool_calls → END
```

**常错（你刚踩过的）：**

- `agent_node` 没有出边 → 必须 `add_conditional_edges`
- `tools_node` 同时连 agent 和 END → 只能 `tools → agent`
- `add_messages` 后 message 变 `HumanMessage` → 已在 `llm.py` 处理，practice 不用管
- `should_continue` 用 `last.get(...)` → AIMessage 没有 `.get`，用 `getattr(last, "tool_calls", None)`
- invoke 传 `{"messages": [{"role":"user", "content":"..."}]}`（list，不是 dict）

---

## 自测清单（全部复习完勾一遍）

- [ ] 能不看代码画出 Day2 的图（几个节点、几条边）
- [ ] 能说出 Day3 为什么必须 `retrieve → call_llm`
- [ ] 能写出 Day4 `add_conditional_edges` 三件套
- [ ] 能对比 Day4 规则分流 vs Day9 模型选工具
- [ ] 能口述 tool loop 完整路径（user → agent → tools → agent → END）
- [ ] 知道 `compile` 和 `invoke` 分别干什么

---

## 收工口令

| 完成 | 你说 |
|------|------|
| Day2 复习 | 「Day2 复习过了」 |
| Day3 复习 | 「Day3 复习过了」 |
| Day4 复习 | 「Day4 复习过了」 |
| Day9 复习 | 「Day9 复习过了」 |
| 卡住 | 「Day X 复习 · 第 N 步 · …」 |

---

## 答案在哪

过关后再对照：

- `practice/practice_l1.py` … `practice_l4_tool_loop.py`（当前实现）
- 主项目：`graph/build.py`、`graph/nodes.py`（Day5 并入版）

**复习阶段不要先打开答案文件。**
