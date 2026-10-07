#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 7 章 · 关卡 1 检查器：HelloAgentsLLM 的继承式扩展（my_llm.MyLLM）

它只做三件事：
  1. 确认你的 my_llm.py 里有一个「真的重写了东西」的 MyLLM 子类
  2. 用受控的环境变量，从外部观察它把 provider / api_key / base_url / model 解析成了什么
  3. 逐条对 SPEC.md 里关卡 1 的验收标准打分

不联网、不需要真 key：只构造客户端，不发任何请求。每次「构造」都可能真的创建一个
OpenAI 客户端对象，但 OpenAI SDK 在构造阶段不发起网络调用。

用法（在 7-0agent实现 目录下，与 my_llm.py 放在一起）：
    F:\\Python_Project\\.venv\\Scripts\\python.exe check_ch7_llm.py
    F:\\Python_Project\\.venv\\Scripts\\python.exe check_ch7_llm.py -v          # 打印每条的实际取值
    F:\\Python_Project\\.venv\\Scripts\\python.exe check_ch7_llm.py --only 4    # 只跑某几条

命名适配：默认 import my_llm.MyLLM，若你换了文件名/类名，只改下面两行即可。
"""

from __future__ import annotations

import argparse
import importlib
import os
import sys
import traceback
from contextlib import contextmanager
from pathlib import Path

# Windows 控制台默认可能是 GBK，先兜住编码，免得框架里的 emoji 把检查器搞崩
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

# ---- 想换文件名/类名，只改这几行 ----
MODULE_NAME, CLASS_NAME = "my_llm", "MyLLM"
BASE_MODULE, BASE_CLASS = "hello_agents", "HelloAgentsLLM"

# 自动检测会读到的环境变量：每个场景开始前一律清空，保证判定是确定的
ENV_KEYS = [
    "LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL_ID", "LLM_TIMEOUT",
    "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "MODELSCOPE_API_KEY",
    "KIMI_API_KEY", "MOONSHOT_API_KEY", "ZHIPU_API_KEY", "GLM_API_KEY",
    "OLLAMA_API_KEY", "OLLAMA_HOST", "VLLM_API_KEY", "VLLM_HOST",
    "SILICONFLOW_API_KEY",
]

MODELSCOPE_DEFAULT_BASE = "https://api-inference.modelscope.cn/v1"
OPENAI_DEFAULT_BASE = "https://api.openai.com/v1"
SILICONFLOW_DEFAULT_BASE = "https://api.siliconflow.cn/v1"


# =========================================================================
# 基础设施
# =========================================================================

class CheckFailure(Exception):
    """验收标准没达到（不是代码崩了）。"""


def expect(cond, msg):
    if not cond:
        raise CheckFailure(msg)


def norm(url) -> str:
    """base_url 结尾有没有斜杠不该算分歧。"""
    return str(url or "").rstrip("/")


@contextmanager
def env(**kv):
    """把环境变量切成一个干净的、只含指定键的世界，退出时还原。"""
    saved = {k: os.environ.get(k) for k in ENV_KEYS}
    for key in ENV_KEYS:
        os.environ.pop(key, None)
    for key, value in kv.items():
        os.environ[key] = str(value)
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def load_classes():
    if (HERE / "hello_agents").is_dir():
        raise CheckFailure(
            "这个目录下有 hello_agents/ 子目录，它会盖掉 pip 装的那份官方实现。"
            "路 B 不该出现它——请改名或挪走后再跑。"
        )
    try:
        base_mod = importlib.import_module(BASE_MODULE)
    except Exception as exc:
        raise CheckFailure(f"import hello_agents 失败（官方 0.1.1 没装好？）：{type(exc).__name__}: {exc}")
    base = getattr(base_mod, BASE_CLASS, None)
    expect(base is not None, f"hello_agents 里找不到 {BASE_CLASS}")

    try:
        mod = importlib.import_module(MODULE_NAME)
    except Exception as exc:
        raise CheckFailure(f"import {MODULE_NAME}.py 失败：{type(exc).__name__}: {exc}")
    cls = getattr(mod, CLASS_NAME, None)
    expect(cls is not None, f"{MODULE_NAME}.py 里找不到 {CLASS_NAME}")
    return base_mod, base, cls


def describe(inst) -> str:
    def show(name):
        return f"{name}={getattr(inst, name, '<缺失>')!r}"

    return " ".join(show(n) for n in ("provider", "model", "api_key", "base_url"))


# =========================================================================
# 必过项
# =========================================================================

def case_1_structure(ctx):
    """子类结构与"真的重写了"。"""
    base, cls = ctx["base"], ctx["cls"]
    expect(isinstance(cls, type), f"{CLASS_NAME} 必须是一个类")
    expect(issubclass(cls, base), f"{CLASS_NAME} 必须是 {BASE_CLASS} 的子类（路 B 要求用继承扩展）")
    expect(cls is not base, f"{CLASS_NAME} 不能就是 {BASE_CLASS} 本身")
    overridden = [
        name for name in ("__init__", "_auto_detect_provider", "_resolve_credentials",
                          "_create_client", "_get_default_model")
        if getattr(cls, name, None) is not getattr(base, name, None)
    ]
    expect(overridden,
           "MyLLM 什么都没重写（'class MyLLM(HelloAgentsLLM): pass' 不算扩展）；"
           "至少要重写 __init__ / _auto_detect_provider / _resolve_credentials 之一")
    return f"重写了：{', '.join(overridden)}"


def case_2_modelscope_basic(ctx):
    """provider='modelscope' + MODELSCOPE_API_KEY。"""
    cls = ctx["cls"]
    with env(MODELSCOPE_API_KEY="ms-env-key", LLM_MODEL_ID="env-model"):
        inst = cls(provider="modelscope")
        expect(getattr(inst, "provider", None) == "modelscope",
               f"provider 应该是 'modelscope'，实际是 {getattr(inst, 'provider', None)!r}")
        expect(inst.api_key == "ms-env-key",
               f"api_key 应该取 MODELSCOPE_API_KEY，实际是 {inst.api_key!r}")
        expect(norm(inst.base_url) == MODELSCOPE_DEFAULT_BASE,
               f"base_url 应该是 {MODELSCOPE_DEFAULT_BASE}，实际是 {inst.base_url!r}")
        expect(inst.model == "env-model",
               f"model 应该取 LLM_MODEL_ID，实际是 {inst.model!r}")
        expect(abs(float(getattr(inst, "temperature", -1)) - 0.7) < 1e-9,
               f"temperature 默认应该是 0.7，实际是 {getattr(inst, 'temperature', None)!r}")
        expect(getattr(inst, "_client", None) is not None,
               "对象上没有可用的 _client（OpenAI 客户端实例）")
        return describe(inst)


def case_3_explicit_wins(ctx):
    """显式参数优先于环境变量。"""
    cls = ctx["cls"]
    with env(MODELSCOPE_API_KEY="ms-env-key", LLM_MODEL_ID="env-model", LLM_API_KEY="llm-env-key"):
        inst = cls(
            provider="modelscope",
            api_key="ms-explicit-key",
            base_url="https://example.com/v1",
            model="explicit-model",
            temperature=0.2,
            max_tokens=123,
        )
        expect(inst.api_key == "ms-explicit-key", f"显式 api_key 没生效，实际 {inst.api_key!r}")
        expect(norm(inst.base_url) == "https://example.com/v1", f"显式 base_url 没生效，实际 {inst.base_url!r}")
        expect(inst.model == "explicit-model", f"显式 model 没生效，实际 {inst.model!r}")
        expect(abs(float(inst.temperature) - 0.2) < 1e-9, f"显式 temperature 没生效，实际 {inst.temperature!r}")
        expect(inst.max_tokens == 123, f"显式 max_tokens 没生效，实际 {inst.max_tokens!r}")
        return describe(inst)


def case_4_missing_key(ctx):
    """没有任何 modelscope 凭据时必须失败。"""
    cls = ctx["cls"]
    with env():
        try:
            inst = cls(provider="modelscope")
        except Exception as exc:
            msg = str(exc)
            low = msg.lower()
            expect(("key" in low) or ("密钥" in msg) or ("凭据" in msg) or ("api key" in low),
                   f"确实失败了，但报错信息看不出是缺 key：{type(exc).__name__}: {msg}")
            return f"按预期失败：{type(exc).__name__}: {msg}"
        raise CheckFailure(
            "没有 MODELSCOPE_API_KEY 也没有 api_key，构造却成功了"
            f"（{describe(inst)}）——空凭据不该被放行"
        )


def case_5_parent_env(ctx):
    """不传 provider 时，父类那套 LLM_* 环境变量解析照旧生效。"""
    cls = ctx["cls"]
    with env(LLM_API_KEY="sk-llm-env-key", LLM_BASE_URL="https://api.deepseek.com",
             LLM_MODEL_ID="deepseek-flash"):
        inst = cls()
        provider = getattr(inst, "provider", None)
        expect(provider in ("deepseek", "auto"),
               f"provider 应该是 'deepseek'（自动检测）或 'auto'（把 auto 交给了父类兜底），实际 {provider!r}")
        expect(inst.api_key == "sk-llm-env-key", f"api_key 应该取 LLM_API_KEY，实际 {inst.api_key!r}")
        expect(norm(inst.base_url) == "https://api.deepseek.com", f"base_url 应该取 LLM_BASE_URL，实际 {inst.base_url!r}")
        expect(inst.model == "deepseek-flash", f"model 应该取 LLM_MODEL_ID，实际 {inst.model!r}")
        return describe(inst)


def case_6_openai_passthrough(ctx):
    """非 modelscope 的 provider 必须原样交回父类。"""
    cls = ctx["cls"]
    with env(OPENAI_API_KEY="sk-openai-test-key"):
        inst = cls(provider="openai")
        expect(inst.provider == "openai", f"provider 应该是 'openai'，实际 {inst.provider!r}")
        expect(inst.api_key == "sk-openai-test-key", f"api_key 应该取 OPENAI_API_KEY，实际 {inst.api_key!r}")
        expect(norm(inst.base_url) == OPENAI_DEFAULT_BASE,
               f"base_url 应该是父类的默认值 {OPENAI_DEFAULT_BASE}，实际 {inst.base_url!r}")
        return describe(inst)


def case_7_framework_interop(ctx):
    """实例能被框架的 Agent 直接用（接口没被破坏）。"""
    base_mod, cls = ctx["base_mod"], ctx["cls"]
    SimpleAgent = getattr(base_mod, "SimpleAgent", None)
    expect(SimpleAgent is not None, "hello_agents 里找不到 SimpleAgent")

    with env(MODELSCOPE_API_KEY="ms-env-key", LLM_MODEL_ID="env-model"):
        inst = cls(provider="modelscope")
        expect(callable(getattr(inst, "think", None)), "think() 不见了（被继承或被覆盖坏了）")
        expect(callable(getattr(inst, "invoke", None)), "invoke() 不见了（被继承或被覆盖坏了）")

        agent = SimpleAgent(name="关卡1自检", llm=inst, system_prompt="你是检查器的假助手")
        expect(agent.llm is inst, "Agent 没有拿到你的 LLM 实例")

        # 把 invoke 换成一个假的，验证"接口是真的能跑通"，而不是只会构造
        inst.invoke = lambda messages, **kwargs: "pong"
        answer = agent.run("ping")
        expect(answer == "pong", f"Agent.run 没能用上你的 LLM（返回 {answer!r}）")
        expect(len(agent.get_history()) == 2, f"历史应该有 2 条，实际 {len(agent.get_history())}")
        return "SimpleAgent(MyLLM) → run('ping') == 'pong'，历史 2 条"


# =========================================================================
# 加分项
# =========================================================================

def case_8_siliconflow_explicit(ctx):
    """加分：显式 provider='siliconflow'。"""
    cls = ctx["cls"]
    with env():
        inst = cls(provider="siliconflow", api_key="sk-sf-test", model="sf-model")
        expect(inst.provider == "siliconflow", f"provider 应该是 'siliconflow'，实际 {inst.provider!r}")
        expect(inst.api_key == "sk-sf-test", f"api_key 没生效，实际 {inst.api_key!r}")
        expect(norm(inst.base_url) == SILICONFLOW_DEFAULT_BASE,
               f"base_url 应该是 {SILICONFLOW_DEFAULT_BASE}，实际 {inst.base_url!r}")
        expect(inst.model == "sf-model", f"model 没生效，实际 {inst.model!r}")
        return describe(inst)


def case_9_siliconflow_autodetect(ctx):
    """加分：只设 SILICONFLOW_API_KEY，不传 provider，也能自动检测出来。"""
    cls = ctx["cls"]
    with env(SILICONFLOW_API_KEY="sk-sf-env-key", LLM_MODEL_ID="sf-env-model"):
        inst = cls()
        expect(inst.provider == "siliconflow",
               f"provider 应该被自动检测成 'siliconflow'，实际 {inst.provider!r}"
               "（提示：父类里是 provider or _auto_detect_provider(...)，而字符串 'auto' 是真值）")
        expect(inst.api_key == "sk-sf-env-key", f"api_key 应该取 SILICONFLOW_API_KEY，实际 {inst.api_key!r}")
        expect(norm(inst.base_url) == SILICONFLOW_DEFAULT_BASE,
               f"base_url 应该是 {SILICONFLOW_DEFAULT_BASE}，实际 {inst.base_url!r}")
        return describe(inst)


REQUIRED = [
    (1, "子类是 HelloAgentsLLM 的真子类，且真的重写了东西", case_1_structure),
    (2, "modelscope：环境变量里的 key 能撑起整个配置", case_2_modelscope_basic),
    (3, "modelscope：显式参数优先于环境变量", case_3_explicit_wins),
    (4, "modelscope：没有凭据时必须失败", case_4_missing_key),
    (5, "不传 provider：父类的 LLM_* 环境变量解析照旧生效", case_5_parent_env),
    (6, "provider='openai'：原样交回父类", case_6_openai_passthrough),
    (7, "你的 LLM 能被框架的 SimpleAgent 直接用", case_7_framework_interop),
]

BONUS = [
    (8, "加分：显式 provider='siliconflow'", case_8_siliconflow_explicit),
    (9, "加分：SILICONFLOW_API_KEY 能被自动检测", case_9_siliconflow_autodetect),
]


# =========================================================================
# 跑起来
# =========================================================================

def run_one(number, title, fn, ctx, verbose):
    try:
        detail = fn(ctx)
    except CheckFailure as exc:
        print(f"  ❌ [{number}] {title}\n        {exc}")
        return False
    except Exception as exc:
        print(f"  💥 [{number}] {title}\n        {type(exc).__name__}: {exc}")
        if verbose:
            traceback.print_exc()
        return False
    print(f"  ✅ [{number}] {title}")
    if verbose and detail:
        print(f"        {detail}")
    return True


def main():
    parser = argparse.ArgumentParser(description="第 7 章 · 关卡 1 检查器（MyLLM）")
    parser.add_argument("-v", "--verbose", action="store_true", help="通过时也打印实际取值")
    parser.add_argument("--only", default="", help="只跑指定编号，例如 --only 3,4,9")
    args = parser.parse_args()

    print(f"检查目录：{HERE}")
    try:
        base_mod, base, cls = load_classes()
    except CheckFailure as exc:
        print(f"\n结构检查没通过：\n  ❌ {exc}")
        print("\n先按 SPEC.md 的关卡 1 契约把 my_llm.py 写出来，再回来跑。")
        return 1
    print(f"结构检查：my_llm.{CLASS_NAME} 与 hello_agents.{BASE_CLASS} 都在 ✅")
    print(f"  （参考实现版本：{getattr(base_mod, '__version__', '?')}）")

    selected = {int(x) for x in args.only.replace("，", ",").split(",") if x.strip().isdigit()}
    ctx = {"base_mod": base_mod, "base": base, "cls": cls}

    print("\n--- 必过项 ---")
    required_pass = 0
    for number, title, fn in REQUIRED:
        if selected and number not in selected:
            continue
        required_pass += 1 if run_one(number, title, fn, ctx, args.verbose) else 0
    print("\n--- 加分项 ---")
    bonus_pass = 0
    for number, title, fn in BONUS:
        if selected and number not in selected:
            continue
        bonus_pass += 1 if run_one(number, title, fn, ctx, args.verbose) else 0

    total_required = len([1 for n, _, _ in REQUIRED if not selected or n in selected])
    total_bonus = len([1 for n, _, _ in BONUS if not selected or n in selected])
    print(f"\n必过项 {required_pass}/{total_required} · 加分项 {bonus_pass}/{total_bonus}")

    if required_pass < total_required:
        print("\n卡住了就说一声，按『方向提示 → 骨架 → 代码』三级给，默认只给第一级。")
        return 1

    print("\n🎉 必过项全绿。")
    if bonus_pass < total_bonus:
        print("加分项还没拿满：", "、".join(f"[{n}] {t}" for n, t, _ in BONUS if not selected or n in selected))
        print("提示见 SPEC.md 第四节（父类把 provider 判断与凭据解析拆成了两个钩子，且都是在 __init__ 里用 self. 调的）。")
    print("\n下一步：")
    print("  1) 写 my_main.py，用 MyLLM(provider='modelscope') 流式打印一条消息（要真 key，你自己决定何时跑）")
    print("  2) 回 PDF 7.2.1 对照书里的 MyLLM，做一次差异复盘（参数校验时机 / 默认值来源）")
    print("  3) 复盘完喊我，开始关卡 2（7.3 读穿三件套）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
