#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 4 章 · ReAct 检查器（外部观察，不读你的内部实现）

它只做三件事：
  1. import 你写的三个文件（llm_client.py / tools.py / react_agent.py）
  2. 用一个「按剧本回话的假 LLM」替掉真模型，因此默认不花钱、不需要 key
  3. 从外部观察行为，逐条对 SPEC.md 里的验收标准打分

用法（在 chapter4 目录下，与你的三个文件放在一起）：
    F:\\Python_Project\\.venv\\Scripts\\python.exe check_react.py
    F:\\Python_Project\\.venv\\Scripts\\python.exe check_react.py -v          # 打印每次测试里智能体自己的输出
    F:\\Python_Project\\.venv\\Scripts\\python.exe check_react.py --only 8    # 只跑某几条
    F:\\Python_Project\\.venv\\Scripts\\python.exe check_react.py --real      # 必过项全绿后，用真 key 跑一道真实问题

命名适配：默认按 SPEC 的 snake_case（register_tool / get_tool / get_available_tools），
若你写了书里的 camelCase（registerTool / getTool / getAvailableTools），这里也能认。
"""

from __future__ import annotations

import argparse
import copy
import importlib
import inspect
import io
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# Windows 管道下默认可能是 GBK，先兜住编码，免得智能体打印的 emoji 把检查器搞崩
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

# ---- 想换文件名/类名，只改这几行 ----
# 注意：这里必须和你磁盘上的文件名完全一致，Python 的 import 区分大小写。
AGENT_MODULE, AGENT_CLASS = "ReAct_agent", "ReActAgent"
TOOLS_MODULE, TOOLS_CLASS = "tools", "ToolExecutor"
LLM_MODULE, LLM_CLASS = "llm_client", "HelloAgentsLLM"


# =========================================================================
# 基础设施
# =========================================================================

class CheckFailure(Exception):
    """验收标准没达到（不是代码崩了）。"""


def expect(cond, msg):
    if not cond:
        raise CheckFailure(msg)


def _load(module_name: str, class_name: str):
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        raise CheckFailure(f"import {module_name}.py 失败：{type(exc).__name__}: {exc}")
    obj = getattr(module, class_name, None)
    if obj is None:
        raise CheckFailure(f"{module_name}.py 里找不到 {class_name}")
    return obj


def _attr(obj, *names):
    for name in names:
        fn = getattr(obj, name, None)
        if callable(fn):
            return fn
    raise CheckFailure(f"{type(obj).__name__} 上找不到这些方法中的任何一个：{', '.join(names)}")


def messages_to_text(messages) -> str:
    if messages is None:
        return ""
    if isinstance(messages, str):
        return messages
    parts = []
    try:
        iterator = list(messages)
    except TypeError:
        return str(messages)
    for item in iterator:
        if isinstance(item, dict):
            parts.append(str(item.get("content", "")))
        else:
            content = getattr(item, "content", None)
            parts.append(str(content) if content is not None else str(item))
    return "\n".join(parts)


class ScriptedLLM:
    """假 LLM：按剧本吐字符串；剧本里放异常对象就会真的抛出来。"""

    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []  # 每次收到的 messages（深拷贝，防止你复用列表把证据抹掉）

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def think(self, messages=None, *args, **kwargs):  # noqa: D401
        self.calls.append(copy.deepcopy(messages))
        if not self.responses:
            return "Thought: 剧本已经空了。\nAction: Finish[剧本已空]"
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    def prompt_at(self, index: int) -> str:
        return messages_to_text(self.calls[index])


def new_tool_executor():
    return _load(TOOLS_MODULE, TOOLS_CLASS)()


def register_tool(executor, name, description, func):
    _attr(executor, "register_tool", "registerTool")(name, description, func)


def get_tool(executor, name):
    return _attr(executor, "get_tool", "getTool")(name)


def get_available_tools(executor) -> str:
    return _attr(executor, "get_available_tools", "getAvailableTools")()


def make_agent(llm, executor, max_steps: int):
    cls = _load(AGENT_MODULE, AGENT_CLASS)
    try:
        params = inspect.signature(cls.__init__).parameters
    except (TypeError, ValueError):
        params = {}
    if "max_steps" in params or any(p.kind == p.VAR_KEYWORD for p in params.values()):
        return cls(llm, executor, max_steps=max_steps)
    return cls(llm, executor, max_steps)


class Env:
    """一条验收标准一个干净环境：新的工具执行器 + 新剧本 + 新的 Agent 实例。"""

    def __init__(self, max_steps: int = 5, responses=None):
        self.te = new_tool_executor()
        self.llm = ScriptedLLM(responses)
        self.agent = make_agent(self.llm, self.te, max_steps)
        self.tool_calls = []  # [(工具名, 入参)]

    def add_tool(self, name, description="测试工具", func=None):
        def wrapper(*args, **kwargs):
            if args:
                payload = args[0]
            elif kwargs:
                payload = next(iter(kwargs.values()))
            else:
                payload = None
            self.tool_calls.append((name, payload))
            return func(payload)
        register_tool(self.te, name, description, wrapper)

    def responses(self, items):
        self.llm.responses = list(items)


def only_calls(env, name):
    return [payload for tool_name, payload in env.tool_calls if tool_name == name]


# =========================================================================
# 验收标准 1~11
# =========================================================================

def t1_normal_two_rounds(env):
    """正常两轮：先调工具，再 Finish。"""
    env.add_tool("Search", "一个网页搜索引擎。", lambda q: "SEARCH_RESULT: 华为 Mate 70 是当前最新款")
    env.responses([
        "Thought: 这个问题我的知识库答不了，需要联网查。\nAction: Search[华为最新手机]",
        "Thought: 资料够了，可以收尾。\nAction: Finish[华为 Mate 70]",
    ])
    answer = env.agent.run("华为最新的手机是哪一款？")
    expect(answer is not None and "华为 Mate 70" in str(answer),
           f"期望返回 Final Answer（含『华为 Mate 70』），实际得到 {answer!r}")
    expect(only_calls(env, "Search") == ["华为最新手机"],
           f"Search 应被调用 1 次、入参正好是『华为最新手机』，实际收到 {env.tool_calls!r}")
    expect(env.llm.call_count == 2,
           f"LLM 应正好被调用 2 次，实际 {env.llm.call_count} 次")


def t2_no_extra_call_after_finish(env):
    """拿到 Finish 立刻返回，不再多调一次 LLM。"""
    env.responses(["Thought: 我直接知道答案。\nAction: Finish[42]"])
    answer = env.agent.run("1+1 等于几？")
    expect(str(answer).strip() == "42", f"期望立即返回 42，实际 {answer!r}")
    expect(env.llm.call_count == 1, f"Finish 之后不该再调 LLM，实际调了 {env.llm.call_count} 次")


def t3_invalid_action_format(env):
    """Action 格式非法：不崩、不死循环，作为 Observation 记下来继续。"""
    env.responses([
        "Thought: 我要搜一下。\nAction: Search[这里缺了右括号",
        "Thought: 上一轮格式不对，这次直接给答案。\nAction: Finish[兜底答案]",
    ])
    answer = env.agent.run("随便问点什么")
    expect(str(answer).strip() == "兜底答案",
           f"非法 Action 之后应能继续到 Finish，实际返回 {answer!r}")
    expect(env.llm.call_count == 2, f"应该恰好再问一轮 LLM，实际 {env.llm.call_count} 次")
    if env.llm.call_count >= 2:
        nxt = env.llm.prompt_at(1)
        if not any(word in nxt for word in ("错误", "Error", "error", "无效", "无法", "格式")):
            print("    [提示] 第 2 轮 prompt 里看不出给模型反馈了出错信息，建议把错误也写成 Observation")


def t4_multiline_action_input(env):
    """Action 输入含换行：工具要收到完整多行输入。"""
    env.add_tool("Search", "一个网页搜索引擎。", lambda q: "OK")
    env.responses([
        "Thought: 我分两行写这个查询。\nAction: Search[第一行查询\n第二行补充说明]",
        "Thought: 够了。\nAction: Finish[完成]",
    ])
    answer = env.agent.run("多行输入测试")
    expect(str(answer).strip() == "完成", f"期望返回『完成』，实际 {answer!r}")
    got = only_calls(env, "Search")
    expect(len(got) == 1, f"Search 应被调用 1 次，实际 {len(got)} 次")
    payload = got[0] or ""
    expect("第一行查询" in payload and "第二行补充说明" in payload,
           f"工具收到的入参被截断了：{payload!r}")


def t5_max_steps_guard():
    """一直不 Finish：到 max_steps 停下并返回 None，LLM 调用不超过 max_steps。"""
    env = Env(max_steps=3)
    env.add_tool("Search", "一个网页搜索引擎。", lambda q: "永远搜不到有用信息")
    env.responses(["Thought: 再搜一次。\nAction: Search[换个关键词]"] * 10)
    answer = env.agent.run("一个它永远回答不了的问题")
    expect(answer is None, f"跑不出答案时应返回 None，实际返回 {answer!r}")
    expect(env.llm.call_count <= 3, f"LLM 调用次数不应超过 max_steps=3，实际 {env.llm.call_count} 次")
    expect(env.llm.call_count >= 1, "一次都没调 LLM，说明主循环没跑起来")


def t6_empty_llm_response():
    """LLM 返回空字符串（以及 None）：不崩，返回 None。"""
    for bad in ("", None):
        env = Env(max_steps=5, responses=[bad])
        answer = env.agent.run("空响应测试")
        expect(answer is None, f"LLM 返回 {bad!r} 时应返回 None，实际 {answer!r}")


def t7_action_without_thought(env):
    """只有 Action 没有 Thought：照样执行。"""
    env.add_tool("Search", "一个网页搜索引擎。", lambda q: "有点东西")
    env.responses([
        "Action: Search[只有行动]",
        "Action: Finish[完成]",
    ])
    answer = env.agent.run("缺 Thought 的测试")
    expect(only_calls(env, "Search") == ["只有行动"],
           f"缺 Thought 也应执行工具，实际工具调用记录 {env.tool_calls!r}")
    expect(str(answer).strip() == "完成", f"期望返回『完成』，实际 {answer!r}")


def t8_observation_reaches_next_prompt(env):
    """工具返回的内容必须出现在下一轮 prompt 里 —— ReAct 的命根子。"""
    token = "OBS_TOKEN_8f3a1c"
    env.add_tool("Search", "一个网页搜索引擎。", lambda q: f"搜索命中：{token}")
    env.responses([
        "Thought: 先查。\nAction: Search[华为最新手机]",
        "Thought: 根据观察收尾。\nAction: Finish[好了]",
    ])
    env.agent.run("观察回流测试")
    expect(env.llm.call_count >= 2, "至少要有第二轮 LLM 调用才能检查观察回流")
    prompt_2 = env.llm.prompt_at(1)
    expect(token in prompt_2, "工具返回的内容没有出现在下一轮 prompt 里，ReAct 的信息闭环断了")
    expect("华为最新手机" in prompt_2 or "观察回流测试" in prompt_2,
           "下一轮 prompt 里既没有原始问题也没有历史，上下文丢了")


def t9_unknown_tool(env):
    """调用了不存在的工具：不崩，把错误当 Observation 反馈，然后能收尾。"""
    env.responses([
        "Thought: 我记得有个叫 Weather 的工具。\nAction: Weather[北京]",
        "Thought: 没有这个工具，那我直接给结论。\nAction: Finish[改用别的办法]",
    ])
    answer = env.agent.run("调不存在工具的测试")
    expect(str(answer).strip() == "改用别的办法", f"工具不存在时应能继续收尾，实际 {answer!r}")
    if env.llm.call_count >= 2:
        nxt = env.llm.prompt_at(1)
        if "Weather" not in nxt and "错误" not in nxt:
            print("    [提示] 第 2 轮 prompt 里没有提到 Weather 或错误信息，模型不知道自己上一轮错了")


def t10_tool_raises(env):
    """工具函数自己抛异常：捕获成 Observation，不炸穿主循环。"""
    def boom(_q):
        raise RuntimeError("工具内部炸了")

    env.add_tool("Search", "一个网页搜索引擎。", boom)
    env.responses([
        "Thought: 先搜。\nAction: Search[随便]",
        "Thought: 工具坏了，我直接说。\nAction: Finish[工具故障，改用兜底回答]",
    ])
    answer = env.agent.run("工具异常测试")
    expect(str(answer).strip() == "工具故障，改用兜底回答",
           f"工具抛异常不应炸穿主循环，实际返回 {answer!r}")


def t11_history_reset_between_runs():
    """两次 run() 之间历史重置，上一次的问题不污染这一次。"""
    leak = "LEAK_TOKEN_11zz"
    env = Env(max_steps=5)
    env.add_tool("Search", "一个网页搜索引擎。", lambda q: f"旧结果 {leak}")
    env.responses([
        "Thought: 先搜。\nAction: Search[第一个问题相关]",
        "Thought: 够了。\nAction: Finish[第一个答案]",
    ])
    first = env.agent.run("第一个问题：北京今天天气怎么样")
    expect(str(first).strip() == "第一个答案", f"第一次 run 应返回『第一个答案』，实际 {first!r}")

    env.responses(["Thought: 直接答。\nAction: Finish[第二个答案]"])
    calls_before = env.llm.call_count
    second = env.agent.run("第二个问题：上海今天天气怎么样")
    expect(str(second).strip() == "第二个答案", f"第二次 run 应返回『第二个答案』，实际 {second!r}")
    expect(env.llm.call_count == calls_before + 1, "第二次 run 应该只调一次 LLM（Finish 就返回）")
    fresh_prompt = env.llm.prompt_at(calls_before)
    expect(leak not in fresh_prompt and "第一个问题" not in fresh_prompt,
           "上一次 run 的历史污染了这一次的 prompt（run() 开头要重置 history）")


# =========================================================================
# 结构检查（文件 + 接口契约）
# =========================================================================

def structural_check():
    problems = []
    for module_name in (LLM_MODULE, TOOLS_MODULE, AGENT_MODULE):
        path = HERE / f"{module_name}.py"
        if not path.exists():
            problems.append(f"缺少文件 {path.name}")

    notes = []
    if not problems:
        try:
            _load(TOOLS_MODULE, TOOLS_CLASS)
        except CheckFailure as exc:
            problems.append(str(exc))
        try:
            _load(AGENT_MODULE, AGENT_CLASS)
        except CheckFailure as exc:
            problems.append(str(exc))
        try:
            llm_cls = _load(LLM_MODULE, LLM_CLASS)
            if not callable(getattr(llm_cls, "think", None)):
                problems.append(f"{LLM_MODULE}.{LLM_CLASS} 上没有 think 方法")
        except CheckFailure as exc:
            notes.append(f"{exc}（不影响假剧本测试，但 --real 时要用）")
    return problems, notes


# =========================================================================
# 跑测试
# =========================================================================

REQUIRED = [
    (1, "正常两轮：工具 → Finish", t1_normal_two_rounds),
    (2, "Finish 后立即返回，不补调 LLM", t2_no_extra_call_after_finish),
    (3, "Action 格式非法不崩、继续", t3_invalid_action_format),
    (4, "Action 输入含换行不截断", t4_multiline_action_input),
    (5, "超 max_steps 停下并返回 None", t5_max_steps_guard),
    (6, "LLM 返回空串不崩", t6_empty_llm_response),
    (7, "只有 Action 没有 Thought 也能执行", t7_action_without_thought),
    (8, "Observation 进入下一轮 prompt", t8_observation_reaches_next_prompt),
]

def t12_zero_argument_tool(env):
    """零参数工具：Action 写成 `工具名[]` 也必须真的被执行。"""
    called = []
    env.add_tool("GetTime", "获取当前的本地日期与时间。",
                 lambda q=None: (called.append(q), "2026-09-17 14:00:00")[1])
    env.responses([
        "Thought: 需要知道现在几点。\nAction: GetTime[]",
        "Thought: 已经拿到时间了。\nAction: Finish[现在是 2026-09-17 14:00]",
    ])
    answer = env.agent.run("现在几点了？")
    expect(str(answer).strip() == "现在是 2026-09-17 14:00",
           f"期望返回最终答案，实际 {answer!r}")
    expect(len(called) == 1,
           f"`GetTime[]`（零参数调用）必须真的执行一次工具，实际执行 {len(called)} 次"
           "——空输入是合法的，不能当成格式错误拦掉（书里的 `not tool_input` 就错在这）")


BONUS = [
    (9, "调用不存在的工具不崩", t9_unknown_tool),
    (10, "工具抛异常不炸穿主循环", t10_tool_raises),
    (11, "两次 run() 之间历史重置", t11_history_reset_between_runs),
    (12, "零参数工具（工具名[]）必须真的执行", t12_zero_argument_tool),
]


def run_one(number, title, fn, verbose):
    buf = io.StringIO()
    status = "PASS"
    detail = ""
    try:
        takes_env = len(inspect.signature(fn).parameters) > 0
    except (TypeError, ValueError):
        takes_env = False
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            fn(Env()) if takes_env else fn()
    except CheckFailure as exc:
        status = "FAIL"
        detail = str(exc)
    except Exception as exc:  # 你的实现自己炸了
        status = "ERROR"
        detail = f"{type(exc).__name__}: {exc}"
        tb = traceback.format_exc(limit=6)
    else:
        tb = ""
    captured = buf.getvalue()

    mark = {"PASS": "✅", "FAIL": "❌", "ERROR": "💥"}[status]
    print(f"{mark} #{number:<2} {title}  -> {status}")
    if detail:
        print(f"      {detail}")
    if status == "ERROR":
        print("      " + tb.replace("\n", "\n      ").rstrip())
    if (verbose or status != "PASS") and captured.strip():
        print("      ---- 智能体自己的输出 ----")
        print("      " + captured.strip().replace("\n", "\n      "))
    return status == "PASS"


def real_run(question: str):
    print("\n=== 真实模式：用你 .env 里的真 key 跑一遍 ===")
    try:
        from dotenv import load_dotenv  # type: ignore
        for candidate in (HERE / ".env", HERE.parent / ".env", Path.cwd() / ".env"):
            if candidate.exists():
                load_dotenv(candidate, override=False)
                print(f"已加载 {candidate}")
    except ImportError:
        pass

    try:
        llm_cls = _load(LLM_MODULE, LLM_CLASS)
        llm = llm_cls()
    except Exception as exc:
        print(f"❌ 真实 LLM 初始化失败：{type(exc).__name__}: {exc}")
        print("   检查 chapter4/.env（或 llm_client.py 里 load_dotenv 的路径）里的三个变量是否填了真值。")
        return 1

    import datetime

    executor = new_tool_executor()
    register_tool(
        executor,
        "GetTime",
        "获取当前的本地日期与时间。当问题涉及『现在几点』『今天几号』这类实时信息时使用。",
        lambda _q=None: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    register_tool(
        executor,
        "Calculator",
        "计算一个数学表达式，输入应当是纯表达式，例如 (123+456)*789/12。",
        lambda expr: f"{expr} = {eval(str(expr), {'__builtins__': {}}, {})}",  # noqa: S307
    )
    agent = make_agent(llm, executor, 5)
    print(f"问题：{question}")
    answer = agent.run(question)
    print(f"\n最终答案：{answer!r}")
    return 0 if answer else 1


def main():
    parser = argparse.ArgumentParser(description="第 4 章 ReAct 检查器")
    parser.add_argument("-v", "--verbose", action="store_true", help="通过时也打印智能体自己的输出")
    parser.add_argument("--only", default="", help="只跑指定编号，例如 --only 3,4,8")
    parser.add_argument("--real", nargs="?", const="现在几点了？请调用工具确认后再回答。",
                        help="必过项全绿后，用真 key 跑一道真实问题")
    args = parser.parse_args()

    print(f"检查目录：{HERE}")

    problems, notes = structural_check()
    if problems:
        print("\n结构检查没通过：")
        for item in problems:
            print(f"  ❌ {item}")
        print("\n先按 SPEC.md 的接口契约把三个文件补齐，再回来跑。")
        return 1
    print("结构检查：三个文件与类都在 ✅")
    for note in notes:
        print(f"  [提示] {note}")

    selected = {int(x) for x in args.only.replace("，", ",").split(",") if x.strip().isdigit()}
    if args.real is not None:
        selected = set()  # --real 之前，先把所有假剧本检查跑完
    verbose = args.verbose

    print("\n--- 必过项 ---")
    required_pass = 0
    for number, title, fn in REQUIRED:
        if selected and number not in selected:
            continue
        required_pass += 1 if run_one(number, title, fn, verbose) else 0
    print("\n--- 加分项 ---")
    bonus_pass = 0
    for number, title, fn in BONUS:
        if selected and number not in selected:
            continue
        bonus_pass += 1 if run_one(number, title, fn, verbose) else 0

    if not selected:
        print(f"\n必过项 {required_pass}/{len(REQUIRED)} · 加分项 {bonus_pass}/{len(BONUS)}")
    if required_pass < len(REQUIRED):
        print("\n还没到跑真实问题的火候：先把必过项清干净。卡住了就说一声，按『方向提示 → 骨架 → 代码』三级给。")
        return 1
    print("\n🎉 必过项全绿。")
    if args.real is not None:
        return real_run(args.real)
    print("下一步：")
    print("  1) 确认这个目录的 .env 里有 LLM_API_KEY / LLM_MODEL_ID / LLM_BASE_URL")
    print(f"  2) {Path(sys.executable)} {HERE / 'check_react.py'} --real")
    print("  3) 真实跑通后，再回 PDF 对照书里的实现，做一次设计差异复盘。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
