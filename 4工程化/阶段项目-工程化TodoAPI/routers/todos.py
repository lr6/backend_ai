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

import models
import schemas
from database import get_db
from deps import get_current_user

# TODO 1：创建 router
#   prefix="/todos"、tags=["todos"]
#   可选：dependencies=[Depends(get_current_user)] 作为整组路由的默认门禁
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
# TODO 2：创建
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
    return todo


# ===== GET /todos =====
# TODO 3：列表（只返回自己的）
@router.get("", response_model=list[schemas.TodoRead])
def list_todos(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    stmt = select(models.Todo).where(models.Todo.user_id == current_user.id)
    return db.scalars(stmt).all()
    """
    stmt = select(models.Todo).where(models.Todo.user_id == current_user.id)
    return db.scalars(stmt).all()


# ===== GET /todos/{todo_id} =====
# TODO 4：查单条（只查自己的）
@router.get("/{todo_id}", response_model=schemas.TodoRead)
def get_todo(
    todo_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    一次查询同时完成「存在」和「归属」判断：
      select(models.Todo).where(models.Todo.id == todo_id,
                                models.Todo.user_id == current_user.id)
      → 查不到就 raise HTTPException(404, "todo not found")
    注意：裸 id 是内置函数，裸 user_id 是 NameError —— 列必须写成 models.Todo.xxx
    别人的 todo 也是 404（不是 403，别泄露"存在但无权"）
    """
    return _get_owned_todo(todo_id, current_user, db)


# ===== PATCH /todos/{todo_id} =====
# TODO 5：部分更新（只能改自己的）
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
    return todo

# ===== DELETE /todos/{todo_id} =====
# TODO 6：删除（只能删自己的）
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
    return None
