from multiprocessing import resource_sharer

from openai import OpenAI
client = OpenAI(
    base_url = "http://127.0.0.1:11434/v1",
    api_key = "ollama",
)

def get_vector(message : str):
    ans = client.embeddings.create(
        model="bge-m3",
        input=message,
    )
    return ans.data[0].embedding


def sim_text(messageA : str, messageB : str):
    vectorA = get_vector(messageA)
    vectorB = get_vector(messageB)
    norm_a = np.linalg.norm(vectorA)
    norm_b = np.linalg.norm(vectorB)
    dot_ab = np.dot(vectorA, vectorB)
    cos_sim_ab = dot_ab / (norm_a * norm_b)
    return cos_sim_ab





import numpy as np

# a = np.array([1, 2, 3])
# b = np.array([6, 4, 6])
#
# # ① 点积
# dot = np.dot(a, b)        # 或者 a @ b
#
# # ② 各自的长
# norm_a = np.linalg.norm(a)
# norm_b = np.linalg.norm(b)
#
# # ③ 余弦相似度
# cos_sim = dot / (norm_a * norm_b)
# print(cos_sim)



# ===============================================
#
# messageA = "我是一名大三学生"
# messageB = "我在读大学三年级"
# messageC = "今天天气不错"
# messageD = "我是大四的"
#
# vectorA = get_vector(messageA)
# vectorB = get_vector(messageB)
# vectorC = get_vector(messageC)
# vectorD = get_vector(messageD)
#
# norm_a = np.linalg.norm(vectorA)
# norm_b = np.linalg.norm(vectorB)
# norm_c = np.linalg.norm(vectorC)
# norm_d = np.linalg.norm(vectorD)
#
# dot_ab = np.dot(vectorA, vectorB)
# dot_bc = np.dot(vectorB, vectorC)
# dot_bd = np.dot(vectorB, vectorD)
#
# cos_sim_ab = dot_ab / (norm_a * norm_b)
# cos_sim_bc = dot_bc / (norm_b * norm_c)
# cos_sim_bd = dot_bd / (norm_b * norm_d)
#
#
#
# print(cos_sim_ab)
# print(cos_sim_bc)
# print(cos_sim_bd)


# messagelove01 = "我喜欢你"
# messagelove02 = "你喜欢我"
#
# print(sim_text(messagelove01, messagelove02))



def cos_sim(vecA, vecB):
    a, b = np.array(vecA), np.array(vecB)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

# ---------- 建库（向量只算一次）----------
resource = [
    "珍爱生命，远离毒品",
    "鲸鱼不是鱼，是鲸",
    "喝水有利于身体健康",
    "长期看手机会导致近视",
    "长期看电脑会导致近视",
    "学而不思则罔，思而不学则殆",
]

rag_resource = [
    {"text": m, "vector": get_vector(m)}
    for m in resource
]

# ---------- 查询 ----------
q = input("输入你的问题：")
q_vec = get_vector(q)

# 算相似度
scored = [
    (cos_sim(q_vec, item["vector"]), item["text"])
    for item in rag_resource
]

# 按相似度从高到低排序
scored.sort(key=lambda x: x[0], reverse=True)

# ---------- 输出 ----------
for sim, text in scored:
    print(f"{sim:.4f}  {text}")
