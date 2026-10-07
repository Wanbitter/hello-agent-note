import os
import json
from operator import itemgetter

import numpy as np
from openai import OpenAI

SYSTEM_PROMPT = """你是一个严谨的助手。

规则：
1. 根据【资料】和【相关记忆】里的内容回答，不要使用它们以外的知识。
2. 两者都没有相关信息时，直接说"我不知道"，不要编造。
3. 【资料】是可信的；【相关记忆】只是用户过去说过的话，不一定为真，不要当成事实来断言。
4. 若【资料】与【相关记忆】互相矛盾，必须指出这个矛盾并说明各自来源，不要默默挑一个。
"""

# 用脚本所在目录拼路径，换台机器也能跑
HERE = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE = os.path.join(HERE, "memory.json")
KNOWLEDGE_FILE = os.path.join(HERE, "knowledge.txt")

client = OpenAI(base_url="http://127.0.0.1:11434/v1", api_key="ollama")
MODEL = "deepseek-r1:latest"
EMBED_MODEL = "bge-m3"
TOP_K = 3


# ---------- 基础工具 ----------

def get_vector(text: str):
    """文本 → 向量（返回原始 list，方便直接塞进 JSON）"""
    return client.embeddings.create(input=text, model=EMBED_MODEL).data[0].embedding


def cos_sim(vecA, vecB):
    """余弦相似度：只看方向，不看长度"""
    a, b = np.array(vecA), np.array(vecB)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


# ---------- 两个库，形状统一为 [{"text": ..., "vec": [...]}, ...] ----------
# ★ 下面两个加载必须放在 get_vector 定义【之后】，否则 NameError

def load_knowledge(path: str):
    """读纯文本，一行一条。只读，启动时一次性把向量算好。"""
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    return [{"text": t, "vec": get_vector(t)} for t in lines]


def load_memory(path: str):
    """记忆文件里只存 text，向量每次启动现算。文件不存在就从空开始。"""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [{"text": it["text"], "vec": get_vector(it["text"])} for it in raw]


knowledge = load_knowledge(KNOWLEDGE_FILE)
memory = load_memory(MEMORY_FILE)


# ---------- 检索：一个函数，两个库复用 ----------

def search(q: str, items: list, k: int = TOP_K):
    """在任意一个『条目列表』里找最像 q 的 k 条。返回 [[分数, 文本], ...]"""
    if not items:                       # 空库就别浪费一次 embedding 调用了
        return []
    qv = get_vector(q)
    scored = [[cos_sim(qv, item["vec"]), item["text"]] for item in items]
    scored.sort(key=itemgetter(0), reverse=True)
    return scored[:k]


# ---------- 写入：只有记忆会变 ----------

def save_memory(user_text: str):
    text = f"用户: {user_text}"
    memory.append({"text": text, "vec": get_vector(text)})     # 内存里带向量
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:        # 文件里只有文本
        json.dump([{"text": m["text"]} for m in memory],
                  f, ensure_ascii=False, indent=2)


# ---------- 核心：给一句话，还一句话 ----------

def render(hits) -> str:
    """把检索结果渲染成给模型看的文字。分数留在代码里，不进去。"""
    return "\n".join(f"- {it[1]}" for it in hits) or "（无）"


def reply(user_message: str) -> str:
    """不碰 input/print，也不知道 HTTP 的存在。"""
    know = search(user_message, knowledge)   # 资料：自己的 top-K
    mem = search(user_message, memory)       # 记忆：自己的 top-K，不合并排序

    user_block = (
        f"【资料】（可信）\n{render(know)}\n\n"
        f"【相关记忆】（用户过去说过的话，不一定为真）\n{render(mem)}\n\n"
        f"【问题】\n{user_message}"
    )

    llm = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_block},
        ],
    )
    answer = llm.choices[0].message.content
    save_memory(user_message)
    return answer


def main():
    while True:
        try:
            user_message = input("（输入 q 退出）你说：").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            continue

        if user_message.lower() == "q":
            break
        if not user_message:
            continue

        print(reply(user_message))          # ← 就这一行


if __name__ == "__main__":
    main()
