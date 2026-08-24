"""
第一阶段 · 2 REST API 设计 — 检验练习

每个 TODO 需要你来实现。
写完后运行: .venv/bin/python practice.py
全部通过 = REST API 设计 ✅

提示（前端对照）：
  - 资源 = URL 名词（/todos），动作 = HTTP 方法（GET/POST/DELETE）
  - status_code=201     ~ 响应里的 HTTP 状态码，前端 axios 拦截器靠它判断
  - 分页 ?page=&size=   ~ 列表页的「上一页/下一页」
  - HTTPException(404)  ~ 后端抛错，返回统一的 {"detail": "..."}
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.testclient import TestClient

app = FastAPI()

# ============================================
# 内存数据库（已帮你建好，模拟一张 todos 表）
# ============================================
todos = [
    {"id": 1, "title": "学 REST"},
    {"id": 2, "title": "写代码"},
    {"id": 3, "title": "睡觉"},
]


class Todo(BaseModel):
    """创建 todo 时接收的请求体，只有一个字段 title: str"""
    # TODO: 写一个字段 title: str
    title: str


# ===== 练习 1：资源建模判断（纯函数）=====
def is_restful_url(url: str) -> bool:
    """
    判断一个 URL 是否是好的 REST 资源设计。
    规则：URL 应该是「名词」，动作交给 HTTP 方法。
    如果 URL 里包含这些动词之一，就是坏设计，返回 False：
      get / create / update / delete / add / remove / edit

    例如:
      is_restful_url("/users")       -> True
      is_restful_url("/users/42")    -> True
      is_restful_url("/getUser")     -> False
      is_restful_url("/deleteUser")  -> False
    """
    # TODO
    arr = ['get', 'create', 'update', 'delete', 'remove', 'edit']
    for x in arr:
        if(x in url):
            return False
    return True


# ===== 练习 2：创建资源（POST + 201 状态码）=====
@app.post("/todos", status_code=201)
def create_todo(todo: Todo):
    """
    创建一个新 todo，加入 todos 列表，返回这个新 todo（dict）。
    新 id = 现有最大 id + 1（提示：max(t["id"] for t in todos) + 1）。

    注意：装饰器里已经写了 status_code=201，表示「创建成功」。
    前端类比：fetch POST 成功后，看 response.status === 201。
    """
    # TODO
    new_id = max(t['id'] for t in todos) + 1
    new_todo = {'id': new_id, 'title': todo.title}
    todos.append(new_todo)
    return new_todo


# ===== 练习 3：分页（列表 + ?page=&size=）=====
@app.get("/todos")
def list_todos(page: int = 1, size: int = 10):
    """
    返回分页后的列表，结构：
      {"items": [...], "page": page, "size": size, "total": len(todos)}

    items 是切片后的数据：从 (page-1)*size 开始，取 size 个。
    提示：todos[start : start + size]

    前端类比：列表页请求第 2 页 → /todos?page=2&size=10
    """
    # TODO
    start = (page - 1) * size
    items = todos[start: start + size]
    return { 'items': items, 'page': page, 'size': size, 'total': len(todos) }


# ===== 练习 4：错误处理（404 + HTTPException）=====
@app.get("/todos/{todo_id}")
def get_todo(todo_id: int):
    """
    按 id 找 todo：
      - 找到了 → 返回这个 todo（dict）
      - 找不到 → raise HTTPException(status_code=404, detail="Todo not found")

    前端类比：fetch 拿到 404，axios 拦截器统一弹「资源不存在」。
    """
    # TODO
    for t in todos:
        if t['id'] == todo_id:
            return t
    raise HTTPException(status_code=404, detail="Todo not found")


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

    # 练习 1：资源建模
    check("练习1 /users", is_restful_url("/users"), True)
    check("练习1 /users/42", is_restful_url("/users/42"), True)
    check("练习1 /getUser", is_restful_url("/getUser"), False)
    check("练习1 /deleteUser", is_restful_url("/deleteUser"), False)
    check("练习1 /createOrder", is_restful_url("/createOrder"), False)

    # 练习 3：分页（先测，避免练习2 POST 改变数据）
    r = client.get("/todos?page=1&size=2")
    body = r.json()
    check("练习3 第一页 items 数量", len(body["items"]), 2)
    check("练习3 total", body["total"], 3)
    check("练习3 page", body["page"], 1)
    check("练习3 第一页内容", body["items"], [{"id": 1, "title": "学 REST"}, {"id": 2, "title": "写代码"}])
    r2 = client.get("/todos?page=2&size=2")
    check("练习3 第二页 items 数量", len(r2.json()["items"]), 1)

    # 练习 4：错误处理
    r = client.get("/todos/1")
    check("练习4 找到返回 200", r.status_code, 200)
    check("练习4 找到内容", r.json(), {"id": 1, "title": "学 REST"})
    r = client.get("/todos/999")
    check("练习4 找不到返回 404", r.status_code, 404)

    # 练习 2：创建资源（最后测，会往 todos 里加数据）
    r = client.post("/todos", json={"title": "新任务"})
    check("练习2 创建返回 201", r.status_code, 201)
    check("练习2 返回新 title", r.json().get("title"), "新任务")
    check("练习2 新 id 是 4", r.json().get("id"), 4)

    if errors:
        print(f"\n有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("\n🎉 全部通过！REST API 设计 = ✅")
