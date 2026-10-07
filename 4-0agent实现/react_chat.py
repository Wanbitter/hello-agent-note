# 基于llm+react的一个混合案例是对ReAct_agent的一个rebuild

from llm_client import HelloAgentsLLM
from tools import search, calculator, ToolExecutor
from ReAct_agent import ReActAgent

llm = HelloAgentsLLM()

tool_executor = ToolExecutor()
tool_executor.registerTool(
    "Calculator",
    "一个数学计算器。输入必须是一个纯数学表达式，例如 (123+456)*789/12。",
    calculator,
)
tool_executor.registerTool(
    "Search",
    "一个网页搜索引擎。当需要回答时事、事实，或知识库里没有的信息时使用。",
    search,
)

agent = ReActAgent(llm, tool_executor, max_steps=8,Maxerrortime=4)

print("(输入quit,exit,q时，退出)")

while True:
    print("=" * 40)
    question = input("你: ").strip()  # 输入+去除前后空格
    if question.lower() in ("quit", "exit", "q"):  # 转小写识别退出
        break
    if not question:
        continue

    try:
        answer = agent.run(question)

    except Exception as e:
        print(f"智能体出错了：{type(e).__name__}: {e}")
        continue

    print("\n=== 最终答案 ===")
    print(answer or "（没给出答案）")


