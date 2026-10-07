import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel


from agent_try.chatbot_01 import chat

app = FastAPI()
class chatIn(BaseModel):
    text: str

@app.post("/chat")
def chat_endpoint(c: chatIn):
    return {"reply" : chat(c.text)}



if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)

