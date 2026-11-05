# 13 passlib + bcrypt — 密码哈希与加盐

> 学习日期：2026-11-05
> 环境：Python 3.12 / passlib 1.7.4 / **bcrypt 4.0.1（必须锁定，5.x 不兼容）**
> 说明：按用户要求，**先学 13 再学 12**（12 的登录接口需要密码验证，13 是前置）

---

## 一、知识点讲解

### 1. 哈希 ≠ 加密

| | 加密（encryption） | 哈希（hash） |
|---|---|---|
| 能否还原 | ✅ 有密钥就能解回明文 | ❌ 单向，永远回不去 |
| 长度 | 随原文变长 | 固定长度 |
| 典型算法 | AES | SHA-256、bcrypt |
| 密钥 | 需要 | 不需要 |

**前端类比**：

- 加密像上锁的箱子 —— 拿钥匙能打开，拿到原文。
- 哈希像指纹 —— 能从人身上取下指纹，但没法从指纹还原出这个人；但可以拿两个指纹**比对**是不是同一个人。

**密码存哈希的两条理由**：

1. 服务器**根本不需要知道原始密码**，只需要回答「这次输入和注册时是不是同一个」。比对指纹就够了。
2. **拖库后损失更小**：存密文，密钥泄露 = 全部还原；存哈希，攻击者拿到一堆无法反推的指纹。

**验证流程**：用同样的算法再算一遍，然后比对 —— 不是「解密出来比对」。

### 2. 离线暴力破解与彩虹表

攻击者拿到数据库后的套路：

1. 预先算好常见密码的哈希表（`123456 → 哈希A`、`password → 哈希B`……），即 rainbow table。
2. 拖库后逐个比对，秒破一批弱密码。

更糟：**没有盐**时，两个用户密码相同 → 哈希完全一样 → 攻击者一眼看出「这俩人密码相同」，破一个等于破一批。

### 3. 盐（salt）

给每个用户配一段**随机、唯一**的字符串，和密码拼在一起再哈希：

```
hash("123456" + "aX9#kL") ≠ hash("123456" + "Q2$mPz")
```

- 盐**不需要保密**，明文和哈希存在一起。
- 它防的不是「被看到」，而是**被预计算**：盐每人不同，攻击者无法预先算表，只能逐个用户、逐个密码硬算。
- 盐**不防拖库本身**，只限制拖库后能跑多快。

### 4. bcrypt 为什么「慢」

bcrypt 在盐之外还有 **cost 因子（工作因子）**，把哈希过程故意重复 **2^cost** 轮：

```
$2b$12$N9qo8uLOickgx2ZMRZoMye...
 │   │  └── 22 位盐 + 31 位摘要（合在一起）
 │   └──── cost = 12 → 2^12 = 4096 轮
 └──────── 算法版本（2b）
```

- 正常登录只验证一次，慢 0.1 秒无所谓。
- 攻击者要猜几百万次，**每次都要付同样的成本**，经济上不划算。
- 对比 SHA-256：快 → 对攻击者也快 → 不适合存密码。
- **盐和 cost 都嵌在哈希字符串里**，数据库只需要一列。

### 5. passlib API

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

