from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()                                    # 从本文件所在目录往上找 .env

client = OpenAI(
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)

SYSTEM_PROMPT = "你是一个乐于助人的助手。"


def new_history() -> list:
    """开一份新的对话历史"""
    return [{"role": "system", "content": SYSTEM_PROMPT}]


def chat(user_msg: str, history: list | None = None) -> str:
    """发一句话，拿回 AI 的回答。
    history 不传就临时开一份（单次问答）。
    """
    if history is None:
        history = new_history()
    history.append({"role": "user", "content": user_msg})
    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=history,
    )
    ai_reply = response.choices[0].message.content
    history.append({"role": "assistant", "content": ai_reply})
    return ai_reply


def main():
    """终端聊天——只有【直接运行本文件】时才走这里"""
    print("输入 'quit' 退出聊天")
    history = new_history()
    while True:
        user_msg = input("你说：")
        if user_msg == 'quit':
            break
        print("AI：" + chat(user_msg, history))


if __name__ == "__main__":
    main()