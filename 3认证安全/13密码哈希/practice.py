"""
第三阶段 · 13 passlib + bcrypt — 密码哈希与加盐 检验练习

每个函数的 TODO 需要你来实现。
写完后运行: .venv/bin/python "3认证安全/13密码哈希/practice.py"
全部通过 = 13 过关 ✅
"""

from passlib.context import CryptContext

# bcrypt 上下文：默认工作因子 12
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ===== 练习 1：生成密码哈希 =====
def hash_password(password: str) -> str:
    """
    用 bcrypt 生成密码哈希字符串。

    要求:
    - 返回以 "$2b$" 开头的字符串
    - 不含密码明文
    - 同一个密码调用两次，结果必须不同（盐是随机的）

    例如: hash_password("123456") → "$2b$12$...."
    """
    return pwd_context.hash(password)


# ===== 练习 2：验证密码 =====
def verify_password(password: str, hashed: str) -> bool:
    """
    验证明文密码和数据库里的哈希是否匹配。

    注意: 不能重新 hash 后比较字符串（盐每次不同），要从哈希里取盐重算。

    例如: verify_password("123456", hashed) → True
          verify_password("wrong",  hashed) → False
    """
    # TODO
    return pwd_context.verify(password, hashed)


# ===== 练习 3：解析 bcrypt 哈希结构 =====
def parse_bcrypt_hash(hashed: str) -> dict:
    """
    把 bcrypt 哈希拆成各字段，返回 dict。

    bcrypt 格式: $<版本>$<cost>$<22位盐><31位摘要>
    例如: "$2b$12$.L39Cv3UcVlYyHCR/VvAleqFTlmeHEf5KKqd/ZX9rQ20g84s/pKL6"
        → {
            "version": "2b",          # 算法版本
            "cost": 12,               # 工作因子（int）
            "salt": ".L39Cv3UcVlYyHCR/VvAle",   # 前 22 个字符
            "digest": "qFTlmeHEf5KKqd/ZX9rQ20g84s/pKL6",  # 后面 31 个字符
          }

    提示: 用 hashed.split("$") 拆开看每一段是什么。
    """
    parts = hashed.split("$")
    last = parts[3]
    return {
        "version": parts[1],
        "cost": int(parts[2]),
        "salt": last[:22],
        "digest": last[22:]
    }


# ===== 练习 4：指定工作因子（cost） =====
def hash_with_cost(password: str, cost: int) -> str:
    """
    生成指定工作因子的 bcrypt 哈希。

    要求: cost=4 时返回值以 "$2b$04$" 开头；cost=12 时以 "$2b$12$" 开头。
    提示: CryptContext(schemes=["bcrypt"], bcrypt__rounds=cost)

    例如: hash_with_cost("abc", 4) → "$2b$04$..."
    """
    temp_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=cost)
    return temp_context.hash(password)


# ===== 练习 5：判断旧哈希是否需要升级 =====
def needs_rehash(hashed: str, target_cost: int) -> bool:
    """
    判断一个已有哈希的工作因子低于 target_cost 时，是否需要用新 cost 重新哈希。

    要求:
    - 哈希的 cost < target_cost → True
    - 哈希的 cost >= target_cost → False

    场景: 网站把 cost 从 10 提到 12，用户下次登录成功时顺手用新 cost 重算并更新数据库。
    提示: CryptContext(..., bcrypt__rounds=target_cost).needs_update(hashed)

    例如: needs_rehash("$2b$10$...", 12) → True
          needs_rehash("$2b$12$...", 12) → False
    """
    return CryptContext(schemes=["bcrypt"], bcrypt__rounds=target_cost).needs_update(hashed)

