"""
第三阶段 · 12 FastAPI OAuth2 — 检验练习

每个函数的 TODO 需要你来实现。
写完后运行: .venv/bin/python practice.py
全部通过 = 12 FastAPI OAuth2 过关 ✅

依赖: fastapi、python-jose、httpx（均已安装）

说明：
- USERS_DB 是练习用的内存「数据库」，密码存明文只是为了聚焦 OAuth2；
  真实项目用 13 学过的 passlib/bcrypt 做哈希校验。
- create_access_token / create_refresh_token 已替你写好（11 JWT 的内容）。
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.testclient import TestClient
from jose import JWTError, jwt
from pydantic import BaseModel

SECRET_KEY = "practice-secret-change-me"
ALGORITHM = "HS256"

# 模拟数据库：id -> 用户
USERS_DB = {
    1: {"id": 1, "username": "alice", "password": "alice123", "role": "user"},
    2: {"id": 2, "username": "bob", "password": "bob123", "role": "admin"},
}

app = FastAPI()

# FastAPI 的 OAuth2 依赖：自动从 Authorization: Bearer xxx 里取出 xxx
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def get_db():
    """模拟数据库 Session 依赖。"""
    return USERS_DB


def create_access_token(user_id: int, role: str = "user", expires_minutes: int = 15) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int, role: str = "user", expires_days: int = 30) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=expires_days),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def auth_error(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )

# ===== 练习 1：登录接口 =====
@app.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: dict = Depends(get_db)):
    """
    用户名密码登录，成功返回 access token。

    要求：
        1. 按 form.username 在 db 里找用户（遍历 db.values()）
        2. 用户不存在 / 密码不一致 -> raise HTTPException(401, "用户名或密码错误")
        3. 成功 -> {"access_token": create_access_token(用户id, 用户role),
                   "token_type": "bearer"}

    例如:
        POST /login (form: username=alice&password=alice123)
        -> {"access_token": "eyJ...", "token_type": "bearer"}
    """
    user = None
    for u in db.values():
        if u["username"] == form.username:
            user = u
            break
    
    if user is None or user["password"] != form.password:
        raise auth_error("用户名或密码错误")
    return {"access_token": create_access_token(user["id"], user["role"]), "token_type": "bearer"}

# ===== 练习 2：get_current_user 依赖 =====
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: dict = Depends(get_db),
) -> dict:
    """
    把 token 换成当前用户对象。

    要求：
        1. jwt.decode 验签 + 验过期；JWTError -> 401
        2. payload["type"] 必须是 "access"，否则 -> 401
        3. 按 payload["user_id"] 查 db；用户不存在 -> 401
        4. 全部通过 -> 返回用户 dict

    401 统一这样构造：
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    例如:
        get_current_user(token=create_access_token(1), db=USERS_DB)
        -> {"id": 1, "username": "alice", ...}
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise auth_error() from None

    if payload.get("type") != "access":
        raise auth_error()

    u_id = payload.get("user_id")
    user = db.get(u_id)

    if user is None:
        raise auth_error()
    return user


# ===== 练习 3：受保护的路由 =====
@app.get("/me")
def read_me(current_user: dict = Depends(get_current_user)):
    """
    返回当前登录用户的信息（不含密码）。

    要求：返回 {"id": ..., "username": ..., "role": ...}

    例如:
        GET /me (Authorization: Bearer <access>)
        -> {"id": 1, "username": "alice", "role": "user"}
    """
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "role": current_user["role"]
    }


@app.get("/health")
def health():
    """公开接口，不需要登录。"""
    return {"status": "ok"}


# ===== 练习 4：Router 级依赖 =====
# TODO: 给整个 admin_router 挂上 get_current_user 依赖，
#       让 /admin/* 下所有路由自动要求登录，不用逐个写 Depends。
#       提示：APIRouter(prefix="/admin", dependencies=[Depends(...)])
# admin_router = APIRouter(prefix="/admin")
admin_router = APIRouter(
    prefix="/admin",
    dependencies=[Depends(get_current_user)]
)

@admin_router.get("/dashboard")
def admin_dashboard():
    return {"secret": "只有登录用户能看到"}


