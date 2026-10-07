# -*- coding: utf-8 -*-
"""Ollama 本地模型聊天客户端（纯本地、不花钱、不走任何云端 API）

用法：
    双击桌面「Ollama 聊天」；或在终端里:
        F:\\Python_Project\\.venv\\Scripts\\python.exe chat_ollama.py [模型名]
        F:\\Python_Project\\.venv\\Scripts\\python.exe chat_ollama.py --once "你好"

对话中的命令：
    /bye         退出
    /clear       清空上下文（重新开始）
    /models      列出本地模型
    /model 名字   换一个模型继续聊
    /system 文本  换系统提示词

为什么用 Python 而不是直接 ollama run：
    Windows 控制台默认是 GBK，ollama 输出的 UTF-8 中文会乱码，而 .cmd 文件里的中文路径
    又会被 GBK 解析成乱码命令（你之前看到的报错就是这个原因）。
    Python 在 Windows 上走 Unicode 控制台 API，中文输入输出不用管代码页。
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

# 兜底：万一输出被重定向到不认识 Unicode 的地方，宁可显示 ? 也不要崩
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except Exception:
        pass

HOST = "http://127.0.0.1:11434"
DEFAULT_SYSTEM = "你是一个乐于助人的中文助手，回答尽量简洁。"
DEFAULT_MODEL = "qwen2.5:0.5b"


# ----------------------------- HTTP -----------------------------

def http_get(path: str):
    with urllib.request.urlopen(f"{HOST}{path}", timeout=10) as resp:
        return json.load(resp)


def list_models() -> list[str]:
    try:
        data = http_get("/api/tags")
    except Exception as exc:
        print(f"\n[错误] 连不上 Ollama 服务（{HOST}）：{type(exc).__name__}: {exc}")
        print("       解决办法：双击桌面「Ollama 托盘程序」，或在终端里跑 ollama serve")
        raise SystemExit(1)
    return [m.get("name", "") for m in data.get("models", [])]


def stream_chat(model: str, messages: list[dict]):
    """向本地服务的 OpenAI 兼容接口发请求，逐段 yield 文本。"""
    payload = json.dumps({"model": model, "messages": messages, "stream": True}).encode("utf-8")
    req = urllib.request.Request(
        f"{HOST}/v1/chat/completions", data=payload,
        headers={"Content-Type": "application/json", "Authorization": "Bearer ollama"},
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            for raw in resp:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                body = line[5:].strip()
                if body == "[DONE]":
                    break
                try:
                    chunk = json.loads(body)
                except json.JSONDecodeError:
                    continue
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                piece = delta.get("content") or ""
                if piece:
                    yield piece
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        print(f"\n[错误] 服务返回 {exc.code}：{detail}")
        if "not found" in detail.lower():
            print(f"       本地好像没有 {model} 这个模型，先跑：ollama pull {model}")
        return
    except Exception as exc:
        print(f"\n[错误] 请求失败：{type(exc).__name__}: {exc}")
        return


# ----------------------------- 交互 -----------------------------

def ask_once(model: str, system: str, question: str, history: list[dict]) -> None:
    history.append({"role": "user", "content": question})
    messages = [{"role": "system", "content": system}] + history
    print("模型 > ", end="", flush=True)
    t0, pieces = time.time(), []
    for piece in stream_chat(model, messages):
        pieces.append(piece)
        print(piece, end="", flush=True)
    cost = time.time() - t0
    print()
    text = "".join(pieces)
    if text:
        history.append({"role": "assistant", "content": text})
        print(f"       [ {len(text)} 字 / {cost:.1f} 秒 / {len(text) / max(cost, 0.01):.1f} 字每秒 ]")


def main() -> int:
    argv = sys.argv[1:]
    once = None
    if "--once" in argv:
        i = argv.index("--once")
        once = argv[i + 1] if i + 1 < len(argv) else "你好"
        argv = argv[:i] + argv[i + 2:]

    models = list_models()
    model = argv[0] if argv else (models[0] if models else DEFAULT_MODEL)
    if models and model not in models:
        print(f"[提示] 本地没有 {model}，已有的：{', '.join(models)}")
    system = DEFAULT_SYSTEM
    history: list[dict] = []

    if once is not None:
        print(f"模型：{model}")
        ask_once(model, system, once, history)
        return 0

    print("=" * 56)
    print("  Ollama 本地聊天   （纯本地，不花钱）")
    print("=" * 56)
    print(f"本地模型：{', '.join(models) if models else '（一个都没有，先 ollama pull ...）'}")
    print(f"当前模型：{model}")
    print("命令：/bye 退出   /clear 清空上下文   /models 列模型   /model 名字 换模型   /system 文本 换系统提示")
    print("-" * 56)

    while True:
        try:
            question = input("\n你：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见")
            return 0

        if not question:
            continue
        if question in ("/bye", "/exit", "/quit"):
            print("再见")
            return 0
        if question == "/clear":
            history.clear()
            print("[已清空上下文]")
            continue
        if question == "/models":
            print("本地模型：", ", ".join(list_models()) or "（无）")
            continue
        if question.startswith("/model "):
            model = question.split(" ", 1)[1].strip()
            print(f"[已切换到 {model}]（上下文保留，/clear 可清空）")
            continue
        if question.startswith("/system "):
            system = question.split(" ", 1)[1].strip()
            print("[系统提示词已更新]")
            continue

        ask_once(model, system, question, history)


if __name__ == "__main__":
    sys.exit(main())
