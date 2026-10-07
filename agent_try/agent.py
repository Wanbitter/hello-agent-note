# sk-nk8td7lIi9vFVqg175Bd021513C645Df897a5049C06489D6
import os
import re
import requests
from tavily import TavilyClient
from openai import OpenAI


API_KEY = "sk-fce29003075e4a3284527a7e38fb32d7"
BASE_URL = "https://api.deepseek.com"
MODEL_ID = "deepseek-v4-flash"
# Tavily API Key（也可以设置为环境变量，这里直接赋值方便测试）
TAVILY_API_KEY = "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"
os.environ['TAVILY_API_KEY'] = TAVILY_API_KEY  # 让 get_attraction 能读到

# ---------- 1. 系统提示词 ----------
AGENT_SYSTEM_PROMPT = """
你是一个智能旅行助手。你的任务是分析用户的请求，并使用可用工具一步步地解决问题。

# 可用工具:
- `get_weather(city: str)`: 查询指定城市的实时天气。
- `get_attraction(city: str, weather: str)`: 根据城市和天气搜索推荐的旅游景点。

# 输出格式要求:
你的每次回复必须严格遵循以下格式，包含一对Thought和Action：

Thought: [你的思考过程和下一步计划]
Action: [你要执行的具体行动]

Action的格式必须是以下之一：
1. 调用工具：function_name(arg_name="arg_value")
2. 结束任务：Finish[最终答案]

# 重要提示:
- 每次只输出一对Thought-Action
- Action必须在同一行，不要换行
- 当收集到足够信息可以回答用户问题时，必须使用 Action: Finish[最终答案] 格式结束

请开始吧！
"""


# ---------- 2. 工具函数 ----------
def get_weather(city: str) -> str:
    """通过 wttr.in 查询天气"""
    url = f"https://wttr.in/{city}?format=j1"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        current = data['current_condition'][0]
        weather_desc = current['weatherDesc'][0]['value']
        temp_c = current['temp_C']
        return f"{city}当前天气:{weather_desc}，气温{temp_c}摄氏度"
    except Exception as e:
        return f"错误:查询天气失败 - {e}"


def get_attraction(city: str, weather: str) -> str:
    """使用 Tavily 搜索景点"""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "错误:未配置TAVILY_API_KEY环境变量。"
    tavily = TavilyClient(api_key=api_key)
    query = f"'{city}' 在'{weather}'天气下最值得去的旅游景点推荐及理由"
    try:
        response = tavily.search(query=query, search_depth="basic", include_answer=True)
        if response.get("answer"):
            return response["answer"]
        results = [f"- {r['title']}: {r['content']}" for r in response.get("results", [])]
        return "根据搜索，为您找到以下信息:\n" + "\n".join(results) if results else "抱歉，没有找到相关景点。"
    except Exception as e:
        return f"错误:执行Tavily搜索失败 - {e}"


available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
}


# ---------- 3. LLM 客户端封装（兼容 OpenAI 接口） ----------
class OpenAICompatibleClient:
    def __init__(self, model: str, api_key: str, base_url: str = None):
        self.model = model
        # 如果 base_url 为 None，则使用 OpenAI 默认地址
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, prompt: str, system_prompt: str) -> str:
        print("正在调用大语言模型...")
        try:
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt}
            ]
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False
            )
            answer = response.choices[0].message.content
            print("大语言模型响应成功。")
            return answer
        except Exception as e:
            print(f"调用LLM API时发生错误: {e}")
            return "错误:调用语言模型服务时出错。"

# 实例化 LLM 客户端
llm = OpenAICompatibleClient(
    model=MODEL_ID,
    api_key=API_KEY,
    base_url=BASE_URL
)

# ---------- 5. 执行主循环 ----------
space = input("输入查询地点")
user_prompt = "你好，请帮我查询一下今天" + space +"的天气，然后根据天气推荐一个合适的旅游景点。"
prompt_history = [f"用户请求: {user_prompt}"]

print(f"用户输入: {user_prompt}\n" + "=" * 40)

for i in range(1):  # 最大循环5次
    print(f"--- 循环 {i + 1} ---\n")

    # 5.1 构建完整 prompt
    full_prompt = "\n".join(prompt_history)

    # 5.2 调用 LLM
    llm_output = llm.generate(full_prompt, system_prompt=AGENT_SYSTEM_PROMPT)

    # 截断多余的 Thought-Action（防止模型输出多对）
    match = re.search(r'(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)', llm_output, re.DOTALL)
    if match:
        truncated = match.group(1).strip()
        if truncated != llm_output.strip():
            llm_output = truncated
            print("已截断多余的 Thought-Action 对")
    print(f"模型输出:\n{llm_output}\n")
    prompt_history.append(llm_output)

    # 5.3 解析 Action
    action_match = re.search(r"Action: (.*)", llm_output, re.DOTALL)
    if not action_match:
        observation = "错误: 未能解析到 Action 字段。请确保你的回复严格遵循 'Thought: ... Action: ...' 的格式。"
        observation_str = f"Observation: {observation}"
        print(f"{observation_str}\n" + "=" * 40)
        prompt_history.append(observation_str)
        continue

    action_str = action_match.group(1).strip()

    # 如果是 Finish，结束
    if action_str.startswith("Finish"):
        final_answer = re.match(r"Finish\[(.*)\]", action_str).group(1)
        print(f"任务完成，最终答案: {final_answer}")
        break

    # 解析工具名称和参数
    tool_name = re.search(r"(\w+)\(", action_str).group(1)
    args_str = re.search(r"\((.*)\)", action_str).group(1)
    kwargs = dict(re.findall(r'(\w+)="([^"]*)"', args_str))

    # 执行工具
    if tool_name in available_tools:
        observation = available_tools[tool_name](**kwargs)
    else:
        observation = f"错误:未定义的工具 '{tool_name}'"

    # 记录观察结果
    observation_str = f"Observation: {observation}"
    print(f"{observation_str}\n" + "=" * 40)
    prompt_history.append(observation_str)