# ===== 练习 6：安全地验证（容错） =====
def safe_verify_password(password: str, hashed: str) -> bool:
    """
    和 verify_password 一样，但哈希格式非法时返回 False，不能抛异常。

    场景: 数据库里混进了脏数据（比如空字符串、"123456" 明文），
         登录接口不能因此 500，应统一按"验证失败"处理。

    例如: safe_verify_password("123456", "not-a-hash") → False
          safe_verify_password("123456", 合法哈希)     → True
    提示: passlib 对非法哈希会抛 ValueError，用 try/except 包住。
    """
    try:
        return pwd_context.verify(password, hashed)
    except ValueError:
        return False


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    errors = []

    def check(name, cond, expected, actual):
        if cond:
            print(f"✅ {name}")
        else:
            errors.append(f"{name} — 期望 {expected!r}，实际 {actual!r}")

    SAMPLE = "$2b$12$.L39Cv3UcVlYyHCR/VvAleqFTlmeHEf5KKqd/ZX9rQ20g84s/pKL6"

    # ---- 练习 1 ----
    try:
        h1 = hash_password("123456")
        h2 = hash_password("123456")
        check("1.1 返回字符串", isinstance(h1, str), "str", type(h1).__name__)
        check("1.2 是 bcrypt 格式", isinstance(h1, str) and h1.startswith("$2b$"), "$2b$ 开头", h1)
        check("1.3 不含明文", isinstance(h1, str) and "123456" not in h1, "不含明文", h1)
        check("1.4 正确密码可通过 verify", pwd_context.verify("123456", h1), True, False)
        check("1.5 两次哈希不同（随机盐）", h1 != h2, "不同", "相同")
    except Exception as e:
        errors.append(f"练习 1 抛异常: {type(e).__name__}: {e}")

    # ---- 练习 2 ----
    try:
        ok = verify_password("123456", SAMPLE)
        bad = verify_password("wrong", SAMPLE)
        check("2.1 正确密码返回 True", ok is True, True, ok)
        check("2.2 错误密码返回 False", bad is False, False, bad)
    except Exception as e:
        errors.append(f"练习 2 抛异常: {type(e).__name__}: {e}")

    # ---- 练习 3 ----
    try:
        info = parse_bcrypt_hash(SAMPLE)
        expected = {
            "version": "2b",
            "cost": 12,
            "salt": ".L39Cv3UcVlYyHCR/VvAle",
            "digest": "qFTlmeHEf5KKqd/ZX9rQ20g84s/pKL6",
        }
        check("3.1 每个字段都对", info == expected, expected, info)
        check("3.2 cost 是 int", isinstance(info.get("cost"), int), "int", type(info.get("cost")).__name__)
    except Exception as e:
        errors.append(f"练习 3 抛异常: {type(e).__name__}: {e}")

    # ---- 练习 4 ----
    try:
        h4 = hash_with_cost("abc", 4)
        h12 = hash_with_cost("abc", 12)
        check("4.1 cost=4 前缀", isinstance(h4, str) and h4.startswith("$2b$04$"), "$2b$04$ 开头", h4)
        check("4.2 cost=12 前缀", isinstance(h12, str) and h12.startswith("$2b$12$"), "$2b$12$ 开头", h12)
        check("4.3 生成的哈希可验证", pwd_context.verify("abc", h4), True, False)
    except Exception as e:
        errors.append(f"练习 4 抛异常: {type(e).__name__}: {e}")

    # ---- 练习 5 ----
    try:
        old10 = CryptContext(schemes=["bcrypt"], bcrypt__rounds=10).hash("x")
        new12 = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12).hash("x")
        r1 = needs_rehash(old10, 12)
        r2 = needs_rehash(new12, 12)
        check("5.1 cost 10 需要升级到 12", r1 is True, True, r1)
        check("5.2 cost 12 不需要升级", r2 is False, False, r2)
    except Exception as e:
        errors.append(f"练习 5 抛异常: {type(e).__name__}: {e}")

    # ---- 练习 6 ----
    try:
        r_bad = safe_verify_password("123456", "not-a-hash")
        r_empty = safe_verify_password("123456", "")
        r_ok = safe_verify_password("123456", SAMPLE)
        check("6.1 非法哈希返回 False", r_bad is False, False, r_bad)
        check("6.2 空字符串返回 False", r_empty is False, False, r_empty)
        check("6.3 合法哈希正常验证", r_ok is True, True, r_ok)
    except Exception as e:
        errors.append(f"练习 6 抛异常: {type(e).__name__}: {e}")

    print()
    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！13 passlib + bcrypt = ✅")
