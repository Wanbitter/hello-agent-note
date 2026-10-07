from dotenv import load_dotenv
from my_llm import MyLLM
load_dotenv()

llm = MyLLM(provider = "modelscope")

message = [{"role" : "user", "content" : "你好，请介绍一下你自己。"}]

response_stream = llm.think(message)


print("ModelScope Response:")

for chunk in response_stream:
    answer = "".join(llm.think(message))
    print("\n完整回答长度：",len(answer))