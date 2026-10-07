# main.py
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# 【关键】从我们刚写的两个文件里导入东西
from config import SYSTEM_PROMPT, MODEL_NAME, BASE_URL
from tools import get_current_time

# ---- 1. 加载密钥 ----
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# ---- 2. 连接AI ----
client = OpenAI(
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url=BASE_URL   # 从这里读取，不再硬编码
)

# ---- 3. 启动对话（初始化笔记本） ----
# 注意这里用了从 config 导入的 SYSTEM_PROMPT
history: list = [{"role": "system", "content": SYSTEM_PROMPT}]

print("🤖 输入 'quit' 退出聊天")

# ---- 4. 主体循环 ----
while True:
    user_msg = input("👤 你说：")
    if user_msg == 'quit':
        break

    history.append({"role": "user", "content": user_msg})

    response = client.chat.completions.create(
        model=MODEL_NAME,      # 从这里读取
        messages=history
    )

    ai_reply = response.choices[0].message.content

    # ---- 5. 工具调用拦截（这里调用 tools.py 里的函数） ----
    if "[TIME]" in ai_reply:
        real_time =  get_current_time() # 调用工具
        ai_reply = ai_reply.replace("[TIME]", real_time)

    print("🤖 AI：" + ai_reply)

    # 记得把最终展示的内容存进历史，保证上下文一致
    history.append({"role": "assistant", "content": ai_reply})