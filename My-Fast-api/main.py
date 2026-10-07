from fastapi import *
from pydantic import BaseModel
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

# ---------------- "数据库"（住在内存里）----------------
TODOS: dict[int, dict] = {}      # ← dict，不是 dist
NEXT_ID = 1

app = FastAPI()

app.add_middleware(              # 给整个 app 装一个"中间件"
    CORSMiddleware,              # 装哪个：专门管 CORS 的那个
    allow_origins=["*"],         # 允许哪些源来读（* = 任何网站）
    allow_methods=["*"],         # 允许哪些方法（* = 全部）
    allow_headers=["*"],         # 允许带哪些请求头（* = 全部）
)

# ---------------- 请求体的形状（自己定义）----------------
class TodoIn(BaseModel):
    title: str                   # 建待办时必须给一个标题

class TodoOut(BaseModel):
    id: int
    title: str
    done: bool

class TodoPut(BaseModel):
    title: str
    done: bool = False          # ← 没有默认值，客户端【必须】两个都传

class TodoPatch(BaseModel):
    title: str | None = None      # ← 有默认值 = 可以不传
    done: bool | None = None

# ---------------- 接口 ----------------
@app.post("/todos", status_code=201, response_model=TodoOut)
def create_todo(t: TodoIn):
    global NEXT_ID
    todo = {"id": NEXT_ID, "title": t.title, "done": False , "secret" : "隐藏信息测试"}
    TODOS[NEXT_ID] = todo        # 写进"数据库"
    NEXT_ID += 1
    return todo

@app.get("/todos",response_model=list[TodoOut])
def list_todos():
    return list(TODOS.values())  # 从"数据库"读

@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    if todo_id not in TODOS:
        # 404：这个 id 本来就不存在，错在客户端
        raise HTTPException(status_code=404, detail=f"没有 id={todo_id} 的待办")

    del TODOS[todo_id]
    # 204 = "成功，但没有任何内容" → 所以什么都不返回

@app.put("/todos/{todo_id}",response_model=TodoOut)
def update_todo(todo_id: int, t: TodoPut):
    if todo_id not in TODOS:
        raise HTTPException(status_code=404, detail=f"没有 id={todo_id} 的待办")
    TODOS[todo_id] = {"id" : todo_id, "title" : t.title,"done":t.done}
    return TODOS[todo_id]

@app.patch("/todos/{todo_id}", response_model=TodoOut)
def patch_todo(todo_id: int, p: TodoPatch):
    if todo_id not in TODOS:
        raise HTTPException(status_code=404, detail=f"没有 id={todo_id} 的待办")

    updates = p.model_dump(exclude_unset=True)    # ★ 只拿"客户端真的传了的"字段
    TODOS[todo_id].update(updates)                # 只覆盖这几个
    return TODOS[todo_id]



if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)