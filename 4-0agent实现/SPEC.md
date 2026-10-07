# 第 4 章 · ReAct 手写规格（不剧透版）

> 这份文件只写**要什么**和**怎么判合格**，不写**怎么实现**。
> 实现由你写；`check_react.py` 只从外部观察你的 Agent 行为。
> 卡住时喊我，按方向提示 → 结构骨架 → 代码 三级给，默认只给第一级。

---

## 一、这一章你要交的东西

在 `hello_agents_self/chapter4/` 下自己写三个文件（文件名固定，检查脚本要 import）：

| 文件 | 职责 | 要求 |
| --- | --- | --- |
| `llm_client.py` | 包一层 LLM 调用 | 提供 `think(messages) -> str`，内部走 `openai` SDK + `.env` 里的 key，出错时不要抛出去把主循环打死 |
| `tools.py` | 工具注册与执行 | 提供 `ToolExecutor` 类，见下面接口契约 |
| `react_agent.py` | ReAct 主循环 | 提供 `ReActAgent` 类，见下面接口契约 |

**接口契约**（这一层我替你定死，好让自动化检查能接进来；内部怎么组织、怎么命名，全随你）：

```python
# react_agent.py
class ReActAgent:
    def __init__(self, llm_client, tool_executor, max_steps: int = 5): ...
    def run(self, question: str) -> str | None: ...   # 拿到 Final Answer 返回字符串；跑不出来返回 None

# tools.py
class ToolExecutor:
    def register_tool(self, name: str, description: str, func) -> None: ...
    def get_available_tools(self) -> str: ...          # 返回给 LLM 看的工具清单文本
    def get_tool(self, name: str): ...                 # 找不到时返回 None（不要抛异常）

# llm_client.py
class HelloAgentsLLM:
    def think(self, messages: list[dict]) -> str: ...  # messages 是 OpenAI 格式
```

想换命名也行，改 `check_react.py` 顶部那几行适配即可；但**别为了迁就测试改坏设计**。

---

## 二、文本协议（Agent 与 LLM 之间的约定）

LLM 每轮必须按这个格式回话，你的解析器要认它：

```
Thought: 你的推理，可以多行
Action: Search[华为最新手机]
```

Action 只有两种合法形态：

- `工具名[输入]` —— 调工具
- `Finish[最终答案]` —— 收工，答案就是括号里的内容

你每执行一次工具，要把结果以 `Observation: ...` 追加进历史，下次连同历史一起发给 LLM。

> 这一节是整个第 4 章的骨架，想清楚"历史里到底存了什么、下次 prompt 长什么样"，比写代码重要。

---

## 三、验收标准（`check_react.py` 会逐条查）

| # | 场景 | 期望行为 | 权重 |
| --- | --- | --- | --- |
| 1 | 正常两轮：先调工具，再 `Finish` | 返回最终答案；工具被调用 1 次且入参正确；LLM 正好被调用 2 次 | 必过 |
| 2 | 拿到 `Finish` 之后 | 立即返回，**不再**多调一次 LLM | 必过 |
| 3 | Action 格式非法（比如缺 `]`） | 不崩、不死循环；把错误作为 Observation 追加并继续 | 必过 |
| 4 | Action 输入含换行 | 工具收到完整的多行输入，不被截断 | 必过 |
| 5 | 一直不 `Finish`，超过 `max_steps` | 停下并返回 `None`，LLM 调用次数不超过 `max_steps` | 必过 |
| 6 | LLM 返回空字符串 | 不崩，返回 `None` | 必过 |
| 7 | 只有 `Action` 没有 `Thought` | 照样能执行，不能因为缺 Thought 就罢工 | 必过 |
| 8 | 工具返回的内容 | 必须出现在**下一轮**发给 LLM 的 prompt 里（这是 ReAct 的命根子） | 必过 |
| 9 | 调用了不存在的工具 | 不崩，把错误作为 Observation 反馈，然后能收尾 | 加分 |
| 10 | 工具函数自己抛异常 | 捕获成 Observation，不炸穿主循环 | 加分 |
| 11 | 每次 `run()` 之间 | 历史被重置，上一次的问题不污染这一次 | 加分 |

---

## 四、怎么跑

```powershell
F:\Python_Project\.venv\Scripts\python.exe F:\Python_Project\hello_agents_self\chapter4\check_react.py
```

检查脚本**不需要真实 API key**，它用一个假的 LLM 按剧本回话，不花你一分钱。
等全部必过项都绿了，再跑一次真实问题（脚本末尾会提示怎么跑），最后才回 PDF 对照正文的实现，做设计差异复盘。

---

## 五、学习提醒

- PDF 正文里带完整代码块，**先别看**。第一遍只读"为什么要有 Thought / 为什么要有 Observation / 为什么要有 max_steps"。
- 你现有 `agent_try_case01/main.py` 那种"检测到 `[TIME]` 就替换"的写法属于**关键词触发**，跟 ReAct 的区别正好是这一章的核心，写的时候可以对比着想想差在哪。
