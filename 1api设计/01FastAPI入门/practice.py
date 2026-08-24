"""
第一阶段 · 1 FastAPI 入门 — 检验练习

每个 TODO 需要你来实现。
写完后运行: .venv/bin/python practice.py
全部通过 = FastAPI 入门 ✅

提示（前端对照）：
  - FastAPI()              ~  createApp() / new Vue()
  - @app.get("/users/{id}") ~  React Router 的 /users/:id（路径参数）
  - 函数参数 q: str = None  ~  查询参数 ?q=xxx（URLSearchParams）
  - POST + Pydantic 模型    ~  fetch 的 body: JSON.stringify()
  - TestClient(app).get()   ~  fetch() 发请求拿响应
"""

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.testclient import TestClient

# ============================================
# 应用实例（已帮你建好，装饰器依赖它）
# ============================================
app = FastAPI()


# ===== 练习 1：第一个路由（根路由）=====
@app.get("/")
def read_root():
    """
    返回 {"message": "Hello World"}。
    测试会请求 GET /，检查返回的 JSON。
    """
    # TODO: 返回 {"message": "Hello World"}
    return {"message": 'Hello World'}


# ===== 练习 2：路径参数（path parameter）=====
@app.get("/users/{user_id}")
def get_user(user_id: int):
    """
    返回 {"user_id": user_id}。
    注意：路径里的 {user_id} 会被 FastAPI 捕获，作为参数传入这个函数。
    前端类比：React Router 的 /users/:user_id
    """
    # TODO: 返回 {"user_id": user_id}
    return {"user_id": user_id}


# ===== 练习 3：查询参数（query parameter）=====
@app.get("/search")
def search(q: str = None):
    """
    返回 {"q": q}。
    q 不在路径里，而是 URL 里的 ?q=xxx。
    前端类比：URLSearchParams(location.search).get("q")
    """
    # TODO: 返回 {"q": q}
    return {"q": q}


# ===== 练习 4：请求体（request body）=====
class Item(BaseModel):
    """
    Item 模型，定义两个字段：
      - name: str
      - price: float
    """
    # TODO: 写两个字段
    name: str
    price: float


@app.post("/items")
def create_item(item: Item):
    """
    接收 JSON 请求体，返回 {"name": item.name, "price": item.price}。
    前端类比：fetch("/items", {method:"POST", body: JSON.stringify(...)})
    """
    # TODO: 返回 {"name": item.name, "price": item.price}
    return {"name": item.name, "price": item.price}


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

    # 练习 1：根路由
    r = client.get("/")
    check("练习1 状态码", r.status_code, 200)
    check("练习1 JSON", r.json(), {"message": "Hello World"})

    # 练习 2：路径参数
    r = client.get("/users/42")
    check("练习2 状态码", r.status_code, 200)
    check("练习2 JSON", r.json(), {"user_id": 42})
    check("练习2 user_id 是 int", type(r.json()["user_id"]), int)

    # 练习 3：查询参数
    r = client.get("/search?q=fastapi")
    check("练习3 有参数", r.json(), {"q": "fastapi"})
    r = client.get("/search")
    check("练习3 无参数", r.json(), {"q": None})

    # 练习 4：请求体
    r = client.post("/items", json={"name": "apple", "price": 3.5})
    check("练习4 状态码", r.status_code, 200)
    check("练习4 JSON", r.json(), {"name": "apple", "price": 3.5})

    if errors:
        print(f"\n有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("\n🎉 全部通过！FastAPI 入门 = ✅")
