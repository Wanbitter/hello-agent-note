import re
from llm_client import HelloAgentsLLM
from tools import ToolExecutor, search,calculator
from ReActagentconfig import REACT_PROMPT_TEMPLATE



class ReActAgent:
    def __init__(self, llm_client: HelloAgentsLLM, tool_executor: ToolExecutor, max_steps: int = 8 ,Maxerrortime: int = 4):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.history = []
        self.Maxerrortime = Maxerrortime

    def run(self, question: str):
        """
        运行ReAct智能体来回答一个问题。
        """
        self.history = []  # 每次运行时重置历史记录
        current_step = 0
        errortime = 0

        while current_step < self.max_steps:
            current_step += 1
            print(f"--- 第 {current_step} 步 ---")
            if errortime >= self.Maxerrortime:
                return "工具调用错误次数较多"


            # 1. 格式化提示词
            tools_desc = self.tool_executor.getAvailableTools()
            history_str = "\n".join(self.history)
            prompt = REACT_PROMPT_TEMPLATE.format(
                tools=tools_desc,
                question=question,
                history=history_str
            )

            # 2. 调用LLM进行思考
            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(messages = messages)

            if not response_text:
                print("错误:LLM未能返回有效响应。")
                break

            thought, action  = self._parse_output(response_text)

            if thought:
                print(f"思考: {thought}")

            if not action:
                print("警告:未能解析出有效的Action，流程终止。")
                break

            if action.startswith("Finish"):
                # 如果是Finish指令，提取最终答案并结束
                m = re.match(r"Finish\[(.*)\]", action, re.DOTALL)
                if m :
                    final_answer = m.group(1)
                    print(f"🎉 最终答案: {final_answer}")
                    return final_answer
                self.history.append(f"Action: {action}")
                self.history.append("Observation: 错误: Finish 格式非法，应为 Finish[最终答案]。")
                continue

            tool_name, tool_input = self._parse_action(action)
            # 空输入是合法的（有些工具不需要参数），所以不能拿 tool_input 判空。
            # 只有切不出工具名才算格式错误；格式错误也必须写回 history，
            # 否则模型不知道自己错了，会一直重复同一个错误直到步数耗尽。
            #在此处加入                ← 这种过程性的话，改完就删掉
            if tool_name is None:  # ← 只有"压根没切出工具名"才算格式错误
                self.history.append(f"Action: {action}")
                self.history.append("Observation: 错误: Action 格式非法，应为 工具名[输入] 或 Finish[答案]。")
                continue
            #上面的是为了放置调用tool_input的时候是空字符串导致的空跑
            #因此，下面的就被注释掉了
            # if not tool_name or not tool_input:
            #     # ... 处理无效Action格式 ...
            #     continue
            print(f"🎬 行动: {tool_name}[{tool_input}]")

            tool_function = self.tool_executor.getTool(tool_name)
            if not tool_function:
                observation = f"错误:未找到名为 '{tool_name}' 的工具。"
            else :
                #本来只有observation = tool_function(tool_input)普通的工具调用，但是，ai让我加了异常
                try:
                    observation = tool_function(tool_input)
                except Exception as e:
                    observation = f"错误: 工具 '{tool_name}' 执行失败: {e}, 检查工具输入的正确性"

            if str(observation).startswith("错误"):
                errortime += 1
                if errortime == self.Maxerrortime - 2:
                    observation += "\n调用失败次数过多，尝试更换工具或者输出格式"
            else:
                errortime = 0


            print(f"👀 观察: {observation}")

            self.history.append(f"Action: {action}")
            self.history.append(f"Observation: {observation}")



        print("已达到最大步数，流程终止。")
        return None


    def _parse_output(self, text: str):
        """解析LLM的输出，提取Thought和Action。
        """
        # Thought: 匹配到 Action: 或文本末尾
        thought_match = re.search(r"Thought[：:]\s*(.*?)(?=\nAction[：:]|$)", text, re.DOTALL | re.IGNORECASE)
        # Action: 匹配到文本末尾
        action_match = re.search(r"Action[：:]\s*(.*?)$", text, re.DOTALL | re.IGNORECASE)
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        return thought, action

    def _parse_action(self, action_text: str):
        """解析Action字符串，提取工具名称和输入。
        """
        text = action_text.strip()
        text = text.replace("【","[").replace("】","]")
        text = text.strip("`*_ \t")
        match = re.search(r"(\w+)\[(.*)\]", text, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        return None, None

if __name__ == "__main__":
    llm_client = HelloAgentsLLM()     # 真模型
    tool_executor = ToolExecutor()
    tool_executor.registerTool(
        "Calculator",
        "一个计算工具，当发现有数学式子的时候计算,返回结果",
        calculator
    )
    tool_executor.registerTool(
         "Search",
         "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。",
         search
    )

    agent = ReActAgent(llm_client, tool_executor, max_steps=7)
    answer = agent.run("现在的电脑屏幕最好的是那些？从刷新率，价格方面给我答案，要求性价比高")
    print("\n=== 最终答案 ===")
    print(answer)


# if __name__ == "__main__":
#     from tools import search
#
#     llm_client = HelloAgentsLLM()
#     tool_executor = ToolExecutor()
#     tool_executor.registerTool("Search", "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。", search)
#     agent = ReActAgent(llm_client, tool_executor, max_steps=5)
#
#     print("输入 quit 退出")
#     while True:
#         try:
#             question = input("\n👤 你问：").strip()
#         except (EOFError, KeyboardInterrupt):     # Ctrl+C / Ctrl+D
#             print("\n再见")
#             break
#         if question in ("quit", "exit", "q"):
#             break
#         if not question:
#             continue
#         try:
#             answer = agent.run(question)
#         except Exception as e:                     # 兜住 run() 里没兜住的意外
#             print(f"❌ 智能体炸了：{type(e).__name__}: {e}")
#             continue
#         print("\n=== 最终答案 ===")
#         print(answer or "（没给出答案）")