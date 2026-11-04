"""
第三阶段 · 11 JWT — 检验练习

每个函数的 TODO 需要你来实现。
写完后运行: .venv/bin/python practice.py
全部通过 = 11 JWT 过关 ✅

依赖: python-jose[cryptography]（已安装）
"""

from datetime import datetime, timedelta, timezone
import base64

from jose import jwt, JWTError, ExpiredSignatureError

SECRET_KEY = "practice-secret-change-me"
ALGORITHM = "HS256"


# ===== 练习 1：签发 access token =====
def create_access_token(user_id: int, role: str, expires_minutes: int = 15) -> str:
    """
    签发一个 access token。payload 至少包含：
        user_id、role、type="access"、exp

    提示：exp 用 datetime.now(timezone.utc) + timedelta(minutes=...)
         拒绝过期可以用负数，比如 expires_minutes=-1

    例如:
        create_access_token(1, "user") -> "eyJhbGci...eyJ1c2Vy...xxx"（三段，两个点）
    """
    payload = {
        "user_id": user_id,
        "role": role,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ===== 练习 2：验证并解析 token =====
def decode_token(token: str) -> dict:
    """
    校验签名和过期时间，返回 payload（dict）。

    行为要求：
        - token 合法        -> 返回 payload
        - 被篡改 / 签名错误 -> 抛出 JWTError
        - 已过期            -> 抛出 ExpiredSignatureError

    例如:
        decode_token(create_access_token(1, "user")) -> {"user_id": 1, "role": "user", ...}
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# ===== 练习 3：签发 refresh token 和 token 对 =====
def create_refresh_token(user_id: int, role: str, expires_days: int = 30) -> str:
    """
    签发一个 refresh token。payload 至少包含：
        user_id、role、type="refresh"、exp（以天为单位）

    例如:
        create_refresh_token(1, "user") -> "eyJhbGci...eyJyZWZy...xxx"
    """
    payload = {
        "user_id": user_id,
        "type": "refresh",
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(days=expires_days)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_token_pair(user_id: int, role: str) -> dict:
    """
    登录成功后同时签发两个 token。

    返回:
        {"access_token": "...", "refresh_token": "..."}

    例如:
        create_token_pair(7, "admin") -> {"access_token": "eyJ...", "refresh_token": "eyJ..."}
    """
    return {
        "access_token": create_access_token(user_id, role),
        "refresh_token": create_refresh_token(user_id, role)
    }


# ===== 练习 4：校验 token 类型 =====
def verify_token_type(token: str, expected_type: str) -> dict:
    """
    先验证 token（签名 + 过期），再检查 payload["type"] 是否等于 expected_type。

    行为要求：
        - 类型匹配   -> 返回 payload
        - 类型不匹配 -> 抛出 JWTError

    为什么需要这个？防止有人拿 refresh token 冒充 access token 访问业务接口。

    例如:
        verify_token_type(pair["access_token"], "access")  -> payload
        verify_token_type(pair["refresh_token"], "access") -> JWTError
    """
    payload = decode_token(token)
    if payload["type"] != expected_type:
        raise JWTError("token 类型不匹配")
    return payload


# ===== 练习 5：用 refresh token 换新 access token =====
def refresh_access_token(store: dict, user_id: int, refresh_token: str) -> str:
    """
    store 模拟服务端存储的 refresh token 记录，形如 {user_id: refresh_token}。

    流程：
        1. 验证 refresh_token（签名 + 过期 + 类型必须是 "refresh"）
        2. 检查 store.get(user_id) 是否等于这个 refresh_token
           —— 不相等说明已被登出/吊销，抛 ValueError
        3. 全部通过 -> 返回一张新的 access token（沿用 token 里的 role）

    例如:
        refresh_access_token({1: rt}, 1, rt) -> "eyJ..."（新的 access token）
    """
    payload = verify_token_type(refresh_token, "refresh")
    if store.get(user_id) != refresh_token:
        raise ValueError("refresh token 已失效或已被吊销")
    return create_access_token(user_id, payload["role"])



# ===== 练习 6：吊销 refresh token（登出）=====
def revoke_refresh_token(store: dict, user_id: int) -> None:
    """
    登出：从 store 中删除该用户的 refresh token 记录。
    记录不存在时也不报错。

    例如:
        store = {1: "xxx"}; revoke_refresh_token(store, 1) -> store == {}
    """
    store.pop(user_id, None)    


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    errors = []

    # ---------- 练习 1 ----------
    try:
        token = create_access_token(1, "user")
        if not isinstance(token, str):
            errors.append(f"练习1: 期望返回 str，实际 {type(token).__name__}")
        elif token.count(".") != 2:
            errors.append(f"练习1: 期望三段用两个点连接，实际 {token!r}")
    except Exception as e:
        errors.append(f"练习1: 运行出错 {type(e).__name__}: {e}")

    # ---------- 练习 2 ----------
    try:
        claims = decode_token(create_access_token(1, "user"))
        if not isinstance(claims, dict):
            errors.append(f"练习2: 期望返回 dict，实际 {type(claims).__name__}")
        elif claims.get("user_id") != 1 or claims.get("role") != "user":
            errors.append(f"练习2: payload 内容不对，实际 {claims}")
    except Exception as e:
        errors.append(f"练习2(合法 token): 不应该抛异常，实际 {type(e).__name__}: {e}")

    try:
        decode_token(create_access_token(1, "user", expires_minutes=-1))
        errors.append("练习2(过期 token): 期望抛 ExpiredSignatureError，实际没抛")
    except ExpiredSignatureError:
        pass
    except Exception as e:
        errors.append(f"练习2(过期 token): 期望 ExpiredSignatureError，实际 {type(e).__name__}: {e}")

    try:
        good = create_access_token(1, "user")
        header, _payload, sig = good.split(".")
        fake = base64.urlsafe_b64encode(
            b'{"user_id": 2, "role": "admin", "type": "access"}'
        ).rstrip(b"=").decode()
        decode_token(f"{header}.{fake}.{sig}")
        errors.append("练习2(篡改 token): 期望抛 JWTError，实际没抛")
    except JWTError:
        pass
    except Exception as e:
        errors.append(f"练习2(篡改 token): 期望 JWTError，实际 {type(e).__name__}: {e}")

    # ---------- 练习 3 ----------
    try:
        rt = create_refresh_token(1, "user")
        rt_claims = decode_token(rt)
        if rt_claims.get("type") != "refresh":
            errors.append(f"练习3(refresh): 期望 type='refresh'，实际 {rt_claims.get('type')!r}")
        if rt_claims.get("user_id") != 1:
            errors.append(f"练习3(refresh): user_id 应为 1，实际 {rt_claims.get('user_id')!r}")
    except Exception as e:
        errors.append(f"练习3(refresh): 运行出错 {type(e).__name__}: {e}")

    try:
        pair = create_token_pair(7, "admin")
        if not isinstance(pair, dict) or "access_token" not in pair or "refresh_token" not in pair:
            errors.append(f"练习3(pair): 期望含 access_token/refresh_token 的 dict，实际 {pair!r}")
        else:
            ac = decode_token(pair["access_token"])
            rc = decode_token(pair["refresh_token"])
            if ac.get("type") != "access" or rc.get("type") != "refresh":
                errors.append(
                    f"练习3(pair): 类型不对，access={ac.get('type')!r} refresh={rc.get('type')!r}"
                )
    except Exception as e:
        errors.append(f"练习3(pair): 运行出错 {type(e).__name__}: {e}")

    # ---------- 练习 4 ----------
    try:
        pair = create_token_pair(7, "admin")
        payload = verify_token_type(pair["access_token"], "access")
        if payload.get("user_id") != 7:
            errors.append(f"练习4(匹配): 期望返回 payload，实际 {payload!r}")
    except Exception as e:
        errors.append(f"练习4(匹配): 不应该抛异常，实际 {type(e).__name__}: {e}")

    try:
        pair = create_token_pair(7, "admin")
        verify_token_type(pair["refresh_token"], "access")
        errors.append("练习4(不匹配): 期望抛 JWTError，实际没抛")
    except JWTError:
        pass
    except Exception as e:
        errors.append(f"练习4(不匹配): 期望 JWTError，实际 {type(e).__name__}: {e}")

    # ---------- 练习 5 ----------
    try:
        rt = create_refresh_token(3, "user")
        new_access = refresh_access_token({3: rt}, 3, rt)
        new_claims = decode_token(new_access)
        if new_claims.get("type") != "access":
            errors.append(f"练习5(换新): 期望新 token type='access'，实际 {new_claims.get('type')!r}")
        if new_claims.get("user_id") != 3 or new_claims.get("role") != "user":
            errors.append(f"练习5(换新): 新 token 信息不对，实际 {new_claims}")
    except Exception as e:
        errors.append(f"练习5(换新): 不应该抛异常，实际 {type(e).__name__}: {e}")

    try:
        rt = create_refresh_token(3, "user")
        refresh_access_token({}, 3, rt)
        errors.append("练习5(已吊销): 期望抛 ValueError，实际没抛")
    except ValueError:
        pass
    except Exception as e:
        errors.append(f"练习5(已吊销): 期望 ValueError，实际 {type(e).__name__}: {e}")

    # ---------- 练习 6 ----------
    try:
        store = {1: "token-a"}
        revoke_refresh_token(store, 1)
        if 1 in store:
            errors.append(f"练习6: 期望删除记录后 store 为空，实际 {store!r}")
    except Exception as e:
        errors.append(f"练习6(删除): 运行出错 {type(e).__name__}: {e}")

    try:
        revoke_refresh_token({}, 1)
    except Exception as e:
        errors.append(f"练习6(不存在的记录): 不应该报错，实际 {type(e).__name__}: {e}")

    # ---------- 汇总 ----------
    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！11 JWT = ✅")
