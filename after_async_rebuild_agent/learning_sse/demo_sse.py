import time
from fastapi import FastAPI
from fastapi.sse import EventSourceResponse
import uvicorn

app = FastAPI()


@app.get("/count", response_class=EventSourceResponse)
def count():
    for i in range(1, 6):
        yield {"n": i, "at": time.strftime("%H:%M:%S")}
        time.sleep(1)          # ← 故意每秒才吐一条


if __name__ == "__main__":
    uvicorn.run(app, port=8099)