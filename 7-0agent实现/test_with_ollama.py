# -*- coding: utf-8 -*-
"""验证"框架零改动接本地 Ollama"（不花钱、不用 API key）。

用法：
    F:\\Python_Project\\.venv\\Scripts\\python.exe test_with_ollama.py [模型名]
默认模型 qwen2.5:0.5b。

前提：Ollama 已安装并正在运行（任务栏有羊驼图标，或终端里 ollama serve 常驻）。
"""
import json
import os
import sys
import urllib.request

MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5:0.5b"
HOST = "http://127.0.0.1:11434"

# ---- 1) 服务在不在、本地有哪些模型 ----
try:
    with urllib.request.urlopen(f"{HOST}/api/tags", timeout=5) as r:
        tags = json.load(r)
    names = [m.get("name", "") for m in tags.get("models", [])]
    print("✅ Ollama 服务在跑。本地已有模型：", names or "（一个都没有）")
except Exception as exc:
    print(f"❌ 连不上 Ollama（{HOST}）：{type(exc).__name__}: {exc}")
    print("   先在一个终端里跑：ollama serve")
    print("   或者确认任务栏有 Ollama 图标（安装后它会自动常驻）")
    raise SystemExit(1)

base_name = MODEL.split(":")[0]
if MODEL not in names and not any(n.split(":")[0] == base_name for n in names):
    print(f"⚠️ 本地还没有 {MODEL}。先跑：ollama pull {MODEL}")
    print("   （不拉也行，直接跑这个脚本会看到 404 model not found，那也是有效信息）")

# ---- 2) 清掉云端凭据，确保这次真的走本地 ----
for key in ("LLM_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "MODELSCOPE_API_KEY",
            "ZHIPU_API_KEY", "GLM_API_KEY", "KIMI_API_KEY", "DASHSCOPE_API_KEY",
            "OLLAMA_API_KEY", "VLLM_API_KEY"):
    os.environ.pop(key, None)
os.environ["LLM_BASE_URL"] = f"{HOST}/v1"
os.environ["LLM_MODEL_ID"] = MODEL

from hello_agents import HelloAgentsLLM, SimpleAgent  # noqa: E402

llm = HelloAgentsLLM(provider="ollama", model=MODEL)
print(f"\n框架解析结果：provider={llm.provider} base_url={llm.base_url} model={llm.model}")
print("（注意：api_key 会自动填 'ollama'——本地服务不校验它）")

print("\n[1] 非流式 invoke():")
print("   ->", llm.invoke([{"role": "user", "content": "用一句话介绍你自己"}]))

print("\n[2] 流式 think()（think 内部会自己打印一遍）：")
text = "".join(llm.think([{"role": "user", "content": "数到三"}]))
print("   收集到:", repr(text))

print("\n[3] 走一遍框架的 SimpleAgent.run():")
agent = SimpleAgent(name="本地助手", llm=llm, system_prompt="你是一个简洁的助手")
answer = agent.run("你好，请介绍一下你自己")
print("   回答:", repr(answer), "| 历史条数:", len(agent.get_history()))

print("\n结论：同一套 Agent 代码，把 base_url 换成本地地址就能用 —— 这就是 7.2.2 的论点 ✅")
