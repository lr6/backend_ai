"""
第三阶段 · 阶段项目 · Task 4 — main.py（认证 + 受保护路由）
认证路由：注册 / 登录 / 刷新

Task 4B 会在这里继续加 get_current_user 和受保护的 todo 路由。

写完后运行: ../../.venv/bin/python main.py
全部通过 = Task 4 过关 ✅
"""

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

import models
import schemas
import security
from database import get_db

app = FastAPI(title="Auth Todo API")


# 统一造 401：必须带 WWW-Authenticate: Bearer（学习项 12）
def auth_error(detail: str = "invalid credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


# ===== POST /auth/register =====
@app.post("/auth/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    注册。

    步骤：
      1. 查重：select(models.User).where(models.User.username == payload.username)
         → 有结果就 raise HTTPException(409, "username already taken")
      2. 造 User：只传 username / email / password_hash
         password_hash 用 security.hash_password(payload.password) 生成
         （注意：不能把 payload.model_dump() 整个塞进去，它里面是明文 password）
      3. db.add / db.commit / db.refresh
      4. return user
    """
    existing = db.scalar(select(models.User).where(models.User.username == payload.username))
    if existing is not None:
        raise HTTPException(409, "username already taken")
    user = models.User(
        username = payload.username,
        email = payload.email,
        password_hash = security.hash_password(payload.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ===== POST /auth/login =====
@app.post("/auth/login", response_model=schemas.TokenPair)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    登录（OAuth2 password flow：收 form，不收 JSON）。

    步骤：
      1. 按 username 查用户
      2. 用户不存在 或 verify_password 失败 → raise auth_error()
         （两种失败给同一个提示，别告诉攻击者用户名是否存在）
      3. 成功 → 返回 TokenPair：
           access_token  = security.create_access_token(user.id)
           refresh_token = security.create_refresh_token(user.id)
         （token_type 有默认值，不用传）
    """
    user = db.scalar(select(models.User).where(models.User.username == form.username))
    if user is None or not security.verify_password(form.password, user.password_hash):
        raise auth_error()
    return schemas.TokenPair(
        access_token=security.create_access_token(user.id),
        refresh_token=security.create_refresh_token(user.id)
    )



# ===== POST /auth/refresh =====
@app.post("/auth/refresh", response_model=schemas.TokenPair)
def refresh(payload: schemas.RefreshRequest, db: Session = Depends(get_db)):
    """
    用 refresh token 换一对新 token。

    步骤：
      1. try: claims = security.decode_token(payload.refresh_token, "refresh")
         except JWTError: raise auth_error("invalid refresh token")
         —— 注意用一条 except 兜住：过期、伪造、类型不对，统一 401
      2. 按 claims["user_id"] 查用户 → 不存在也 raise auth_error()
      3. 返回新的 TokenPair（access + refresh 都重新签）
    """
    try:
        claims = security.decode_token(payload.refresh_token, "refresh")
    except JWTError:
        raise auth_error("invalid refresh token")

    user = db.get(models.User, claims["user_id"])
    if user is None:
        raise auth_error("invalid refresh token")
    return schemas.TokenPair(
        access_token=security.create_access_token(user.id),
        refresh_token=security.create_refresh_token(user.id)
    )


# ============================================
# Task 4B：当前用户依赖 + 受保护的 Todo 路由
# ============================================

# tokenUrl 指向登录接口，Swagger 的 Authorize 按钮会用到
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """
    从 Authorization: Bearer <token> 解析出当前用户。

    Depends 链：oauth2_scheme 取出 token → 这里验 token → 查库 → 返回 User

    步骤：
      1. try: claims = security.decode_token(token, "access")
         except JWTError: raise auth_error("invalid token")
         —— 注意第二个参数是 "access"：refresh token 不能访问业务接口
      2. user = db.get(models.User, claims["user_id"])
         → None 就 raise auth_error("invalid token")
      3. return user
    """
    try:
        claims = security.decode_token(token, "access")
    except JWTError:
        raise auth_error("invalid token")
    user = db.get(models.User, claims["user_id"])
    if user is None:
        raise auth_error("invalid token")
    return user


# 演示用：登录后能看到自己的信息
@app.get("/users/me", response_model=schemas.UserRead)
def read_me(current_user: models.User = Depends(get_current_user)):
    return current_user


# ===== POST /todos =====
@app.post("/todos", response_model=schemas.TodoRead, status_code=status.HTTP_201_CREATED)
def create_todo(
    payload: schemas.TodoCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    创建 todo，归属当前用户。

    步骤：
      1. todo = models.Todo(title=payload.title, user_id=current_user.id)
         —— 注意 user_id 来自 current_user，不是请求体
      2. add / commit / refresh / return
    """
    todo = models.Todo(title=payload.title, user_id=current_user.id)
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo



# ===== GET /todos =====
@app.get("/todos", response_model=list[schemas.TodoRead])
def list_todos(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    只返回自己的 todo。

    步骤：
      stmt = select(models.Todo).where(models.Todo.user_id == current_user.id)
      return db.scalars(stmt).all()
    """
    stmt = select(models.Todo).where(models.Todo.user_id == current_user.id)
    return db.scalars(stmt).all()
    


# ===== GET /todos/{todo_id} =====
@app.get("/todos/{todo_id}", response_model=schemas.TodoRead)
def get_todo(
    todo_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    查单条，只能查自己的。

    推荐写法（一次查询同时完成「存在」和「归属」判断）：
      todo = db.scalar(
          select(models.Todo).where(
              models.Todo.id == todo_id,
              models.Todo.user_id == current_user.id,
          )
      )
      if todo is None: raise HTTPException(404, "todo not found")
      return todo
    """
    todo = db.scalar(
        select(models.Todo).where(
            models.Todo.id == todo_id,
            models.Todo.user_id == current_user.id,
        )
    )
    if todo is None:
        raise HTTPException(404, "todo not found")
    return todo


# ===== PATCH /todos/{todo_id} =====
@app.patch("/todos/{todo_id}", response_model=schemas.TodoRead)
def update_todo(
    todo_id: int,
    payload: schemas.TodoUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    部分更新，只能改自己的。

    同上先按 (id, user_id) 查出来 → 404 判断
    → model_dump(exclude_unset=True) → setattr → commit / refresh / return
    """
    todo = db.scalar(
        select(models.Todo).where(
            models.Todo.id == todo_id,
            models.Todo.user_id == current_user.id,
        )
    )
    if todo is None:
        raise HTTPException(404, "todo not found")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(todo, key, value)

    db.commit()
    db.refresh(todo)
    return todo


# ===== DELETE /todos/{todo_id} =====
@app.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(
    todo_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    删除，只能删自己的。

    同上先按 (id, user_id) 查 → 404 → db.delete → commit → return None
    """
    todo = db.scalar(
        select(models.Todo).where(
            models.Todo.id == todo_id,
            models.Todo.user_id == current_user.id,
        )
    )

    if todo is None:
        raise HTTPException(404, "todo not found")
    
    db.delete(todo)
    db.commit()
    return None


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

    def auth_header():
        return {"Authorization": f"Bearer {tokens['access_token']}"} if tokens else {}

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

    # ---------- Task 4B：认证保护 + 所有权 ----------
    other_username = f"other_{uuid4().hex[:8]}"
    other_id = None
    other_tokens = None
    my_todo_id = None
    other_todo_id = None

    def bearer(tok):
        return {"Authorization": f"Bearer {tok}"}

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
        print("🎉 全部通过！Task 4 main.py = ✅")
