"""
第四阶段 · 阶段项目 · Task 1C — routers/auth.py
认证路由：注册 / 登录 / 刷新

和第三阶段相比，函数体几乎一样，变的是「挂在哪」：
  @app.post("/auth/register")   →   @router.post("/register") + prefix="/auth"

依赖方向：routers/auth.py → deps.py / security.py / schemas.py / models.py
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

import models
import schemas
import security
from database import get_db
from deps import auth_error

# TODO 1：创建 router
#   prefix="/auth"、tags=["auth"]
router = APIRouter(prefix="/auth", tags=["auth"])


# ===== POST /auth/register =====
# 注意路径只写 "/register" —— prefix 已经拼在前面
# TODO 2：实现注册（第三阶段写过）
@router.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    步骤：
      1. 查重：select(models.User).where(models.User.username == payload.username)
         → 有结果就 raise HTTPException(409, "username already taken")
      2. 造 User：username / email / password_hash（用 security.hash_password）
         ⚠️ 不能把 payload.model_dump() 整个塞进去，里面有明文 password
      3. db.add / db.commit / db.refresh / return
    """
    u = db.scalar(select(models.User).where(models.User.username == payload.username))
    if u is None:
        user = models.User(
            username = payload.username,
            email = payload.email,
            password_hash = security.hash_password(payload.password)
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    raise HTTPException(409, "username already taken")


# ===== POST /auth/login =====
# TODO 3：实现登录
@router.post("/login", response_model=schemas.TokenPair)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    OAuth2 password flow：收 form，不收 JSON。

    步骤：
      1. 按 username 查用户
      2. 用户不存在 或 verify_password 失败 → raise auth_error()
         （两种失败同一个提示，别告诉攻击者用户名是否存在）
      3. 成功 → return schemas.TokenPair(
             access_token=security.create_access_token(user.id),
             refresh_token=security.create_refresh_token(user.id),
         )
    """
    user = db.scalar(select(models.User).where(models.User.username == form.username))
    if user is None or not security.verify_password(form.password, user.password_hash):
        raise auth_error()
    return schemas.TokenPair(
        access_token=security.create_access_token(user.id),
        refresh_token=security.create_refresh_token(user.id)
    )

# ===== POST /auth/refresh =====
# TODO 4：实现刷新
@router.post("/refresh", response_model=schemas.TokenPair)
def refresh(payload: schemas.RefreshRequest, db: Session = Depends(get_db)):
    """
    步骤：
      1. try: claims = security.decode_token(payload.refresh_token, "refresh")
         except JWTError: raise auth_error("invalid refresh token")
      2. user = db.get(models.User, claims["user_id"]) → None 也 401
      3. 返回新的 TokenPair（access + refresh 都重签）
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
