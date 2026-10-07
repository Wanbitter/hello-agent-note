"""Agent 核心。
一个带工具调用能力的对话 agent：
    用户提问 → 模型决定调工具 → 执行工具 → 把结果喂回模型 → …… → 最终回答
对外提供两种"交付方式"：
    agent_stream() —— 生成器，边跑边 yield 事件（HTTP 流式接口用）
    agent_reply()  —— 普通函数，把事件消费掉，只返回最终回答（终端用）
两者共用同一份循环实现：agent_reply 只是 agent_stream 的一个消费者。
"""
import json
import os
from collections.abc import Iterable
from time import perf_counter
import openai
from dotenv import load_dotenv
from config import SYSTEM_PROMPT, MODEL_ID, BASE_URL
from tools import REGISTRY, SCHEMAS
load_dotenv()

client = openai.Client(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=BASE_URL,
)

MAX_STEPS = 8   # 一次提问内最多来回几轮：防止模型反复调同一个失败的工具、无限烧钱


def run_tool(call) -> str:
    """执行模型申请的一个工具，返回【文本】结果。
    两条约定：
      1. 一律返回字符串 —— 模型只能读文本，读不了 Python 对象。
      2. 异常也转成文本返回，绝不往外抛 —— 抛出去就没有"模型看到错误、自己纠正"这一步了。
    """
    name = call.function.name
    func = REGISTRY.get(name)
    if func is None:
        return f"错误：没有名为 {name} 的工具"

    try:
        args = json.loads(call.function.arguments or "{}")
        return str(func(**args))
    except Exception as e:
        return f"错误：{type(e).__name__}: {e}"


def agent_stream(user_input: str, history: list) -> Iterable[dict]:
    """跑一次完整的 agent 循环，每发生一件事就 yield 一个事件。

    history 由调用方保管，本函数【就地修改】它（追加 user / assistant / tool 消息）。

    yield 的事件类型：
        {"type": "tool_call",   "name": ..., "args": ...}   调用工具【之前】
        {"type": "tool_result", "name": ..., "text": ...}   工具返回【之后】
        {"type": "stats",       "seconds": ..., "model_calls": ...,
                                "tokens_in": ..., "tokens_out": ..., "thinking": ...}
        {"type": "final",       "text": ...}                最终回答（正常结束）
        {"type": "error",       "text": ...}                达到最大步数（异常结束）
    """
    history.append({"role": "user", "content": user_input})

    started = perf_counter()
    model_calls = 0
    tokens_in = 0
    tokens_out = 0
    thinking_tokens = 0

    def stats_event() -> dict:
        """本次问答的成本快照（闭包：读的是上面那几个计数器）。"""
        return {
            "type": "stats",
            "seconds": round(perf_counter() - started, 2),
            "model_calls": model_calls,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "thinking": thinking_tokens,
        }

    for _ in range(MAX_STEPS):
        model_calls += 1
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=history,
            tools=SCHEMAS,
        )
        msg = response.choices[0].message

        # 用量先累加、再判断分支。反过来的话只会统计到最后一次调用，成本少算一大半
        usage = response.usage
        tokens_in += usage.prompt_tokens
        tokens_out += usage.completion_tokens
        detail = usage.completion_tokens_details
        if detail is not None and detail.reasoning_tokens:
            thinking_tokens += detail.reasoning_tokens

        # 模型没有申请工具 = 这就是最终回答
        if not msg.tool_calls:
            history.append({"role": "assistant", "content": msg.content})
            yield stats_event()
            yield {"type": "final", "text": msg.content}
            return

        # 模型申请了工具：申请单必须存档。
        # 下一轮发工具结果时，协议要求结果能对上一条带 tool_calls 的 assistant 消息
        history.append(msg)

        for call in msg.tool_calls:
            yield {
                "type": "tool_call",
                "name": call.function.name,
                "args": call.function.arguments,
            }
            result = run_tool(call)
            yield {
                "type": "tool_result",
                "name": call.function.name,
                "text": result,
            }
            history.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": result,
            })

    # 循环跑完还没拿到最终回答 = 撞上了最大步数
    yield stats_event()
    yield {"type": "error", "text": "达到最大步数，没能得出最终答案"}


def agent_reply(user_input: str, history: list) -> str:
    """非流式入口：消费 agent_stream 的事件，只返回最终回答的文本。

    终端场景用它；HTTP 流式场景直接迭代 agent_stream。
    """
    reply = ""
    last_stats = None

    for event in agent_stream(user_input, history):
        kind = event["type"]

        if kind == "tool_call":
            print(f"  [调用工具] {event['name']} {event['args']}")
        elif kind == "tool_result":
            print(f"  [工具返回] {event['text']}")
        elif kind == "stats":
            last_stats = event                 # 记下来，等回答打完再显示
        else:                                  # final / error
            reply = event["text"]

    if last_stats:
        print(
            f"  [本次] 用时 {last_stats['seconds']}s"
            f" | 模型调用 {last_stats['model_calls']} 次"
            f" | 输入 {last_stats['tokens_in']} tokens"
            f" / 输出 {last_stats['tokens_out']}（思考 {last_stats['thinking']}）"
        )

    return reply


def main() -> None:
    """终端界面：读输入，交给 agent_reply 处理。"""
    history = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        try:
            user_input = input("\n你说: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n再见")
            break

        if user_input in {"quit", "exit"}:
            break
        if not user_input:
            continue

        print("助手:", agent_reply(user_input, history))


if __name__ == "__main__":
    main()
