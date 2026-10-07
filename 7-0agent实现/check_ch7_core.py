#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 7 章 · 关卡 2 检查器：把 7.3 的三个类"问穿"（预测-验证式）

用法（重点不是"跑"，是"先猜再跑"）：
    1) 先别运行。把下面每一题的**预测**写在 7-0agent实现\\note.md 里（一行一题，例如 "3: 报错"）
    2) 再运行：
         F:\\Python_Project\\.venv\\Scripts\\python.exe check_ch7_core.py
    3) 对答案：预测错的那几条，就是你要回去读源码的地方

它测的是**框架 0.1.1 的 Message / Config / Agent 三个类**（不是你写的代码），
所以不需要 my_llm.py 之类的东西，也不联网、不花钱。
"""

from __future__ import annotations

import os
import sys
import warnings
from datetime import datetime
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from hello_agents import Config, Message                            # noqa: E402
from hello_agents.core.agent import Agent                            # noqa: E402
from hello_agents.core.message import MessageRole                     # noqa: E402


class FakeLLM:
    """假的 LLM：Agent 只需要它有 .provider 属性。"""

    def __init__(self, provider="fake"):
        self.provider = provider

    def invoke(self, messages, **kwargs):
        return "（假 LLM 的回答）"

    def think(self, messages, **kwargs):
        yield "（假 LLM 的流式回答）"


class MiniAgent(Agent):
    """只实现 run 的最小 Agent，用来观察基类行为。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.invoke_count = 0

    def run(self, input_text: str, **kwargs) -> str:
        self.invoke_count += 1
        return f"[MiniAgent] {input_text}"


def show(number: int, question: str, func):
    print(f"\n[{number}] {question}")
    try:
        outcome = func()
    except Exception as exc:  # 异常本身也是"结果"
        print(f"    实际结果 -> 抛异常：{type(exc).__name__}: {str(exc).splitlines()[0][:160]}")
        return
    print(f"    实际结果 -> {outcome}")


# ============================ Message ============================

def q1():
    m = Message("你好", "user")
    return f"type={type(m).__name__}  str(m)={str(m)!r}  合法 role={MessageRole}"


def q2():
    m = Message("你好", "user")
    return f"to_dict()={m.to_dict()}"


def q3():
    m = Message("你好", "user")
    return f"timestamp={type(m.timestamp).__name__} metadata={m.metadata!r}"


def q4():
    return Message("你好", "robot")   # 非法 role；show() 会把异常当结果打出来


def q5():
    m1, m2 = Message("a", "user"), Message("b", "user")
    m1.metadata["k"] = "v"
    return f"m1.metadata={m1.metadata!r}  m2.metadata={m2.metadata!r}（默认值会不会共享？）"


def q6():
    m = Message("你好", "user")
    m.role = 123          # 故意塞个非法类型
    return f"赋值后 m.role={m.role!r}（pydantic 会拦住赋值吗？）"


def q7():
    m = Message("你好", "user", timestamp=datetime(2020, 1, 1), metadata={"src": "test"})
    return f"timestamp={m.timestamp} metadata={m.metadata} to_dict={m.to_dict()}"


# ============================ Config ============================

def q8():
    c = Config()
    return f"默认值={c.to_dict()}"


def q9():
    os.environ["TEMPERATURE"] = "0.1"
    os.environ["DEBUG"] = "true"
    os.environ["LOG_LEVEL"] = "WARNING"
    os.environ["LLM_MODEL_ID"] = "some-model-id"
    c = Config.from_env()
    for k in ("TEMPERATURE", "DEBUG", "LOG_LEVEL", "LLM_MODEL_ID"):
        os.environ.pop(k, None)
    return f"from_env() -> temperature={c.temperature} debug={c.debug} log_level={c.log_level!r} default_model={c.default_model!r}"


def q10():
    c = Config.from_env()
    c2 = Config.from_env()
    return f"两次 from_env() 是同一个对象吗？ {c is c2}"


