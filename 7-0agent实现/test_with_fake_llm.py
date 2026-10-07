# -*- coding: utf-8 -*-
"""验证：openai SDK 3.x + hello_agents 0.1.1 这条链路是否还通（全走本地假服务，不花钱）。"""
import os

os.environ["LLM_API_KEY"] = "fake-key"
os.environ["LLM_BASE_URL"] = "http://127.0.0.1:8765/v1"
os.environ["LLM_MODEL_ID"] = "fake-model"
for k in ("OPENAI_API_KEY", "DEEPSEEK_API_KEY", "MODELSCOPE_API_KEY", "ZHIPU_API_KEY",
          "DASHSCOPE_API_KEY", "KIMI_API_KEY", "OLLAMA_API_KEY", "VLLM_API_KEY"):
    os.environ.pop(k, None)

import openai
import hello_agents
from hello_agents import HelloAgentsLLM, SimpleAgent

print("openai SDK 版本 :", openai.__version__)
print("hello_agents 版本:", hello_agents.__version__)

llm = HelloAgentsLLM()
print("解析结果        : provider=%s base_url=%s model=%s" % (llm.provider, llm.base_url, llm.model))

print("\n[1] 非流式 invoke():")
print("   ->", repr(llm.invoke([{"role": "user", "content": "hi"}])))

print("\n[2] 流式 think()（think 自己会打印一遍，这里只收集）:")
text = "".join(llm.think([{"role": "user", "content": "hi"}]))
print("   收集到:", repr(text))

print("\n[3] 走一遍框架的 SimpleAgent.run():")
agent = SimpleAgent(name="诊断助手", llm=llm, system_prompt="你是测试助手")
answer = agent.run("你好")
print("   回答:", repr(answer), "| 历史条数:", len(agent.get_history()))
print("\n结论：链路正常 ✅")
