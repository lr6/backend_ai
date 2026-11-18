"""
第四阶段 · 阶段项目 · Task 1C — main.py
组装 app。

main.py 只做三件事：创建 app、挂路由、挂全局中间件（Task 2 才加）。
业务逻辑一行都不该出现在这里 —— 这是拆包的意义。

写完后运行: ../../.venv/bin/python main.py
全部通过 = Task 1C 过关 ✅
"""

from fastapi import Depends, FastAPI

import models
import schemas
from deps import get_current_user
from routers import auth, todos

app = FastAPI(title="Engineering Todo API")

# TODO 1：把两个 router 挂上来
#   app.include_router(???)  —— 传的是 router 对象，不是模块
#   auth 模块里的 router 变量怎么访问？
#   第三阶段踩过的坑：include_router 的第一个参数是 router 对象，不是 APIRouter 类
app.include_router(auth.router)
app.include_router(todos.router)


# 演示用：登录后能看到自己的信息
@app.get("/users/me", response_model=schemas.UserRead, tags=["users"])
def read_me(current_user: models.User = Depends(get_current_user)):
    return current_user


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    from uuid import uuid4

    from fastapi.testclient import TestClient
    from sqlalchemy import delete

    from database import SessionLocal

    client = TestClient(app)
    errors = []

    username = f"auth_{uuid4().hex[:8]}"
    password = "12345678"
    user_id = None
    tokens = None

    def check(name, cond, detail=""):
        if cond:
            print(f"✅ {name}")
        else:
            errors.append(f"{name} {detail}")

    def bearer(tok):
        return {"Authorization": f"Bearer {tok}"}

    # ---------- 注册 ----------
    try:
        r = client.post("/auth/register", json={"username": username, "password": password})
        check("POST /auth/register 状态码 201", r.status_code == 201, f"实际 {r.status_code} {r.text}")
        body = r.json()
        check("注册返回 username", body.get("username") == username)
        check("注册返回 id 是整数", isinstance(body.get("id"), int))
        check("注册响应不含 password / password_hash",
              "password" not in body and "password_hash" not in body,
              f"实际字段: {list(body)}")
        user_id = body.get("id")
    except Exception as e:
        errors.append(f"注册异常: {type(e).__name__}: {e}")

    try:
        r = client.post("/auth/register", json={"username": username, "password": password})
        check("重复用户名 → 409", r.status_code == 409, f"实际 {r.status_code} {r.text}")
    except Exception as e:
        errors.append(f"重复注册异常: {type(e).__name__}: {e}")

    try:
        r = client.post("/auth/register", json={"username": f"x_{uuid4().hex[:6]}", "password": "short"})
        check("密码少于 8 位 → 422", r.status_code == 422, f"实际 {r.status_code}")
    except Exception as e:
        errors.append(f"短密码异常: {type(e).__name__}: {e}")

    # ---------- 登录 ----------
    try:
        r = client.post("/auth/login", data={"username": username, "password": password})
        check("POST /auth/login 状态码 200", r.status_code == 200, f"实际 {r.status_code} {r.text}")
        body = r.json()
        check("登录返回 access_token", isinstance(body.get("access_token"), str))
        check("登录返回 refresh_token", isinstance(body.get("refresh_token"), str))
        check("token_type 为 bearer", body.get("token_type") == "bearer", f"实际 {body.get('token_type')!r}")
        tokens = body
    except Exception as e:
        errors.append(f"登录异常: {type(e).__name__}: {e}")

    try:
        r = client.post("/auth/login", data={"username": username, "password": "wrongpass"})
        check("密码错误 → 401", r.status_code == 401, f"实际 {r.status_code}")
        check("401 带 WWW-Authenticate: Bearer",
              r.headers.get("www-authenticate") == "Bearer",
              f"实际 {r.headers.get('www-authenticate')!r}")
        check("401 的 detail 是字符串",
              isinstance(r.json().get("detail"), str),
              f"实际 {r.json().get('detail')!r}")
    except Exception as e:
        errors.append(f"错误密码异常: {type(e).__name__}: {e}")

    try:
        r = client.post("/auth/login", data={"username": f"nobody_{uuid4().hex[:6]}", "password": password})
        check("用户不存在 → 401（同样提示）", r.status_code == 401, f"实际 {r.status_code}")
    except Exception as e:
        errors.append(f"不存在用户异常: {type(e).__name__}: {e}")

    try:
        r = client.post("/auth/login", json={"username": username, "password": password})
        check("登录用 JSON 而不是 form → 422", r.status_code == 422, f"实际 {r.status_code}")
    except Exception as e:
        errors.append(f"JSON 登录异常: {type(e).__name__}: {e}")

    # ---------- 刷新 ----------
    if tokens:
        try:
            r = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
            check("POST /auth/refresh 状态码 200", r.status_code == 200, f"实际 {r.status_code} {r.text}")
            body = r.json()
            check("刷新返回新的 access_token", isinstance(body.get("access_token"), str))
            check("刷新返回 refresh_token", isinstance(body.get("refresh_token"), str))
        except Exception as e:
            errors.append(f"刷新异常: {type(e).__name__}: {e}")

        try:
            r = client.post("/auth/refresh", json={"refresh_token": tokens["access_token"]})
            check("用 access 冒充 refresh → 401", r.status_code == 401, f"实际 {r.status_code}")
        except Exception as e:
            errors.append(f"access 冒充异常: {type(e).__name__}: {e}")

        try:
            r = client.post("/auth/refresh", json={"refresh_token": "garbage"})
            check("乱码 refresh → 401", r.status_code == 401, f"实际 {r.status_code}")
        except Exception as e:
            errors.append(f"乱码 refresh 异常: {type(e).__name__}: {e}")

    # ---------- 认证保护 + 所有权 ----------
    other_username = f"other_{uuid4().hex[:8]}"
    other_id = None
    other_tokens = None
    my_todo_id = None
    other_todo_id = None

    if tokens:
        # 造一个用户 B，用来测越权
        try:
            r = client.post("/auth/register", json={"username": other_username, "password": password})
            other_id = r.json().get("id")
            r = client.post("/auth/login", data={"username": other_username, "password": password})
            other_tokens = r.json()
        except Exception as e:
            errors.append(f"创建用户 B 异常: {type(e).__name__}: {e}")

        # 不带 token
        try:
            r = client.get("/todos")
            check("GET /todos 不带 token → 401", r.status_code == 401, f"实际 {r.status_code}")
            check("未认证响应带 WWW-Authenticate: Bearer",
                  r.headers.get("www-authenticate") == "Bearer",
                  f"实际 {r.headers.get('www-authenticate')!r}")
            r = client.post("/todos", json={"title": "x"})
            check("POST /todos 不带 token → 401", r.status_code == 401, f"实际 {r.status_code}")
        except Exception as e:
            errors.append(f"未认证访问异常: {type(e).__name__}: {e}")

        # 带 token 创建；同时试图伪造 user_id 为别人
        try:
            r = client.post(
                "/todos",
                json={"title": "我的待办", "user_id": other_id},
                headers=bearer(tokens["access_token"]),
            )
            check("POST /todos 带 token → 201", r.status_code == 201, f"实际 {r.status_code} {r.text}")
            body = r.json()
            check("todo 归属当前用户（忽略伪造的 user_id）",
                  body.get("user_id") == user_id,
                  f"实际 user_id={body.get('user_id')}，期望 {user_id}")
            my_todo_id = body.get("id")
        except Exception as e:
            errors.append(f"创建 todo 异常: {type(e).__name__}: {e}")

        # 列表只看到自己的
        try:
            r = client.get("/todos", headers=bearer(tokens["access_token"]))
            check("GET /todos 带 token → 200", r.status_code == 200, f"实际 {r.status_code}")
            ids = [t.get("id") for t in r.json()]
            check("列表包含自己的 todo", my_todo_id in ids, f"实际 ids={ids}")
        except Exception as e:
            errors.append(f"列表异常: {type(e).__name__}: {e}")

        # 用户 B 创建一条 todo
        if other_tokens:
            try:
                r = client.post("/todos", json={"title": "B 的待办"},
                                headers=bearer(other_tokens["access_token"]))
                other_todo_id = r.json().get("id")
            except Exception as e:
                errors.append(f"B 创建 todo 异常: {type(e).__name__}: {e}")

        # A 访问 / 改 / 删 B 的 todo → 404
        if other_todo_id is not None:
            try:
                r = client.get(f"/todos/{other_todo_id}", headers=bearer(tokens["access_token"]))
                check("A 查 B 的 todo → 404", r.status_code == 404, f"实际 {r.status_code}")
                r = client.patch(f"/todos/{other_todo_id}", json={"done": True},
                                 headers=bearer(tokens["access_token"]))
                check("A 改 B 的 todo → 404", r.status_code == 404, f"实际 {r.status_code}")
                r = client.delete(f"/todos/{other_todo_id}", headers=bearer(tokens["access_token"]))
                check("A 删 B 的 todo → 404", r.status_code == 404, f"实际 {r.status_code}")
                # 确认 B 的 todo 还在、没被改动
                r = client.get(f"/todos/{other_todo_id}", headers=bearer(other_tokens["access_token"]))
                check("B 的 todo 未被改动", r.status_code == 200 and r.json().get("done") is False,
                      f"实际 {r.status_code} {r.text}")
            except Exception as e:
                errors.append(f"越权测试异常: {type(e).__name__}: {e}")

        # 自己的 todo 可以改、可以删
        if my_todo_id is not None:
            try:
                r = client.patch(f"/todos/{my_todo_id}", json={"done": True},
                                 headers=bearer(tokens["access_token"]))
                check("A 改自己的 todo → 200", r.status_code == 200, f"实际 {r.status_code} {r.text}")
                check("done 变为 True", r.json().get("done") is True)
                r = client.delete(f"/todos/{my_todo_id}", headers=bearer(tokens["access_token"]))
                check("A 删自己的 todo → 204", r.status_code == 204, f"实际 {r.status_code}")
            except Exception as e:
                errors.append(f"自己的 todo 操作异常: {type(e).__name__}: {e}")

        # /users/me
        try:
            r = client.get("/users/me", headers=bearer(tokens["access_token"]))
            check("GET /users/me → 200 且是本人", r.status_code == 200 and r.json().get("username") == username,
                  f"实际 {r.status_code} {r.text}")
        except Exception as e:
            errors.append(f"/users/me 异常: {type(e).__name__}: {e}")

    # ---------- 清理 ----------
    db = SessionLocal()
    try:
        for uid in (user_id, other_id):
            if uid is not None:
                db.execute(delete(models.Todo).where(models.Todo.user_id == uid))
                db.execute(delete(models.User).where(models.User.id == uid))
        db.commit()
    finally:
        db.close()

    print()
    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！Task 1C main.py = ✅")
