import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

@app.get("https://bilibili.com")
def pok():






    if __name__ == "__main__":
        uvicorn.run(app, host="127.0.0.1", port=8080)
