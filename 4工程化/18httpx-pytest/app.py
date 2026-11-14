"""
第四阶段 · 18 httpx + pytest — 被测应用

一个最小 Todo API：
- 数据存在内存 Store 里
- 通过 get_store 依赖注入，测试里用 dependency_overrides 替换成干净实例
- /me 演示请求头认证
"""

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class TodoOut(BaseModel):
    id: int
    title: str
    done: bool = False


class Store:
    def __init__(self):
        self.todos: dict[int, TodoOut] = {}
        self.next_id = 1

    def list(self) -> list[TodoOut]:
        return list(self.todos.values())

    def get(self, todo_id: int) -> TodoOut | None:
        return self.todos.get(todo_id)

    def create(self, title: str) -> TodoOut:
        todo = TodoOut(id=self.next_id, title=title)
        self.todos[todo.id] = todo
        self.next_id += 1
        return todo

    def delete(self, todo_id: int) -> bool:
        return self.todos.pop(todo_id, None) is not None


_store = Store()


def get_store() -> Store:
    return _store


def require_token(x_token: str | None = Header(default=None)) -> str:
    if x_token != "secret":
        raise HTTPException(401, "invalid token")
    return "demo-user"


app = FastAPI()


@app.get("/todos", response_model=list[TodoOut])
def list_todos(store: Store = Depends(get_store)):
    return store.list()


@app.post("/todos", response_model=TodoOut, status_code=201)
def create_todo(payload: TodoCreate, store: Store = Depends(get_store)):
    return store.create(payload.title)


@app.get("/todos/{todo_id}", response_model=TodoOut)
def get_todo(todo_id: int, store: Store = Depends(get_store)):
    todo = store.get(todo_id)
    if todo is None:
        raise HTTPException(404, "todo not found")
    return todo


@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int, store: Store = Depends(get_store)):
    if not store.delete(todo_id):
        raise HTTPException(404, "todo not found")
    return None


@app.get("/me")
def me(user: str = Depends(require_token)):
    return {"user": user}
