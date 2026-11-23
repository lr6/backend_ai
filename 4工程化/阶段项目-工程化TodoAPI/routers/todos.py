"""
第四阶段 · 阶段项目 · Task 1C — routers/todos.py
Todo CRUD，每条都只能操作自己的数据（所有权 = 防 IDOR）

路径小知识：
  prefix="/todos" + @router.get("")        → GET  /todos
  prefix="/todos" + @router.get("/")       → GET  /todos/（多一个斜杠，会 307 跳转）
  prefix="/todos" + @router.get("/{id}")   → GET  /todos/{id}
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

import cache
import models
import schemas
from database import get_db
from deps import get_current_user

router = APIRouter(prefix="/todos", tags=["todos"])


def _get_owned_todo(todo_id: int, current_user: models.User, db: Session) -> models.Todo:
    """
    按 (id, user_id) 查一条 todo，查不到就直接 404。

    「不存在」和「是别人的」在这里合并成同一种结果：
    不告诉调用方（和攻击者）这条数据到底存不存在。
    """
    stmt = select(models.Todo).where(
        models.Todo.id == todo_id,
        models.Todo.user_id == current_user.id,
    )
    todo = db.scalar(stmt)
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="todo not found")
    return todo


# ===== POST /todos =====
@router.post("", response_model=schemas.TodoRead, status_code=status.HTTP_201_CREATED)
def create_todo(
    payload: schemas.TodoCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    user_id 来自 current_user，不是请求体（客户端传了也忽略）。
    步骤：models.Todo(title=payload.title, user_id=current_user.id)
          → add / commit / refresh / return
    """
    todo = models.Todo(
        title=payload.title,
        user_id=current_user.id,
    )
    db.add(todo)
    db.commit()
    db.refresh(todo)

    # 顺序：先 commit 再删缓存。新增一条 → 列表必然变了。
    cache.delete(cache.list_key(current_user.id))
    return todo


# ===== GET /todos =====
@router.get("", response_model=list[schemas.TodoRead])
def list_todos(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Task 2 · 列表读路径：
      命中缓存（含空列表 []）→ 直接 return
      CACHE_MISS → 查库 → 转成 list[dict] → 回填 → return

    注意判断用 `is not cache.CACHE_MISS`，不能用 `if cached:` ——
    空列表 [] 是合法结果，但它 falsy，会被误判成「没缓存」。
    """
    key = cache.list_key(current_user.id)
    cached = cache.get_json(key)
    if cached is not cache.CACHE_MISS:
        return cached

    stmt = select(models.Todo).where(models.Todo.user_id == current_user.id)
    todos = db.scalars(stmt).all()

    data = [schemas.TodoRead.model_validate(t).model_dump() for t in todos]
    cache.set_json(key, data)
    return data


# ===== GET /todos/{todo_id} =====
@router.get("/{todo_id}", response_model=schemas.TodoRead)
def get_todo(
    todo_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Task 2 · 读路径 Cache-Aside（三种返回值分别处理）：
      1. key = cache.todo_key(current_user.id, todo_id)
      2. cached = cache.get_json(key)
      3. CACHE_MISS（没缓存）→ 查库
           查到  → 转 dict → 回填缓存 → return dict
           查不到 → 写哨兵（set_json(key, None, ttl=cache.TTL_MISSING)）→ raise 404
      4. None（哨兵命中）→ raise 404，不查库
      5. dict → 直接 return

    查库步骤手写而不复用 _get_owned_todo：后者查不到就 raise，
    这里需要在「查不到」时先写哨兵。
    """
    key = cache.todo_key(current_user.id, todo_id)
    cached = cache.get_json(key)

    # ---- 命中缓存这条线：直接把结果交出去，不碰数据库 ----
    if cached is not cache.CACHE_MISS:
        if cached is None:
            # 哨兵命中：之前确认过「不存在」
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="todo not found")
        return cached

    # ---- 未命中：查库（id + user_id 一次完成「存在」和「归属」判断）----
    stmt = select(models.Todo).where(
        models.Todo.id == todo_id,
        models.Todo.user_id == current_user.id,
    )
    todo = db.scalar(stmt)

    if todo is None:
        # 确认不存在 → 写哨兵（过期后才会再查库），再 404
        cache.set_json(key, None, ttl=cache.TTL_MISSING)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="todo not found")

    # ORM 对象不能直接进 Redis，先转成 JSON 友好的 dict 再回填
    data = schemas.TodoRead.model_validate(todo).model_dump()
    cache.set_json(key, data)
    return data


# ===== PATCH /todos/{todo_id} =====
@router.patch("/{todo_id}", response_model=schemas.TodoRead)
def update_todo(
    todo_id: int,
    payload: schemas.TodoUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    同上先按 (models.Todo.id, models.Todo.user_id) 查 → 404
    → model_dump(exclude_unset=True) → setattr → commit / refresh / return
    """
    todo = _get_owned_todo(todo_id, current_user, db)
    data = payload.model_dump(exclude_unset=True)
    for key, val in data.items():
        setattr(todo, key, val)
    db.commit()
    db.refresh(todo)

    # 先 commit 再删：单条和列表都装过这条数据，一起删
    cache.delete(
        cache.todo_key(current_user.id, todo_id),
        cache.list_key(current_user.id),
    )
    return todo


# ===== DELETE /todos/{todo_id} =====
@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(
    todo_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    同上查 → 404 → db.delete(todo) → commit → return None
    """
    todo = _get_owned_todo(todo_id, current_user, db)
    db.delete(todo)
    db.commit()

    # 先 commit 再删：单条的 key 也要删掉（否则删了还能读到缓存副本）
    cache.delete(
        cache.todo_key(current_user.id, todo_id),
        cache.list_key(current_user.id),
    )
    return None