app.include_router(admin_router)


# ===== 练习 5：用 refresh token 换新 access token =====
class RefreshRequest(BaseModel):
    refresh_token: str


@app.post("/refresh")
def refresh_access_token(body: RefreshRequest, db: dict = Depends(get_db)):
    """
    用 refresh token 换一张新的 access token。

    要求：
        1. jwt.decode 验签 + 验过期；失败 -> 401（同练习 2 的构造方式）
        2. payload["type"] 必须是 "refresh"，否则 -> 401
        3. 用户不存在 -> 401
        4. 成功 -> {"access_token": create_access_token(user_id, role),
                   "token_type": "bearer"}

    例如:
        POST /refresh {"refresh_token": "<refresh>"}
        -> {"access_token": "eyJ...", "token_type": "bearer"}
    """
    try:
        payload = jwt.decode(body.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise auth_error() from None

    if payload.get("type") != "refresh":
        raise auth_error()

    user = db.get(payload.get("user_id"))
    if user is None:
        raise auth_error()
    return {"access_token": create_access_token(user["id"], user["role"]), "token_type": "bearer"}


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    errors = []
    client = TestClient(app)

    # ---------- 练习 1 ----------
    try:
        r = client.post("/login", data={"username": "alice", "password": "alice123"})
        if r.status_code != 200:
            errors.append(f"练习1(正确密码): 期望 200，实际 {r.status_code} {r.text}")
        else:
            body = r.json()
            if not isinstance(body.get("access_token"), str):
                errors.append(f"练习1(正确密码): 响应缺少 access_token，实际 {body}")
            elif body.get("token_type") != "bearer":
                errors.append(
                    f"练习1(正确密码): token_type 应为 'bearer'，实际 {body.get('token_type')!r}"
                )
            else:
                claims = jwt.decode(body["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
                if (claims.get("user_id") != 1
                        or claims.get("role") != "user"
                        or claims.get("type") != "access"):
                    errors.append(f"练习1(正确密码): token 内容不对，实际 {claims}")
    except Exception as e:
        errors.append(f"练习1(正确密码): 运行出错 {type(e).__name__}: {e}")

    try:
        r = client.post("/login", data={"username": "alice", "password": "wrong"})
        if r.status_code != 401:
            errors.append(f"练习1(密码错误): 期望 401，实际 {r.status_code}")
    except Exception as e:
        errors.append(f"练习1(密码错误): 运行出错 {type(e).__name__}: {e}")

    try:
        r = client.post("/login", data={"username": "nobody", "password": "x"})
        if r.status_code != 401:
            errors.append(f"练习1(用户不存在): 期望 401，实际 {r.status_code}")
    except Exception as e:
        errors.append(f"练习1(用户不存在): 运行出错 {type(e).__name__}: {e}")

    try:
        r = client.post("/login", json={"username": "alice", "password": "alice123"})
        if r.status_code != 422:
            errors.append(
                f"练习1(JSON 请求): 期望 422（表单依赖只收 form），实际 {r.status_code}"
            )
    except Exception as e:
        errors.append(f"练习1(JSON 请求): 运行出错 {type(e).__name__}: {e}")

    # ---------- 练习 2 ----------
    try:
        user = get_current_user(token=create_access_token(1, "user"), db=USERS_DB)
        if not isinstance(user, dict) or user.get("username") != "alice":
            errors.append(f"练习2(合法 token): 期望返回 alice 用户，实际 {user!r}")
    except Exception as e:
        errors.append(f"练习2(合法 token): 不应该抛异常，实际 {type(e).__name__}: {e}")

    bad_cases = [
        ("过期 access", create_access_token(1, expires_minutes=-1)),
        ("乱码", "not-a-jwt"),
        ("refresh 冒充 access", create_refresh_token(1)),
        ("用户不存在", create_access_token(999)),
    ]
    for label, bad_token in bad_cases:
        try:
            get_current_user(token=bad_token, db=USERS_DB)
            errors.append(f"练习2({label}): 期望抛 HTTPException 401，实际没抛")
        except HTTPException as e:
            if e.status_code != 401:
                errors.append(f"练习2({label}): 期望 401，实际 {e.status_code}")
            elif (e.headers or {}).get("WWW-Authenticate") != "Bearer":
                errors.append(
                    f"练习2({label}): 401 应带 WWW-Authenticate: Bearer，实际 {e.headers}"
                )
        except Exception as e:
            errors.append(f"练习2({label}): 期望 HTTPException，实际 {type(e).__name__}: {e}")

    # ---------- 练习 3 ----------
    valid = create_access_token(1, "user")
    try:
        r = client.get("/me")
        if r.status_code != 401:
            errors.append(f"练习3(不带 token): 期望 401，实际 {r.status_code}")
    except Exception as e:
        errors.append(f"练习3(不带 token): 运行出错 {type(e).__name__}: {e}")

    try:
        r = client.get("/me", headers={"Authorization": f"Bearer {valid}"})
        if r.status_code != 200:
            errors.append(f"练习3(带 token): 期望 200，实际 {r.status_code} {r.text}")
        else:
            expected = {"id": 1, "username": "alice", "role": "user"}
            if r.json() != expected:
                errors.append(f"练习3(带 token): 期望 {expected}，实际 {r.json()}")
    except Exception as e:
        errors.append(f"练习3(带 token): 运行出错 {type(e).__name__}: {e}")

    try:
        r = client.get("/health")
        if r.status_code != 200:
            errors.append(f"练习3(公开接口): 期望 200，实际 {r.status_code}")
    except Exception as e:
        errors.append(f"练习3(公开接口): 运行出错 {type(e).__name__}: {e}")

    # ---------- 练习 4 ----------
    try:
        r = client.get("/admin/dashboard")
        if r.status_code != 401:
            errors.append(f"练习4(不带 token): 期望 401（router 级依赖），实际 {r.status_code}")
    except Exception as e:
        errors.append(f"练习4(不带 token): 运行出错 {type(e).__name__}: {e}")

    try:
        r = client.get("/admin/dashboard", headers={"Authorization": f"Bearer {valid}"})
        if r.status_code != 200:
            errors.append(f"练习4(带 token): 期望 200，实际 {r.status_code} {r.text}")
    except Exception as e:
        errors.append(f"练习4(带 token): 运行出错 {type(e).__name__}: {e}")

    # ---------- 练习 5 ----------
    try:
        rt = create_refresh_token(1, "user")
        r = client.post("/refresh", json={"refresh_token": rt})
        if r.status_code != 200:
            errors.append(f"练习5(合法 refresh): 期望 200，实际 {r.status_code} {r.text}")
        else:
            body = r.json()
            if not isinstance(body.get("access_token"), str):
                errors.append(f"练习5(合法 refresh): 响应缺少 access_token，实际 {body}")
            elif body.get("token_type") != "bearer":
                errors.append(
                    f"练习5(合法 refresh): token_type 应为 'bearer'，实际 {body.get('token_type')!r}"
                )
            else:
                claims = jwt.decode(body["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
                if (claims.get("user_id") != 1
                        or claims.get("role") != "user"
                        or claims.get("type") != "access"):
                    errors.append(f"练习5(合法 refresh): 新 token 内容不对，实际 {claims}")
    except Exception as e:
        errors.append(f"练习5(合法 refresh): 运行出错 {type(e).__name__}: {e}")

    try:
        r = client.post("/refresh", json={"refresh_token": create_access_token(1)})
        if r.status_code != 401:
            errors.append(f"练习5(access 冒充 refresh): 期望 401，实际 {r.status_code}")
    except Exception as e:
        errors.append(f"练习5(access 冒充 refresh): 运行出错 {type(e).__name__}: {e}")

    try:
        r = client.post("/refresh", json={"refresh_token": "garbage"})
        if r.status_code != 401:
            errors.append(f"练习5(乱码): 期望 401，实际 {r.status_code}")
    except Exception as e:
        errors.append(f"练习5(乱码): 运行出错 {type(e).__name__}: {e}")

    # ---------- 汇总 ----------
    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！12 FastAPI OAuth2 = ✅")
