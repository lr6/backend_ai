"""
第四阶段 · 阶段项目 · Task 1C — deps.py
FastAPI 依赖：认人（从 token 里解出当前用户）

为什么单独一个 deps.py？
  - auth 路由不需要它，todos / users 路由都需要
  - 如果放 routers/auth.py 里，routers/todos.py 就得 import 另一个 router 模块
    → router 之间互相依赖，拆包就白拆了
  - deps.py 是谁都可以 import 的「公共层」

依赖方向：routers/* → deps.py → security.py / database.py / models.py
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

import models
import security
from database import get_db

# tokenUrl 指向登录接口，Swagger 的 Authorize 按钮会用到
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# TODO 1：统一造 401
#   学习项 12 的老朋友：401 必须带 WWW-Authenticate: Bearer
#   返回（不是 raise）一个 HTTPException，用它的地方再 raise
def auth_error(detail: str = "invalid credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


# TODO 2：从 Authorization: Bearer <token> 解析出当前用户
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """
    Depends 链：oauth2_scheme 取出 token → 这里验 token → 查库 → 返回 User

    步骤（第三阶段写过，这次全靠记忆）：
      1. try: claims = security.decode_token(token, "access")
         except JWTError: raise auth_error("invalid token")
         —— 第二个参数是 "access"：refresh token 不能访问业务接口
      2. user = db.get(models.User, claims["user_id"])
         → None 就 raise auth_error("invalid token")
      3. return user
    """
    try:
        claims = security.decode_token(token, "access")
        user = db.get(models.User, claims["user_id"])
        if user is None:
            raise auth_error("invalid token")
        return user
    except JWTError:
        raise auth_error("invalid token")
