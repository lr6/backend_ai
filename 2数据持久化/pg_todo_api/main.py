"""
第二阶段 · 阶段项目 · Task 4B — main.py
CRUD 路由（完整版：用户 + Todo）

请求链路：
    HTTP JSON → Pydantic 请求模型 → 路由函数 → Session → PostgreSQL
                                  ← Pydantic 响应模型 ←

已完成：用户与 Todo 的全部接口。

写完后运行: .venv/bin/python main.py
全部通过 = Task 4B 过关 ✅
"""

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db

app = FastAPI(title="Todo API")


# ===== 已完成：POST /users =====
@app.post("/users", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    user = models.User(**payload.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ===== 已完成：GET /users/{user_id} =====
@app.get("/users/{user_id}", response_model=schemas.UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return user


# ===== POST /todos =====
@app.post("/todos", response_model=schemas.TodoRead, status_code=status.HTTP_201_CREATED)
def create_todo(payload: schemas.TodoCreate, db: Session = Depends(get_db)):
    """
    创建 todo。

    步骤：
      1. 先确认 user 存在：db.get(models.User, payload.user_id)
         → 不存在就 raise HTTPException(404, "user not found")
      2. 和创建 user 一样：models.Todo(**payload.model_dump())
      3. add / commit / refresh
      4. return todo
    """
    user = db.get(models.User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    todo = models.Todo(**payload.model_dump())
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo



# ===== GET /todos =====
@app.get("/todos", response_model=list[schemas.TodoRead])
def list_todos(
    user_id: int | None = None,
    done: bool | None = None,
    db: Session = Depends(get_db),
):
    """
    列表查询，支持两个可选筛选参数：?user_id=1&done=false

    步骤：
      1. stmt = select(models.Todo)
      2. user_id 不是 None → stmt = stmt.where(models.Todo.user_id == user_id)
      3. done 不是 None → stmt = stmt.where(models.Todo.done == done)
      4. return db.scalars(stmt).all()
    """
    stmt = select(models.Todo)
    if user_id is not None:
        stmt = stmt.where(models.Todo.user_id == user_id)

    if done is not None:
        stmt = stmt.where(models.Todo.done == done)
    return db.scalars(stmt).all()


# ===== PATCH /todos/{todo_id} =====
@app.patch("/todos/{todo_id}", response_model=schemas.TodoRead)
def update_todo(todo_id: int, payload: schemas.TodoUpdate, db: Session = Depends(get_db)):
    """
    部分更新。

    步骤：
      1. todo = db.get(models.Todo, todo_id)
         → None 就 raise HTTPException(404, "todo not found")
      2. data = payload.model_dump(exclude_unset=True)
      3. for key, value in data.items(): setattr(todo, key, value)
      4. db.commit() → db.refresh(todo) → return todo
    """
    todo = db.get(models.Todo, todo_id)
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
def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    """
    删除 todo，成功返回 204（无响应体）。

    步骤：
      1. todo = db.get(models.Todo, todo_id)
         → None 就 raise HTTPException(404, "todo not found")
      2. db.delete(todo)
      3. db.commit()
      4. return None
    """
    todo = db.get(models.Todo, todo_id)
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
    username = f"test_{uuid4().hex[:8]}"
    user_id = None
    todo_id = None
    missing_user_id = 999999999

    def check(name, cond, detail=""):
        if cond:
            print(f"✅ {name}")
        else:
            errors.append(f"{name} {detail}")

    # ---------- 用户 ----------
    try:
        r = client.post("/users", json={"username": username, "email": "test@example.com"})
        check("POST /users 状态码 201", r.status_code == 201, f"实际 {r.status_code} {r.text}")
        body = r.json()
        check("返回 username 正确", body.get("username") == username, f"实际 {body.get('username')!r}")
        check("返回 id 是整数", isinstance(body.get("id"), int), f"实际 {body.get('id')!r}")
        check("返回 email 正确", body.get("email") == "test@example.com")
        user_id = body.get("id")
    except Exception as e:
        errors.append(f"POST /users 异常: {type(e).__name__}: {e}")

    if user_id is not None:
        try:
            r = client.get(f"/users/{user_id}")
            check("GET /users/{id} 状态码 200", r.status_code == 200, f"实际 {r.status_code} {r.text}")
            check("查询结果 username 正确", r.json().get("username") == username)
        except Exception as e:
            errors.append(f"GET /users/{{id}} 异常: {type(e).__name__}: {e}")

    try:
        r = client.get("/users/999999999")
        check("GET 不存在的用户返回 404", r.status_code == 404, f"实际 {r.status_code} {r.text}")
    except Exception as e:
        errors.append(f"404 测试异常: {type(e).__name__}: {e}")

    # ---------- Todo ----------
    # 测试 1：user 不存在时创建 todo → 404
    try:
        r = client.post("/todos", json={"title": "孤儿 todo", "user_id": missing_user_id})
        check("POST /todos 用户不存在 → 404", r.status_code == 404, f"实际 {r.status_code} {r.text}")
    except Exception as e:
        errors.append(f"POST /todos 404 测试异常: {type(e).__name__}: {e}")

    # 测试 2：正常创建 todo
    if user_id is not None:
        try:
            r = client.post("/todos", json={"title": "买牛奶", "user_id": user_id})
            check("POST /todos 状态码 201", r.status_code == 201, f"实际 {r.status_code} {r.text}")
            body = r.json()
            check("todo title 正确", body.get("title") == "买牛奶", f"实际 {body.get('title')!r}")
            check("todo done 默认 False", body.get("done") is False, f"实际 {body.get('done')!r}")
            check("todo user_id 正确", body.get("user_id") == user_id)
            todo_id = body.get("id")
        except Exception as e:
            errors.append(f"POST /todos 异常: {type(e).__name__}: {e}")

    # 测试 3：列表 + 筛选
    if user_id is not None and todo_id is not None:
        try:
            r = client.get("/todos", params={"user_id": user_id})
            check("GET /todos?user_id 状态码 200", r.status_code == 200, f"实际 {r.status_code} {r.text}")
            ids = [t.get("id") for t in r.json()]
            check("列表包含刚创建的 todo", todo_id in ids, f"实际 ids={ids}")

            r = client.get("/todos", params={"user_id": user_id, "done": "true"})
            check("done=true 筛选后不包含未完成的 todo", todo_id not in [t.get("id") for t in r.json()])
        except Exception as e:
            errors.append(f"GET /todos 异常: {type(e).__name__}: {e}")

    # 测试 4：PATCH 只改 done，title 保持不变
    if todo_id is not None:
        try:
            r = client.patch(f"/todos/{todo_id}", json={"done": True})
            check("PATCH /todos 状态码 200", r.status_code == 200, f"实际 {r.status_code} {r.text}")
            body = r.json()
            check("PATCH done 变为 True", body.get("done") is True, f"实际 {body.get('done')!r}")
            check("PATCH 未传的 title 保持不变", body.get("title") == "买牛奶", f"实际 {body.get('title')!r}")
        except Exception as e:
            errors.append(f"PATCH /todos 异常: {type(e).__name__}: {e}")

    # 测试 5：PATCH 只改 title，done 保持 True（验证 exclude_unset）
    if todo_id is not None:
        try:
            r = client.patch(f"/todos/{todo_id}", json={"title": "买酸奶"})
            body = r.json()
            check("PATCH title 更新", body.get("title") == "买酸奶", f"实际 {body.get('title')!r}")
            check("PATCH 未传的 done 保持 True", body.get("done") is True, f"实际 {body.get('done')!r}")
        except Exception as e:
            errors.append(f"PATCH title 异常: {type(e).__name__}: {e}")

    # 测试 6：DELETE → 204，再删一次 → 404
    if todo_id is not None:
        try:
            r = client.delete(f"/todos/{todo_id}")
            check("DELETE /todos 状态码 204", r.status_code == 204, f"实际 {r.status_code} {r.text}")
            r = client.delete(f"/todos/{todo_id}")
            check("再次 DELETE 返回 404", r.status_code == 404, f"实际 {r.status_code} {r.text}")
        except Exception as e:
            errors.append(f"DELETE /todos 异常: {type(e).__name__}: {e}")

    # ---------- 清理测试数据 ----------
    db = SessionLocal()
    try:
        if user_id is not None:
            db.execute(delete(models.Todo).where(models.Todo.user_id == user_id))
            db.execute(delete(models.User).where(models.User.id == user_id))
            db.commit()
    finally:
        db.close()

    print()
    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！Task 4B main.py = ✅")
