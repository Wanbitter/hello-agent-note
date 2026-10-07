# 第 7 章 · 关卡规格（只写"要什么"和"怎么判合格"）

> 本文件按关卡逐步追加。现在只有**关卡 1（7.2 LLM 中枢的继承式扩展）**。
> 实现由你写；`check_ch7_llm.py` 只从外部观察行为。
> 卡住时喊我，按 **方向提示 → 结构骨架 → 代码** 三级给，默认只给第一级。

---

## 关卡 1 · 7.2 扩展 `HelloAgentsLLM`

### 一、这一关要交的东西

在 `7-0agent实现/` 下写两个文件（文件名固定，检查脚本要 import）：

| 文件 | 职责 | 要求 |
| --- | --- | --- |
| `my_llm.py` | 你自己的 LLM 客户端 | `class MyLLM(HelloAgentsLLM)`，**通过继承**增加 ModelScope 支持；其余 provider 一律交回父类 |
| `my_main.py` | 使用示例 | 用 `MyLLM(provider="modelscope")` 发一条消息并把流式响应打印出来（写好后自己跑一次真 key） |

**接口契约**（这一层我替你定死，好让检查器能接进来）：

```python
# my_llm.py
from hello_agents import HelloAgentsLLM

class MyLLM(HelloAgentsLLM):
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        provider: str | None = "auto",
        **kwargs,
    ): ...
```

想换命名也行，改 `check_ch7_llm.py` 顶部那两行适配即可；但**别为了迁就测试改坏设计**。

### 二、行为规格

1. **`provider="modelscope"` 走你自己的分支**
   - `api_key`：显式传入 > `MODELSCOPE_API_KEY` 环境变量；两者都没有 → **构造时必须失败**（抛异常，消息里要能看出是缺 key）
   - `base_url`：显式传入 > 默认值 `https://api-inference.modelscope.cn/v1/`
     （检查器**不会**在 modelscope 场景下设置 `LLM_BASE_URL`，所以这里怎么兜底随你设计）
   - `model`：显式传入 > `LLM_MODEL_ID` > 你自己给的默认模型
   - `temperature` / `max_tokens` 等参数要能从 `**kwargs` 里生效（默认 temperature = 0.7）
   - 对象上要有可用的 `_client`（OpenAI 客户端实例）

2. **其它 `provider`（包括 `"auto"`）一个字都别改，原样 `super().__init__(...)`**
   - `MyLLM(provider="openai")` 要和 `HelloAgentsLLM(provider="openai")` 表现一致（key 从 `OPENAI_API_KEY` 取、base_url 用官方默认）
   - 不传 provider 时，父类那套环境变量解析（`LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL_ID`）照旧生效

3. **必须是"真继承"，不是空壳**
   - `MyLLM` 得是 `HelloAgentsLLM` 的子类，且真的重写了 `__init__` / `_auto_detect_provider` / `_resolve_credentials` 中的**至少一个**（`class MyLLM(HelloAgentsLLM): pass` 这种不算，检查器会拦）

4. **不能改库源码**
   - `site-packages\hello_agents\` 里的文件一个都不许动。理由：升级即失效，这也是书 7.2.1 的立论起点

### 三、验收标准（`check_ch7_llm.py` 会逐条查）

| # | 场景 | 期望行为 | 权重 |
| --- | --- | --- | --- |
| 1 | 子类结构与"真的重写了" | `MyLLM` 是 `HelloAgentsLLM` 的子类且非空壳 | 必过 |
| 2 | `MODELSCOPE_API_KEY` + `provider="modelscope"` | provider / api_key / base_url / model 全部正确，`_client` 就绪，temperature 默认 0.7 | 必过 |
| 3 | 显式参数 vs 环境变量 | 显式 `api_key` / `base_url` / `model` / `temperature` / `max_tokens` 全部优先 | 必过 |
| 4 | 没有任何 modelscope 凭据 | 构造失败（抛异常），而不是拿空 key 硬上 | 必过 |
| 5 | 不传 provider（只有 `LLM_*`） | 父类的环境变量解析照旧生效：key/base_url/model 都取自 `LLM_*` | 必过 |
| 6 | `provider="openai"` | 走父类那条路：key 取自 `OPENAI_API_KEY`，base_url 是官方默认值 | 必过 |
| 7 | 把 `MyLLM` 实例喂给框架的 `SimpleAgent` | 构造不报错，`think` / `invoke` 都还在（说明你**没有**破坏父类接口） | 必过 |
| 8 | 加分：显式 `provider="siliconflow"` | 见下面第四节的自定义 provider 契约 | 加分 |
| 9 | 加分：只设 `SILICONFLOW_API_KEY`、不传 provider | 能被**自动检测**成 siliconflow（对应习题 2） | 加分 |

检查器不需要真实 key、**不联网**：它只构造客户端、不发起请求。

### 四、加分题契约（习题 2）：再加一个父类没有的 provider

父类**已经**内置了 openai / deepseek / qwen / modelscope / kimi / zhipu / ollama / vllm / local，
所以要证明"扩展能力"，得加一个父类没有的。这里定死一套参数，检查器才好验：

| 项 | 值 |
| --- | --- |
| provider 名 | `siliconflow` |
| 环境变量 | `SILICONFLOW_API_KEY` |
| 默认 base_url | `https://api.siliconflow.cn/v1` |
| 默认 model | 随你（非空即可），例如 `Qwen/Qwen2.5-7B-Instruct` |

> 方向提示（不给代码）：
> ① 父类把"判断 provider"和"解析凭据"拆成了**两个钩子方法**，而且它们都是在 `__init__` 里被 `self.` 调用的。
>    想清楚"要让第 8 条和第 9 条同时成立"，就知道这两个钩子是不是得**成对**处理了。
> ② 还有一处小陷阱：父类里写的是 `provider or self._auto_detect_provider(...)`，而字符串 `"auto"` 是**真值**，
>    你的构造函数默认值又正好是 `"auto"`。所以"不传 provider 就会自动检测"这件事**不会**自动发生——
>    你得先决定：把 `"auto"` 当"用户没指定"，还是当"用户就是要通用配置"。

### 五、怎么跑

```powershell
$env:PYTHONIOENCODING='utf-8'
F:\Python_Project\.venv\Scripts\python.exe F:\Python_Project\7-0agent实现\check_ch7_llm.py
F:\Python_Project\.venv\Scripts\python.exe F:\Python_Project\7-0agent实现\check_ch7_llm.py -v        # 通过时也打印细节
F:\Python_Project\.venv\Scripts\python.exe F:\Python_Project\7-0agent实现\check_ch7_llm.py --only 4  # 只跑某条
```

必过项全绿之后，再用真 key 跑 `my_main.py`（这一步要花钱，你自己决定什么时候跑）。

### 六、学习提醒

- **先别看** `site-packages\hello_agents\core\llm.py` 的实现，先按 7.2.1 的文字自己写。
  写不出时，优先问自己三个问题：非 modelscope 的情况我怎么"还回去"？父类的哪些东西我必须自己补？
  缺 key 的时候应该在哪一行失败？
- `think()` 是**流式生成器**（`Iterator[str]`），`invoke()` 返回整段字符串——你的 `my_main.py` 用哪个，
  取决于你想不想要打字机效果。这两个方法都在父类里，你**不需要重写**。
- 复盘阶段再翻源码，对照着回答：书里的 `MyLLM` 和你的，在"参数校验时机"和"默认值来源"上有几处不同？为什么？