hashed = pwd_context.hash("123456")        # 每次结果不同（随机盐）
pwd_context.verify("123456", hashed)       # True
pwd_context.verify("wrong",  hashed)       # False
```

关键点：

- **不能**写成 `hash(输入) == 数据库里的值` —— 盐每次不同，两次 hash 永远不相等。
- `verify(明文, 哈希)` 从哈希串里取出盐和 cost 重算，再比对。
- 非法哈希会抛 `ValueError`，登录接口要 try/except 兜底。
- `needs_update(hashed)`：按当前配置判断旧哈希是否该重算（cost 变高、算法被标记 deprecated）。
- bcrypt 只处理前 **72 字节**，超长密码会被截断/报错（bcrypt 5 直接抛错）。

### 6. 工程实践

- **依赖锁版本**：passlib 1.7.4 与 bcrypt 5.0.0 不兼容（passlib 后端自检用超长密码，bcrypt 5 直接抛 `ValueError: password cannot be longer than 72 bytes`）→ 固定 `bcrypt==4.0.1`。
- **cost 升级迁移**：老用户下次登录成功时用新 cost 重算并更新数据库，不需要强制所有人改密码。

---

## 二、练习 ↔ 知识点映射

| 练习 | 函数 | 对应知识点 |
|------|------|-----------|
| 1 | `hash_password` | `context.hash()`、随机盐（两次结果不同）、不含明文 |
| 2 | `verify_password` | `context.verify()`，不能重算后比字符串 |
| 3 | `parse_bcrypt_hash` | `$2b$12$<22位盐><31位摘要>` 结构、`split("$")` 的边界 |
| 4 | `hash_with_cost` | 工作因子 `bcrypt__rounds`，cost 的零填充前缀 |
| 5 | `needs_rehash` | `needs_update` / 手动比 cost，cost 升级场景 |
| 6 | `safe_verify_password` | 脏数据容错、`ValueError`、精确 except |

---

## 三、练习纠错全记录

### 探底：两个问题都答「不知道」

问：哈希 vs 加密的区别？为什么存哈希不存密文？盐的作用？
答：**都不知道** → 直接讲解（不再引导）。这决定了本节按「从零讲」的深度展开。

### 讲解后的检查问题

1. 「拖库后攻击者下一步怎么做？」→ 答「暴力破解，拿常见密码做 hash 再对比」✅ 正确。
2. 「盐明文存库，拖库后盐也泄露，还有用吗？」→ 答「有用，防住成本……本质是验证一次成本巨高……两个人密码相同哈希也不同……防不住拖库本身」✅ 核心正确。需澄清的分工：**盐负责「不能预计算」，cost 负责「单次很慢」**。
3. 「注册哈希 H1，登录再 hash 得 H2，相等吗？正确验证写法？」→ 答「不相等，salt 不同；用 verify」✅ 正确。

### 练习 3：连续四个坑

代码：

```python
salt_list = hashed.split("$")
return {
    "version": salt_list[0],
    "cost": salt_list[1],
    "salt": salt_list[2].slice(0, 22),
    "version": salt_list[2].slice(22)
}
```

| # | 现象 | 原因 | 对应知识点 |
|---|------|------|-----------|
| 1 | `AttributeError: 'str' object has no attribute 'slice'` | `.slice()` 是 JavaScript 方法，Python 用 `s[start:end]` | 语言迁移，JS 思维 |
| 2 | 字段整体错位 | `"$2b$12$..."` 以 `$` 开头，`split` 第一段是空串 → 实际 `['', '2b', '12', 盐+摘要]` | 先看真实数据再取下标 |
| 3 | 字典只剩 `version` 一个键 | 写了两遍 `"version"`，后一个**静默覆盖** | 11 JWT 练习 3 同款（`access_token` 重复） |
| 4 | cost 是字符串 `"12"` | 未 `int()` | 类型意识 |

用户说「你告诉我」→ 直接给出正确代码并逐条解释。正确写法：

```python
parts = hashed.split("$")
last = parts[3]
return {
    "version": parts[1],
    "cost": int(parts[2]),
    "salt": last[:22],
    "digest": last[22:],
}
```

**Claude 自己的错误**：第一次给的测试期望值把盐写成 24 位、摘要写成 29 位（应为 22/31），导致用户正确代码报错。用 Python 量了 `split` 各段长度后修正测试。教训：期望值也要用真实数据核对，不能手数。

### 练习 4：直接问「怎么写」

给出两行答案：

```python
context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=cost)
return context.hash(password)
```

强调 `bcrypt__rounds` 是双下划线、临时 context 不污染全局、verify 会自己读哈希里的 cost。

### 练习 5：能过但「糙」→ 再讲一遍

初版手写解析：

```python
cost = int(hashed.split("$")[2])
return cost < target_cost
```

能过测试，但只懂 bcrypt。建议改用：

```python
return CryptContext(schemes=["bcrypt"], bcrypt__rounds=target_cost).needs_update(hashed)
```

用户第一次没看懂「算法迁移」那层，换说法重讲：argon2 哈希 `$argon2id$v=19$...` 用 `split("$")[2]` 拿到 `v=19`，`int()` 直接炸；库认识所有算法。最终改用了 `needs_update`。

### 练习 6：测试全绿但藏着登录绕过 bug

初版：

```python
try:
    pwd_context.verify(password, hashed)
    return True
except:
    return False
```

- **现象**：测试 6.1/6.2/6.3 全绿。
- **隐藏 bug**：`verify` 对错误密码**不抛异常**，只返回 `False`；返回值被丢弃 → 密码错 + 哈希合法时返回 `True` → **登录直接放行**。
- **为什么测试没抓到**：测试只覆盖了「非法哈希」和「正确密码」，没覆盖「错误密码 + 合法哈希」。
- **复现**：单独跑 `safe_verify_password('WRONG', 合法哈希)`，结果 `True`。
- **修复**：`return pwd_context.verify(...)`；`except:` → `except ValueError:`。
- **教训**：「测试通过 ≠ 代码正确」（11 JWT 练习 3 的 role 字面量同款）；裸 except 会吞 `KeyboardInterrupt` 和真 bug。

### 环境踩坑：passlib 与 bcrypt 5 不兼容

```
ValueError: password cannot be longer than 72 bytes, truncate manually if necessary
  ... passlib/handlers/bcrypt.py ..., in detect_wrap_bug
```

- 原因：passlib 1.7.4 已停止维护，后端自检用超过 72 字节的密码；bcrypt 5.0.0 改为直接抛错。
- 解决：`pip install "bcrypt==4.0.1"`。
- 教训：**依赖要锁版本**，requirements.txt / pyproject 写死。

---

## 四、踩坑速查表

| 错误写法 | 现象 | 正确写法 |
|----------|------|----------|
| `hashed.split("$")[0]` 当版本号 | 拿到空串，字段整体错位 | 先 `print(hashed.split("$"))`，注意开头 `$` 产生的空段 |
| `s.slice(0, 22)` | `AttributeError`（JS 写法） | `s[:22]` / `s[22:]` |
| 字典字面量重复 key | 静默覆盖，不报错 | 检查 key 唯一 |
| `"cost": parts[2]` | 字符串 `"12"` | `int(parts[2])` |
| `verify(...)` 后不接返回值 | 错误密码也返回 True → 登录绕过 | `return pwd_context.verify(...)` |
| `except:` | 吞掉 Ctrl+C 和真 bug | `except ValueError:` |
| `hash(输入) == 库里哈希` | 永远 False（盐随机） | `pwd_context.verify(输入, 库里哈希)` |
| `bcrypt` 5.x + `passlib` 1.7.4 | 后端初始化 ValueError | 固定 `bcrypt==4.0.1` |
| 密码超过 72 字节 | bcrypt 截断/报错 | 入库前限制长度，或先做 SHA-256 预哈希 |

---

## 五、下一步：12 FastAPI OAuth2

本节的知识会在 12 里直接用到：

1. 注册：`hash_password(password)` 存库（**绝不存明文**）。
2. 登录：`verify_password(输入, 库里的哈希)`，成功才签发 JWT。
3. 登录成功时可用 `needs_update` 顺手把老 cost 的哈希升级。
