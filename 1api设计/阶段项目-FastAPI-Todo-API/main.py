"""
第一阶段 · 阶段项目：FastAPI Todo API

目标：用 FastAPI 写一个完整的 Todo API（CRUD + 数据存内存）
这是第一阶段的综合大考，串起前面学的全部知识。

需要实现的 5 个接口：

| 方法   | 路径          | 请求            | 成功状态码 | 说明 |
|--------|--------------|-----------------|-----------|------|
| GET    | /todos       | ?page=1&size=10 | 200       | 分页列表 {items, page, size, total} |
| GET    | /todos/{id}  | -               | 200       | 单个，找不到 404 |
| POST   | /todos       | {title, done?}  | 201       | 创建，自动生成 id |
| PUT    | /todos/{id}  | {title, done?}  | 200       | 更新，找不到 404 |
| DELETE | /todos/{id}  | -               | 204       | 删除，找不到 404 |

写完后运行: .venv/bin/python main.py
全部通过 = 阶段项目 FastAPI Todo API ✅

提示：
  - Todo 模型：title: str（必填）、done: bool = False（默认）
  - id 生成：注意空列表时 max([]) 会报错
  - DELETE 返回 204：用 status_code=204，无 body
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.testclient import TestClient

app = FastAPI(title="Todo API", description="待办事项管理接口", version="1.0.0")


# ============================================
# 你的实现：Todo 模型 + 内存存储 + 5 个接口
# ============================================

todos = []

class Todo(BaseModel):
    title: str
    done: bool = False

@app.get('/todos')
def get_todos(page: int = 1, size: int = 10):
    start = (page-1)*size
    items = todos[start: start+size]
    return {
        'page': page,
        'size': size,
        'items': items,
        'total': len(todos)
    }

@app.get('/todos/{todo_id}')
def get_todo(todo_id: int):
    for t in todos:
        if(t['id'] == todo_id):
            return t
    raise HTTPException(status_code=404, detail='todo not found')

@app.post('/todos', status_code=201)
def create_todo(todo: Todo):
    new_id = 1 if len(todos) == 0 else max(t['id'] for t in todos) + 1
    new_title = todo.title
    todos.append({
        'id': new_id,
        'title': new_title,
        'done': todo.done
    })
    return { 'id': new_id, 'title': new_title, 'done': todo.done }

@app.put('/todos/{todo_id}')
def update_todo(todo_id: int, todo: Todo):
    for t in todos:
        if(t['id'] == todo_id):
            t['done'] = todo.done
            t['title'] = todo.title
            return todo
    raise HTTPException(status_code=404, detail='todo not found')

@app.delete('/todos/{todo_id}', status_code=204)
def delete_todo(todo_id: int):
    for index, t in enumerate(todos):
        if(t['id'] == todo_id):
            todos.pop(index)
            return {}
    raise HTTPException(status_code=404, detail='todo not found')

# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    client = TestClient(app)
    errors = []

    def check(name, actual, expected):
        if actual != expected:
            errors.append(f"{name}: 期望 {expected}，实际 {actual}")
        else:
            print(f"✅ {name}")

    # 1. 创建 3 条
    r = client.post("/todos", json={"title": "学习 FastAPI"})
    check("POST 创建返回 201", r.status_code, 201)
    check("POST 返回 id=1", r.json().get("id"), 1)
    check("POST done 默认 False", r.json().get("done"), False)

    client.post("/todos", json={"title": "写代码", "done": True})
    client.post("/todos", json={"title": "睡觉"})

    # 2. 列表（分页）
    r = client.get("/todos")
    check("GET 列表 total=3", r.json().get("total"), 3)
    check("GET 列表 items 3 条", len(r.json().get("items", [])), 3)

    r = client.get("/todos?page=1&size=2")
    check("GET 分页第1页 2 条", len(r.json().get("items", [])), 2)
    r = client.get("/todos?page=2&size=2")
    check("GET 分页第2页 1 条", len(r.json().get("items", [])), 1)

    # 3. 单个
    r = client.get("/todos/1")
    check("GET 单个 200", r.status_code, 200)
    check("GET 单个 title", r.json().get("title"), "学习 FastAPI")
    r = client.get("/todos/999")
    check("GET 不存在 404", r.status_code, 404)

    # 4. 更新
    r = client.put("/todos/1", json={"title": "学完了", "done": True})
    check("PUT 更新 200", r.status_code, 200)
    check("PUT 更新 title", r.json().get("title"), "学完了")
    check("PUT 更新 done", r.json().get("done"), True)
    r = client.put("/todos/999", json={"title": "x"})
    check("PUT 不存在 404", r.status_code, 404)

    # 5. 删除
    r = client.delete("/todos/1")
    check("DELETE 204", r.status_code, 204)
    r = client.get("/todos/1")
    check("DELETE 后再查 404", r.status_code, 404)
    r = client.delete("/todos/999")
    check("DELETE 不存在 404", r.status_code, 404)

    if errors:
        print(f"\n有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("\n🎉 全部通过！FastAPI Todo API = ✅")
