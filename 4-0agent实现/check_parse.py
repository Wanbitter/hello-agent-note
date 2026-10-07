#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 4 章 · 解析器体检器（check_parse.py）

它只干一件事：**拿一堆「模型真实会写出来的东西」去喂你的解析器，看它扛不扛得住。**

为什么需要它
------------
你的 ReAct 智能体全靠正则，从模型的回复里切出 Thought 和 Action。
正则只对「你想到的写法」有效，而模型的写法你穷举不完。
这个脚本就是那张「穷举表」——你改一版解析器，跑一次，看分数变化。

两段检查
--------
  A 段：解析器单测 —— 直接调你的 _parse_output / _parse_action
  B 段：端到端鲁棒性 —— 用假 LLM 走一次完整 run()，看会不会**崩**
        （崩溃是最高优先级的 bug：一崩全崩，连错误提示都喂不回去）

用法
----
    F:\\Python_Project\\.venv\\Scripts\\python.exe check_parse.py
    F:\\Python_Project\\.venv\\Scripts\\python.exe check_parse.py -v   # 连原始文本一起打出来

判分
----
  必过：正常写法必须认出来；任何一条都**不许抛异常**
  加分：模型的坏习惯（装饰、大小写、全角、换格式）能认出来
"""

from __future__ import annotations

import argparse
import copy
import importlib
import io
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# Windows 管道下默认可能是 GBK，先兜住编码，免得 emoji 把脚本搞崩
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

# ---- 你换文件名/类名，只改这一行 ----
AGENT_MODULE, AGENT_CLASS = "ReAct_agent", "ReActAgent"


# =========================================================================
# A 段：模型可能写出来的东西 → 期望切出的 (工具名, 输入)
# =========================================================================
# 每行三项：类别、说明、模型写的文本、期望结果
# 期望 (None, None) = 「正确行为就是切不出来」（比如压根没写 Action 行）

CASES = [
    # -------- 必过：这些都是正常写法，必须认出来 --------
    ("必过", "标准单行写法",       "Thought: 需要搜索\nAction: Search[华为手机]",            ("Search", "华为手机")),
    ("必过", "Thought 后空一行",   "Thought: 需要搜索\n\nAction: Search[华为手机]",          ("Search", "华为手机")),
    ("必过", "Action 输入跨多行",  "Thought: x\nAction: Search[第一行\n第二行]",             ("Search", "第一行\n第二行")),
    ("必过", "Action 后面带结语",  "Thought: x\nAction: Search[华为手机]\n希望帮到你",        ("Search", "华为手机")),
    ("必过", "完全没有 Action 行", "Thought: 我想想……",                                      (None, None)),
    ("必过", "零参数工具",         "Thought: 现在几点\nAction: GetTime[]",                   ("GetTime", "")),

    # -------- 加分：模型的坏习惯，能认出来更稳 --------
    ("加分", "反引号包裹",         "Thought: x\nAction: `Search[华为手机]`",                 ("Search", "华为手机")),
    ("加分", "Markdown 加粗",      "Thought: x\nAction: **Search[华为手机]**",               ("Search", "华为手机")),
    ("加分", "全角括号【】",       "Thought: x\nAction: Search【华为手机】",                 ("Search", "华为手机")),
    ("加分", "Action 前多写了字",  "Thought: x\nAction: 使用 Search[华为手机]",              ("Search", "华为手机")),
    ("加分", "小写 action/thought","thought: 需要搜索\naction: Search[华为手机]",            ("Search", "华为手机")),
    ("加分", "中文冒号：",         "Thought：需要搜索\nAction：Search[华为手机]",            ("Search", "华为手机")),
    ("加分", "JSON 风格 Action",   'Thought: x\nAction: {"tool": "Search", "input": "华为"}', ("Search", "华为")),
]


# =========================================================================
# 假 LLM + 假工具：B 段端到端测试用，不需要真模型、不花钱
# =========================================================================

class ScriptedLLM:
    """按剧本回话的假模型。"""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def think(self, messages=None, *args, **kwargs):
        self.calls.append(copy.deepcopy(messages))
        if not self.script:
            return "Thought: 剧本空了。\nAction: Finish[剧本空了]"
        return self.script.pop(0)


class FakeTools:
    """假的工具执行器：只要能回答「有哪些工具」「取某个工具」就够了。"""

    def getAvailableTools(self):          # 书里是驼峰，保留
        return "- Search: 一个假的搜索引擎。"

    get_available_tools = getAvailableTools   # 下划线版也提供一份，随你怎么写

    def getTool(self, name):
        return lambda tool_input: f"假的观察结果：{tool_input}"

    get_tool = getTool


# B 段用例：这里只关心一件事 —— **run() 会不会抛异常**
# 期望行为：不崩就算过（返回 None 或返回答案都可以）
CRASH_CASES = [
    ("必过", "标准 Finish",       "Thought: x\nAction: Finish[一共55个]"),
    ("必过", "Finish 带结语",     "Thought: x\nAction: Finish[一共55个]\n\n以上。"),
    ("必过", "Finish 没有方括号", "Thought: x\nAction: Finish"),
    ("必过", "Finish 答案跨多行", "Thought: x\nAction: Finish[第一行\n第二行]"),
    ("加分", "小写 action",       "thought: x\naction: Search[华为手机]"),
]


# =========================================================================
# 基础设施
# =========================================================================

def make_agent():
    """造一个只用来调解析方法的 agent 实例。

    你的 _parse_output / _parse_action 不需要 llm_client 和 tool_executor，
    所以先试着直接构造（传 None），构造不了就绕过 __init__ 硬造一个空壳。
    """
    cls = getattr(importlib.import_module(AGENT_MODULE), AGENT_CLASS)
    try:
        return cls(None, None)
    except Exception:
        return cls.__new__(cls)


def show(text: str) -> str:
    """把换行显示成 \\n，好让表格一行放得下。"""
    return text.replace("\n", "\\n")


# =========================================================================
# A 段
# =========================================================================

def run_parser_section(agent, verbose: bool):
    print("=" * 78)
    print("A 段 · 解析器单测（直接喂 _parse_output / _parse_action）")
    print("=" * 78)
    print(f"{'结果':<6}{'类别':<6}{'场景':<18}{'切出来的 action':<34}实际结果")
    print("-" * 78)

    passed_required = passed_bonus = total_required = total_bonus = 0

    for kind, name, text, expect in CASES:
        if kind == "必过":
            total_required += 1
        else:
            total_bonus += 1

        try:
            thought, action = agent._parse_output(text)
            got = agent._parse_action(action) if action is not None else (None, None)
            crashed = False
        except Exception as exc:
            got, action, crashed = f"崩溃 {type(exc).__name__}", "<前面就崩了>", True

        ok = (got == expect) and not crashed
        if ok:
            if kind == "必过":
                passed_required += 1
            else:
                passed_bonus += 1

        print(f"{'PASS' if ok else 'FAIL':<6}{kind:<6}{name:<18}{show(str(action))[:32]:<34}{got!r}")
        if not ok:
            print(f"      期望 {expect!r}")
            if verbose:
                print(f"      原始文本: {show(text)}")

    return passed_required, total_required, passed_bonus, total_bonus


# =========================================================================
# B 段
# =========================================================================

def run_e2e_section(agent, verbose: bool):
    print()
    print("=" * 78)
    print("B 段 · 端到端鲁棒性（用假 LLM 走一次完整 run()，只问：崩不崩？）")
    print("=" * 78)

    passed = total = 0
    for kind, name, text in CRASH_CASES:
        total += 1
        buf = io.StringIO()
        crashed = None
        answer = None

        # run() 会打印一大堆，先接住；只有崩了才回放给你看
        try:
            with redirect_stdout(buf), redirect_stderr(buf):
                llm = ScriptedLLM([text, "Thought: 兜底。\nAction: Finish[兜底答案]"])
                fresh = make_agent()
                # 换掉依赖：直接给实例塞上假的 llm / 工具
                fresh.llm_client = llm
                fresh.tool_executor = FakeTools()
                fresh.max_steps = 2
                fresh.history = []
                answer = fresh.run("鲁棒性测试")
        except Exception as exc:
            crashed = f"{type(exc).__name__}: {exc}"

        ok = crashed is None
        if ok:
            passed += 1

        print(f"{'PASS' if ok else 'FAIL':<6}{kind:<6}{name:<18}返回值={answer!r}")
        if crashed:
            print(f"      💥 崩了 -> {crashed}")
            print(f"      模型的原文: {show(text)}")
            if verbose:
                print("      ---- run() 崩之前的输出 ----")
                print("      " + buf.getvalue().strip().replace("\n", "\n      "))

    return passed, total


def main():
    parser = argparse.ArgumentParser(description="解析器体检器")
    parser.add_argument("-v", "--verbose", action="store_true", help="失败时连原始文本/中间输出一起打印")
    args = parser.parse_args()

    print(f"检查目录：{HERE}")
    try:
        agent = make_agent()
    except Exception as exc:
        print(f"❌ 载入 {AGENT_MODULE}.py 失败：{type(exc).__name__}: {exc}")
        return 1

    pr, tr, pb, tb = run_parser_section(agent, args.verbose)
    ep, et = run_e2e_section(agent, args.verbose)

    print()
    print("=" * 78)
    print(f"A 段 解析器  必过 {pr}/{tr} · 加分 {pb}/{tb}")
    print(f"B 段 不崩     {ep}/{et}")
    print("=" * 78)

    if ep < et:
        print("⚠️ 有崩溃项 —— 崩溃优先级最高，先修它（提示：看看 Finish 那行的 re.match 有没有判空）。")
    if pr < tr:
        print("⚠️ 必过项没满 —— 正常写法都认不出来，先把这些修好。")
    elif pb < tb:
        print("💡 必过项全绿。加分的那些是模型的坏习惯，能认出来就更抗造。")
    else:
        print("🎉 全绿：正常写法稳，坏习惯也扛得住。")

    return 0 if (ep == et and pr == tr) else 1


if __name__ == "__main__":
    sys.exit(main())
