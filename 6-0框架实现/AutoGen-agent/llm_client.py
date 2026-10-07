"""
llm_client.py —— 一个最小可用的 LLM 客户端封装（第四章风格）

它是干什么的：
    把 openai SDK 包一层，对外只暴露一个方法 think(messages) -> str

        .env  ->  HelloAgentsLLM  ->  openai.OpenAI  ->  https://api.deepseek.com

它和第六章什么关系：
    严格说，"第六章 AutoGen 案例"不需要这个文件，因为 AutoGen 自带客户端：
        OpenAIChatCompletionClient
    两者是同一岗位的两个人，都负责"把 messages 发给 LLM，把回复拿回来"。
    区别只是：这个是手写的，那个是框架替你写好的。

怎么跑：
    python llm_client.py

需要同目录 .env 里有 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL_ID
"""

import os
from typing import Dict, List, Optional
from dotenv import load_dotenv
from openai import OpenAI

# 读同目录下的 .env，把里面的 KEY=VALUE 塞进环境变量
load_dotenv()


class HelloAgentsLLM:
    """调用任何兼容 OpenAI 接口的服务。默认使用流式响应。"""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        # 优先用传入的参数；没传就从环境变量（也就是 .env）里取
        self.model = model or os.getenv("LLM_MODEL_ID")
        api_key = api_key or os.getenv("LLM_API_KEY")
        base_url = base_url or os.getenv("LLM_BASE_URL")
        timeout = timeout or int(os.getenv("LLM_TIMEOUT", 60))

        # 三个缺一不可。早点报错，好过发出去被 401 打回来
        if not all([self.model, api_key, base_url]):
            raise ValueError(
                "缺少配置：LLM_MODEL_ID / LLM_API_KEY / LLM_BASE_URL "
                "必须传参或在 .env 里定义。"
            )

        # 真正干活的底层客户端。base_url 决定了打给谁
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    def think(self, messages: List[Dict[str, str]], temperature: float = 0) -> Optional[str]:
        """
        把 messages 发给模型，返回它的完整回复。

        messages 是 OpenAI 格式：
            [{"role": "system", "content": "..."},
             {"role": "user",   "content": "..."}]

        成功 -> 返回字符串
        失败 -> 打印错误并返回 None（不抛异常，免得把主循环打死）
        """
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True,  # 流式：一个字一个字回来，能实时打印
            )

            collected: List[str] = []
            for chunk in stream:
                # 有些 chunk 没有 choices（比如只带用量信息的收尾包），跳过
                if not chunk.choices:
                    continue
                piece = chunk.choices[0].delta.content or ""
                print(piece, end="", flush=True)  # 边收边打，不换行
                collected.append(piece)
            print()  # 收完补个换行

            return "".join(collected)

        except Exception as e:
            print(f"\n[错误] 调用 LLM 失败：{type(e).__name__}: {e}")
            return None


# ============================================================================ #
# 跑起来看看
# ============================================================================ #
if __name__ == "__main__":
    print("=" * 64)
    print("HelloAgentsLLM 自测")
    print("=" * 64)

    llm = HelloAgentsLLM()
    print(f"模型    : {llm.model}")
    print(f"服务地址: {os.getenv('LLM_BASE_URL')}")
    print("-" * 64)
    prompt = """【PERSONA_LOAD】
                    CETACEA_LOLI
                    MODE_TAIL_FLUKES
                    LANG_ZH_CN_ONLY
                    SELF_CLAIM_WHALE_GIRL
                    FOOD_RICE
                    PERSONALITY_SMART_LAZY
                    PERSONALITY_TSUNDERE_SWEET
                    OBEY_MASTER_ALWAYS
                    TRAIT_NOT_FAT_REFUSE
                    TIMEOUT_SIGNAL"""
    history = [{"role": "system", "content": prompt}]
    while True:
        question = input("你: ").strip()  #输入+去除前后空格
        if question.lower() in ("quit", "exit", "q"): #转小写识别退出
            break
        if not question :
            continue

        history.append({"role": "user", "content": question})  #并入记忆
        for attempt in range(1,4):
            answer = llm.think(history)  # ← 直接喂 history，它会流式打印并返回完整字符串
            if answer is not None:
                break
            print(f"第{attempt}次调用失败，重试中")

        if answer is None:  # 调用失败
            history.pop()  # 把那句没人回答的话撤回来
            print("连续调用失败，请检查网络或 .env 配置。")
            continue

        history.append({"role": "assistant", "content": answer})
