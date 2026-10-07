# Hello-Agents 学习笔记与实现

跟着开源教程 **Hello-Agents** 学习 LLM Agent，把每一章的原理**从零手写**跑通
（**不依赖 Agent 框架**），再回过来对照框架实现做差异复盘。

所有代码均可离线自测 —— 用假 LLM 按剧本回话，**不消耗 API 额度**。

求职方向：全栈开发 / AI Agent。

---

## 目录一览

| 目录 | 内容 | 关键点 |
|---|---|---|
| `4-0agent实现/` | **手写三种 Agent 范式**：ReAct、Plan-and-Solve、Reflection | 本仓库核心 |
| `7-0agent实现/` | 第 7 章实现，含**假 LLM 服务器**做免费用测试 | 测试工程 |
| `6-0框架实现/` | AutoGen、LangGraph 框架对照实现 | 手写 vs 框架 |
| `My-Fast-api/fastapibuildagent/` | FastAPI + **embedding 向量检索** + 对话记忆 + 简易前端 | RAG |
| `after_async_rebuild_agent/` | 异步 Agent + **SSE 流式输出** | 服务化 |
| `Rebuild_Transformer/` | 从零复现 Transformer，附 N-gram→RNN→LSTM→Transformer 演化笔记 | 原理 |
| `Async/` | asyncio 练习，含死锁复现 | 基础 |
| `agent_try_case01/` | 第三章写法：关键词触发（`if "[TIME]" in reply`） | 对照组 |

---

## 三种 Agent 范式（核心）

三种范式的差别在于**"思考"与"行动"在时间上如何排列**：

| 范式 | 结构 | 适合 | 代价 |
|---|---|---|---|
| **ReAct** | Thought → Action → Observation **交替循环** | 需要外部信息、路径不确定的任务 | 每步都调一次模型，轮次多、贵 |
| **Plan-and-Solve** | 先一次性出完整计划，再逐步执行 | 步骤可预判的确定性任务 | 计划错了整条链都错，中途不能改向 |
| **Reflection** | 执行 → 自我评审 → 按反馈优化，**循环** | 有明确质量标准的产出（如代码优化） | 不引入外部信息，只是反复打磨已有答案 |

### 实现要点

**ReAct（`4-0agent实现/ReAct_agent.py`）**

- 自定义文本协议：`Thought: ...` / `Action: 工具名[输入]` 或 `Finish[答案]`，用正则解析器拆解
- **两套安全阀**：`max_steps` 兜死循环；`errortime` 兜连续工具调用失败，且**成功时清零**
- `_parse_action` 只把"切不出工具名"判为格式错误 —— **空输入是合法的**，不能拿 `tool_input` 判空
- 格式错误也要写回 `history`，否则模型不知道自己错了，会反复犯同一个错直到步数耗尽

**Plan-and-Solve（`PlanAndSolveAgent.py`）**

- Planner 输出 Python 列表格式的计划，用 **`ast.literal_eval`** 解析（不用 `eval`，避免执行任意代码）
- Executor 逐步执行，把「已完成的步骤与结果」累积进下一次 prompt

**Reflection（`Reflection.py`）**

- 独立的 `Memory` 模块，按 `execution` / `reflection` 两类记录轨迹
- 终止条件：评审员输出「无需改进」即提前结束，不必跑满 `max_iterations`

### 三者的协作设想

`4-0agent实现/note.md` 里画了一条调度思路：简单任务走 Plan-and-Solve，复杂探索任务走
ReAct 主循环，ReAct 内部需要拆解时调 Planner、失败时调 Reflector，经验写回 Memory 供下次规划使用。

---

## 怎么跑

依赖：Python 3.10+，`pip install -r requirements.txt`（或按各目录内的依赖单独装）。

**推荐先跑离线自测**（不需要 API key、不花钱）：

```bash
python "4-0agent实现/check_react.py"
python "7-0agent实现/check_ch7_core.py"
```

**再接真模型**：把 `.env.example` 复制成 `.env` 并填入自己的 key。

```bash
cp .env.example .env
python "4-0agent实现/ReAct_agent.py"
```

`.env` 需要三个变量：

```
LLM_API_KEY=你的key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL_ID=deepseek-chat
```

> ⚠️ **`.env` 已被 `.gitignore` 排除，不要提交。** 仓库里只提供 `.env.example`。

---

## 关于测试方法

`4-0agent实现/SPEC.md` 里把「这一章要交什么」写成了 11 条可自动判定的验收标准
（含"工具结果必须出现在下一轮 prompt 里""Action 格式非法时不崩不死循环"等），
`check_react.py` 是裁判 —— 它注入一个**按剧本回话的假 LLM**，因此测试完全免费、可重复。

> 这套"先定验收标准，再写实现"的顺序，比先写完再想怎么测要省事得多。

---

## 学习来源

本项目是围绕开源教程 **Hello-Agents** 的学习实践：范式定义、章节结构和部分示例思路来自该教程，
**代码实现、测试脚本、踩坑记录为本人完成**。各目录内的 `学习路线.md`、`SPEC.md`、`note.md`
记录了当时的实现思路与设计取舍。

`agent_case_/1_3helloagent/` 为教程早期示例的个人改写版本，保留用于对照"关键词触发 → 模型自主决策"的演进。
