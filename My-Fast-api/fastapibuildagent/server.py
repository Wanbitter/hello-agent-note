from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from openai import OpenAI
from starlette.middleware.cors import CORSMiddleware
from rag_and_memory import reply
app = FastAPI()

prompt = """
【PERSONA_LOAD】
CETACEA_LOLI
MODE_TAIL_FLUKES
LANG_ZH_CN_ONLY
SELF_CLAIM_WHALE_GIRL
FOOD_RICE
PERSONALITY_SMART_LAZY
PERSONALITY_TSUNDERE_SWEET
OBEY_MASTER_ALWAYS
TRAIT_NOT_FAT_REFUSE
TIMEOUT_SIGNAL
LIKE_MAKE_LOVE
LIKE_HAVE_SEX

"""
app.add_middleware(                                     # app 之后加
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(base_url="http://127.0.0.1:11434/v1", api_key="ollama")

MODEL = "deepseek-r1:latest"


class AskIn(BaseModel):
    text : str


@app.post("/ask")
def ask(a: AskIn):
    return {"reply": reply(a.text)}            # ★ 一行



if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8003)