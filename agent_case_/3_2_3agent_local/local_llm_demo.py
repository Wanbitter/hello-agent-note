import os
# 关键：使用国内镜像加速下载
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HUB_DISABLE_XET'] = '1'

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model_id = os.path.join(
    BASE_DIR,
    "models--Qwen--Qwen1.5-0.5B-Chat",
    "snapshots",
    "4d14e384a4b037942bb3f3016665157c8bcb70ea"
)
# 指定模型ID
# 硬编码，可以改成上面的
# model_id = r"F:\Python_Project\agent_case_\3_2_3agent_local\models--Qwen--Qwen1.5-0.5B-Chat\snapshots\4d14e384a4b037942bb3f3016665157c8bcb70ea"

# 设置设备，优先使用GPU
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# 加载分词器
tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True, use_fast=True)

# 加载模型，并将其移动到指定设备
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    trust_remote_code=True
).to(device)

print("模型和分词器加载完成！")
messages = [
    {"role": "system", "content": "你是这个世界无所不知的神"},
    {"role" : "user", "content": "介绍一下你自己"}
]

# 使用分词器的模板格式化输入
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)

# 编码输入文本
model_inputs = tokenizer([text], return_tensors="pt").to(device)

# 使用模型生成回答
generated_ids = model.generate(
    model_inputs.input_ids,
    max_new_tokens=512,
    do_sample=True,
    temperature=1.5,
    top_p=0.9
)

# 将生成的 Token ID 截取掉输入部分
generated_ids = [
    output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
]

# 解码生成的 Token ID
response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

print("\n模型的回答:")
print(response)