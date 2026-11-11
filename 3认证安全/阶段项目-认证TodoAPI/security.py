"""
第三阶段 · 阶段项目 · Task 2 — security.py
密码哈希 + JWT 签发/校验

这个文件是「纯函数层」：不碰数据库、不碰 FastAPI。
main.py 里的注册/登录/get_current_user 都会调用这里。

写完后运行: ../../.venv/bin/python security.py
全部通过 = Task 2 过关 ✅
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

# ⚠️ 演示用。生产环境应从环境变量读取，绝不能硬编码进 git
SECRET_KEY = "dev-only-secret-change-me"
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30

# 学习项 13 用过的写法：bcrypt + 支持后续迁移算法
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ===== 密码 =====
def hash_password(password: str) -> str:
    """
    把明文密码变成 bcrypt 哈希串（入库用）。

    hash_password("123456") -> "$2b$12$..."（每次调用结果都不同，因为盐随机）
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """
    校验明文密码和库里的哈希是否匹配（登录用）。

    verify_password("123456", hash_password("123456")) -> True
    verify_password("wrong",  hash_password("123456")) -> False
    """
    return pwd_context.verify(plain_password, password_hash)


# ===== JWT =====
def create_access_token(user_id: int, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    """
    签发 access token。

    payload 必须包含：
        user_id : int
        type    : "access"
        exp     : 当前 UTC 时间 + expires_minutes 分钟

    expires_minutes 传负数可以造一个已过期的 token（测试用）。
    """
    payload = {
        "user_id": user_id,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int, expires_days: int = REFRESH_TOKEN_EXPIRE_DAYS) -> str:
    """
    签发 refresh token。

    payload 必须包含：
        user_id : int
        type    : "refresh"
        exp     : 当前 UTC 时间 + expires_days 天
    """
    payload = {
        "user_id": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=expires_days)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str) -> dict:
    """
    验签 + 校验过期 + 校验 token 类型，返回 payload。

    规则：
      1. 签名不对 / 格式乱 / 已过期  → 让 jose 的异常往外抛（JWTError / ExpiredSignatureError）
      2. payload["type"] != expected_type → 抛 JWTError("invalid token type")
      3. 全部通过 → 返回 payload（dict）

    decode_token(create_access_token(1), "access")   -> {"user_id": 1, ...}
    decode_token(create_access_token(1), "refresh")  -> JWTError
    """
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("type") != expected_type:
        raise JWTError("无效 token")
    return payload

# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    from jose import ExpiredSignatureError

    errors = []

    def check(name, fn):
        try:
            fn()
            print(f"✅ {name}")
        except AssertionError as e:
            errors.append(f"{name}: {e}")
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}: {e}")

    # ---------- 密码 ----------
    def t_hash_basic():
        h = hash_password("123456")
        assert isinstance(h, str), f"应返回 str，实际 {type(h).__name__}"
        assert h != "123456", "返回值不能是明文"
        assert h.startswith("$2"), f"应为 bcrypt 哈希串，实际开头 {h[:8]!r}"

    def t_verify_ok():
        h = hash_password("123456")
        assert verify_password("123456", h) is True, "正确密码应返回 True"

    def t_verify_wrong():
        h = hash_password("123456")
        assert verify_password("wrong", h) is False, "错误密码应返回 False"

    def t_salt_random():
        a, b = hash_password("123456"), hash_password("123456")
        assert a != b, "同样的密码两次哈希应该不同（随机盐）"

    # ---------- access token ----------
    def t_access_claims():
        token = create_access_token(42)
        payload = decode_token(token, "access")
        assert payload["user_id"] == 42, f"user_id 期望 42，实际 {payload.get('user_id')!r}"
        assert payload["type"] == "access", f"type 期望 access，实际 {payload.get('type')!r}"
        exp = payload["exp"]
        if isinstance(exp, datetime):
            exp = exp.timestamp()
        diff = abs(exp - (datetime.now(timezone.utc).timestamp() + 15 * 60))
        assert diff < 60, f"exp 应在 15 分钟后，偏差 {diff:.0f} 秒"

    def t_access_not_refresh():
        token = create_access_token(1)
        try:
            decode_token(token, "refresh")
        except JWTError:
            return
        raise AssertionError("access 当作 refresh 用应该抛 JWTError")

    # ---------- refresh token ----------
    def t_refresh_claims():
        token = create_refresh_token(7)
        payload = decode_token(token, "refresh")
        assert payload["user_id"] == 7, f"user_id 期望 7，实际 {payload.get('user_id')!r}"
        assert payload["type"] == "refresh", f"type 期望 refresh，实际 {payload.get('type')!r}"
        exp = payload["exp"]
        if isinstance(exp, datetime):
            exp = exp.timestamp()
        diff = abs(exp - (datetime.now(timezone.utc).timestamp() + 30 * 86400))
        assert diff < 60, f"exp 应在 30 天后，偏差 {diff:.0f} 秒"

    def t_refresh_not_access():
        token = create_refresh_token(1)
        try:
            decode_token(token, "access")
        except JWTError:
            return
        raise AssertionError("refresh 当作 access 用应该抛 JWTError")

    # ---------- 过期 / 篡改 ----------
    def t_expired():
        token = create_access_token(1, expires_minutes=-1)
        try:
            decode_token(token, "access")
        except ExpiredSignatureError:
            return
        raise AssertionError("过期 token 应该抛 ExpiredSignatureError")

    def t_tampered():
        token = create_access_token(1)
        header, payload, sig = token.split(".")
        forged = header + "." + payload + "." + ("A" * len(sig))
        try:
            decode_token(forged, "access")
        except JWTError:
            return
        raise AssertionError("签名被篡改应该抛 JWTError")

    def t_garbage():
        try:
            decode_token("not-a-token", "access")
        except JWTError:
            return
        raise AssertionError("乱码应该抛 JWTError")

    check("hash_password 返回 bcrypt 串", t_hash_basic)
    check("正确密码 verify → True", t_verify_ok)
    check("错误密码 verify → False", t_verify_wrong)
    check("同密码两次哈希不同（随机盐）", t_salt_random)
    check("access token 的 user_id / type / exp", t_access_claims)
    check("access 不能当 refresh", t_access_not_refresh)
    check("refresh token 的 user_id / type / exp", t_refresh_claims)
    check("refresh 不能当 access", t_refresh_not_access)
    check("过期 token 抛 ExpiredSignatureError", t_expired)
    check("篡改签名抛 JWTError", t_tampered)
    check("乱码抛 JWTError", t_garbage)

    print()
    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！Task 2 security.py = ✅")
