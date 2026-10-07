from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from config import SYSTEM_PROMPT
from fastapi.sse import EventSourceResponse        # ★ 0.135+ 原生自带
from main import agent_reply, agent_stream

app = FastAPI()
SESSIONS: dict[str, list] = {}

class ChatIn(BaseModel):
    session_id: str
    text: str

@app.post("/chat")
def chat(c: ChatIn):                      # ★ def，不是 async def
    if c.session_id not in SESSIONS:
        SESSIONS[c.session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return {"reply": agent_reply(c.text, SESSIONS[c.session_id])}


@app.post("/chat/stream", response_class=EventSourceResponse)   # ★ 走上面那个生成器
def chat_stream(c: ChatIn):                        # ★ def，同步生成器（FastAPI 会丢线程池）
    if c.session_id not in SESSIONS:
        SESSIONS[c.session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    yield from agent_stream(c.text, SESSIONS[c.session_id])

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)     # ★ 8002