def q11():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        Config().to_dict()
    kinds = sorted({w.category.__name__ for w in caught}) or ["（没有警告）"]
    return f"to_dict() 触发的警告：{kinds}"


# ============================ Agent ============================

def q12():
    return Agent(name="x", llm=FakeLLM())   # 抽象基类，应该实例化不了


def q13():
    a = MiniAgent(name="小助手", llm=FakeLLM("test-provider"), system_prompt="你是助手")
    return (f"name={a.name} provider={a.llm.provider} config类型={type(a.config).__name__} "
            f"str(a)={str(a)!r} system_prompt={a.system_prompt!r}")


def q14():
    a = MiniAgent(name="小助手", llm=FakeLLM())
    a.add_message(Message("hi", "user"))
    a.add_message(Message("hello", "assistant"))
    h1 = a.get_history()
    h1.append(Message("偷偷加的", "user"))          # 改返回的列表
    h1[0].content = "被我改了"                       # 改列表里的对象
    h2 = a.get_history()
    return (f"外部 append 后内部条数={len(h2)}（副本？）；"
            f"改内部对象后第一条={h2[0].content!r}（深拷贝还是浅拷贝？）")


def q15():
    a = MiniAgent(name="小助手", llm=FakeLLM())
    a.add_message(Message("hi", "user"))
    a.clear_history()
    return f"clear_history() 后 history={a.get_history()}  run()={a.run('测试')!r}"


EXPERIMENTS = [
    (1, "Message 长什么样？str() 会输出什么？", q1),
    (2, "Message.to_dict() 返回几个字段？timestamp/metadata 在里面吗？", q2),
    (3, "timestamp 和 metadata 不传时，默认值分别是什么？", q3),
    (4, "Message('你好', 'robot') —— role 传个非法值会怎样？", q4),
    (5, "两个 Message 实例的 metadata 会不会共享同一个 dict？", q5),
    (6, "创建之后 m.role = 123 这种乱赋值，pydantic 会拦住吗？", q6),
    (7, "显式传 timestamp/metadata 时，to_dict() 会把它们带出去吗？", q7),
    (8, "Config() 的默认值分别是什么？", q8),
    (9, "Config.from_env() 会读哪些环境变量？LLM_MODEL_ID 它管吗？", q9),
    (10, "Config 是单例吗？两次 from_env() 是同一个对象吗？", q10),
    (11, "Config.to_dict() 会触发什么警告？", q11),
    (12, "Agent(name='x', llm=假对象) 能直接实例化吗？", q12),
    (13, "子类只实现 run 就能用吗？str(agent) 里有什么？", q13),
    (14, "get_history() 返回的是副本还是内部列表？深拷贝还是浅拷贝？", q14),
    (15, "clear_history() 清干净了吗？清空后还能 run 吗？", q15),
]


def main() -> int:
    print("=" * 72)
    print("  第 7 章 · 关卡 2：Message / Config / Agent 预测-验证")
    print("=" * 72)
    print("  提醒：先把预测写进 note.md 再往下看，不然这一关就白做了 :)")
    print("=" * 72)

    for number, question, func in EXPERIMENTS:
        show(number, question, func)

    print("\n" + "=" * 72)
    print("  对答案")
    print("=" * 72)
    print("  把你的预测（一行一题）发我，我给你判分，并讲每一条背后的'为什么'。")
    print("  重点看这几条最容易错的：")
    print("    · 4/6  —— pydantic 到底在什么时候校验、什么时候不校验")
    print("    · 5    —— 可变默认值（Python 经典坑）在 pydantic 里还成立吗")
    print("    · 9/10 —— Config 到底管什么、是不是单例（习题 3 在这里埋了个坑）")
    print("    · 12   —— ABC + @abstractmethod 到底拦住了什么")
    print("    · 14   —— 副本 / 浅拷贝 / 深拷贝 的区别")
    print("\n  预测全中，就进 7.4：把第四章的三种范式搬进这套契约里（那才是动手大头）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
