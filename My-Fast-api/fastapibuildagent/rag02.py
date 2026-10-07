"""最小 RAG：检索 → 让模型基于资料回答。"""

import numpy as np
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:11434/v1", api_key="ollama")

MODEL = "deepseek-r1:latest"
EMBED_MODEL = "bge-m3"
TOP_K = 3


def get_vector(text: str):
    """文本 → 向量"""
    return np.array(
        client.embeddings.create(model=EMBED_MODEL, input=text).data[0].embedding
    )


def cos_sim(vecA, vecB) -> float:
    """余弦相似度：只看方向，不看长度"""
    a, b = np.array(vecA), np.array(vecB)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# ---------- 建库：向量只算一次 ----------
resource = [
    "珍爱生命，远离毒品",
    "鲸鱼不是鱼，是鲸",
    "喝水有利于身体健康",
    "长期看手机会导致近视",
    "长期看电脑会导致近视",
    "学而不思则罔，思而不学则殆",
]

rag_resource = [{"text": m, "vector": get_vector(m)}
                for m in resource]


def search(question: str, top_k: int = TOP_K):
    """检索：返回最像的 top_k 条 [(分数, 文本), ...]"""
    q_vec = get_vector(question)
    scored = [(cos_sim(q_vec, item["vector"]), item["text"]) for item in rag_resource]
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


# ========== ↓↓↓ 这一段是新加的 ↓↓↓ ==========

RULE = """你是一个严谨的助手。

规则：
1. 只根据【资料】里的内容回答。
2. 资料里没有相关信息时，直接回答"资料里没有"，不要编造。
3. 不要使用资料以外的知识。
"""


def ask(question: str, hits : list) -> str:
    """把检索结果拼进 messages，让模型基于资料回答。"""

    # ① 把 top_k 条拼成一段带编号的文字 —— 一步一步来
    lines = []
    for i, item in enumerate(hits, 1):
        lines.append(f"{i}. {item[1]}")
    doc_text = "\n".join(lines)
    # ② 组装 messages
    messages = [
        {"role": "system", "content": RULE},
        {"role": "user", "content": f"【资料】\n{doc_text}\n\n【问题】\n{question}"},
    ]

    r = client.chat.completions.create(model=MODEL, messages=messages)
    return r.choices[0].message.content


# ========== ↑↑↑ 新加的到此为止 ↑↑↑ ==========


if __name__ == "__main__":
    while True:
        q = input("\n提问（quit 退出）：").strip()
        if q in {"quit", "exit"}:
            break
        if not q:
            continue

        hits = search(q)     # ★ 只检索一次，结果传给 ask
        if hits[0][0] <= 0.3:
            print("没有可靠的资本表面这件事情")
        else:

            print("\n--- 检索到的资料 ---")
            for score, text in hits:
                print(f"  {score:.4f}  {text}")

            print("\n--- 模型回答 ---")
            print(ask(q, hits))