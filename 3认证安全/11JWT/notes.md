# 11 JWT — 学习笔记

> 第三阶段：认证与安全 · 学习项 11
> 完成日期：2026-11-04
> 练习：`practice.py`（6 个函数全部通过）

---

## 一、知识点讲解

### 1. Session vs JWT：后端记不记得你

| | Session（有状态） | JWT（无状态） |
|---|---|---|
| 状态存哪 | **服务端**（内存 / Redis） | **令牌自身**（签名的 payload） |
| 前端拿什么 | 会话 ID（随机字符串） | 完整 token |
| 每次请求 | 后端拿 ID 去表里查用户 | 后端验签 + 验过期，不查表 |
| 服务器重启/扩容 | 需要共享 session 存储 | 不受影响，任意机器都能验 |
| 能否主动吊销 | 删记录即可 | **不能**（只能等过期） |

Vue 类比：Session 像后端维护了一本 `loggedInUsers` 数据表，前端只拿个下标；JWT 像后端签发了一张盖了防伪章的会员卡，卡上写着你是谁，后端不留底。

**核心桥接例子（用户答对）**：JWT 模式下服务器重启、甚至换一台机器，已登录用户不会掉线 —— 只要签名对得上、没过期，token 就有效。这就是无状态的直接收益。

### 2. JWT 的结构：三段，两个点

```
Header . Payload . Signature
```

| 部分 | 内容 | 说明 |
|------|------|------|
| Header | `{"alg": "HS256", "typ": "JWT"}` | 算法信息 |
| Payload | `{"user_id": 1, "role": "user", "type": "access", "exp": 1793...}` | 业务 claims |
| Signature | HMAC-SHA256(Header + "." + Payload, 密钥) | 防伪章 |

**关键：Header 和 Payload 只是 Base64URL 编码，不是加密。** 任何人拿到 token 都能解开看内容（jwt.io），所以：

- payload 里**不能放密码、身份证等敏感信息**
- `user_id`、`role` 这类标识是常规内容，泄露了也改不了

### 3. 签名如何防篡改

```
Signature = HMAC-SHA256( Header + "." + Payload , 密钥 )
```

后端收到 token 后，用自己保管的**同一把密钥**对前两段重新算签名，再和第三段比对：

- 内容没改 → 重算结果一致 ✅
- 用户改了 payload（比如 `role` 改成 `admin`）→ 重算结果完全不同 → 对不上 ❌ 401

攻击者不知道密钥，就伪造不出能对上的签名。

> ⚠️ 用户这里第一次答错了（认为改 payload 会生效）。记忆点：签名是**内容哈希**，改一个字哈希全变，和 git commit hash 同理。

**安全完全押在密钥上**：密钥泄露 → 攻击者能签发任意合法 token。所以 `SECRET_KEY` 必须放环境变量，绝不能进 git。

### 4. 完整性 vs 机密性（两个独立问题）

| 问题 | JWT |
|------|-----|
| 能不能被篡改（完整性） | ✅ 安全，签名保护 |
| 能不能被偷看（机密性） | ❌ 不安全，payload 明文 |

结论不是“不能用”，而是“别放敏感信息”。

### 5. `exp` 与 Access / Refresh 双 token

`exp` 是标准 claim，过期时间点（Unix 时间戳 / datetime）。后端验签时自动检查，用户不用自己比时间。

两难：

- 有效期长（7 天）→ 体验好，但 token 被偷后能用 7 天
- 有效期短（15 分钟）→ 安全，但用户频繁被踢

**解法：一个用户两张卡**

| | Access Token | Refresh Token |
|---|---|---|
| 有效期 | 15 分钟 | 7~30 天 |
| 用途 | 访问业务 API | **只能**换新 access |
| 存哪 | 内存 / localStorage | httpOnly cookie |
| 被偷后果 | 最多 15 分钟 | 严重，但可吊销 |

工作流程：

```
登录 → access(15min) + refresh(30天)
  ↓
前 15 分钟正常访问
  ↓
access 过期 → 后端 401
  ↓
axios 拦截器拿 refresh 去 POST /refresh
  ↓
后端验 refresh + 查 store 记录 → 发新 access
  ↓
重发刚才失败的请求（用户无感）
```

### 6. httpOnly cookie

后端设置：

```
Set-Cookie: refresh_token=xxx; HttpOnly; Secure; SameSite=Strict; Path=/refresh
```

| | localStorage | httpOnly cookie |
|---|---|---|
| JS 能否读取 | ✅ | ❌（`document.cookie` 也看不到） |
| 谁发送 | axios 拦截器手动加头 | **浏览器自动**携带 |
| XSS 时 | 一行代码偷走 | JS 拿不到 |

分工：

- access token：前端可读 → axios 拦截器加 `Authorization: Bearer xxx`
- refresh token：httpOnly cookie → JS 碰不到，浏览器自动带；axios 需 `withCredentials: true`
- 跨域时后端 CORS 必须允许 credentials（第 14 项 CORS 伏笔）

### 7. 吊销：JWT 无状态的代价怎么补

| | Access | Refresh |
|---|---|---|
| 后端存不存 | ❌ 无状态 | ✅ 存（DB / Redis） |
| 能否吊销 | ❌ 只能等过期 | ✅ 删记录即可 |

**logout 流程**：

```
前端：清掉内存/localStorage 里的 access
  ↓
POST /logout（浏览器自动带 refresh cookie）
  ↓
后端：删掉数据库里的 refresh 记录 + Set-Cookie 清空 cookie
```

**残留风险（用户答对）**：logout 后，刚被偷的 access token 在过期前仍可访问业务接口（最多 15 分钟）。这是已知取舍；要立刻失效就得维护 access 黑名单，重新引入状态。

### 8. python-jose API

```python
from jose import jwt, JWTError, ExpiredSignatureError

token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
```

- `algorithm`（单数）用于 encode；`algorithms`（复数、列表）用于 decode
- decode 自动验签、验过期
- 篡改 → `JWTError`；过期 → `ExpiredSignatureError`（JWTError 子类）
- 函数内不捕获异常，让它自然抛给调用方

---

## 二、练习 ↔ 知识点映射

| 练习 | 函数 | 对应知识点 |
|------|------|-----------|
| 1 | `create_access_token` | `jwt.encode` + `exp` 时间点 |
| 2 | `decode_token` | `jwt.decode` + `JWTError` / `ExpiredSignatureError` |
| 3 | `create_refresh_token` / `create_token_pair` | 双 token、`type` 约定、不同有效期 |
| 4 | `verify_token_type` | 防止 refresh 冒充 access |
| 5 | `refresh_access_token` | 服务端 store 比对 + 换新 access |
| 6 | `revoke_refresh_token` | 登出 = 删除 refresh 记录 |

---

## 三、练习纠错全记录

### 探底问答

| 问题 | 回答 | 评价 |
|------|------|------|
| token 存哪、怎么带 | cookie + axios 拦截器 | ✅ 前端经验正确 |
| Session vs JWT 本质区别 | 不知道 | 后端视角，正常 |
| 服务器重启后 JWT 用户会掉线吗 | 不会，章对得上、没过期就能用 | ✅ 正确 |
| 改 payload 能不能冒充 admin | **会的** | ❌ 漏了“签名是对内容算的” |
| payload 明文放 role 安全吗 | 不安全，泄漏角色信息 | ⚠️ 方向对，但混淆“完整性 vs 机密性” |
| 如何兼得长短有效期 | 想不出来 | 正常，双 token 是工程技巧 |
| logout 后旧 access 还能用吗 | 会的 | ✅ 正确，理解残留风险 |

### 练习 1：`exp` 语义错误

- **现象**：`jwt.encode({"exp": 15}, ...)` 签出来的 token 一解就过期
- **原因**：`exp` 要的是“过期时间点”（时间戳/ datetime），不是“多少分钟后”
- **正确**：`datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)`
- **验证**：`datetime.fromtimestamp(claims["exp"], timezone.utc)` 转回来确认

另有 `# TODO / pass` 留下死代码，已要求清理。

### 练习 2：参数名单复数

- **现象**：`TypeError: decode() got an unexpected keyword argument 'algorithm'`
- **原因**：`jwt.decode` 的参数是复数 `algorithms`（传列表）
- **正确**：`jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])`

### 练习 3：三个问题

1. **`datetime.now(timezone)`** → 要传实例 `timezone.utc`，传类报 `TypeError`
2. **`timedelta(day=...)`** → 参数是复数 `days=`，报 `unexpected keyword argument`
3. **`type` 值写成 `"refresh_token"`** → 约定值是 `"refresh"`；`type` 是 access/refresh 之间的契约，必须精确匹配

### 练习 3（pair）：字典重复 key 静默覆盖

- **现象**：返回的 dict 只有 `access_token` 一个 key，测试提示缺 `refresh_token`
- **原因**：两个 key 都写成 `"access_token"`，后一个**静默覆盖**前一个，不报错
- **教训**：字典字面量重复 key 是静默失败，只能靠测试发现

### 练习 3 隐藏 bug：role 传成了字面量

- **代码**：`create_refresh_token(user_id, "refresh")`
- **问题**：用户 role 变成 `"refresh"`，身份信息丢失
- **为什么测试没抓到**：练习 3 的测试只检查 `type` 和 `user_id`，没检查 `role`
- **教训**：**测试通过 ≠ 代码正确**；用户主动质疑“那练习3第二部分就不对啊”后才发现

### 练习 4：dict 点访问 + return 当 raise

- `payload.type` → `AttributeError`；dict 必须 `payload["type"]`（第二次踩）
- `return JWTError` → 函数正常返回异常类，调用方感知不到；必须 `raise JWTError(...)`（第二次踩）

### 练习 5：store 的含义

- `store` 是模拟服务端存 refresh token 的 dict：`{user_id: refresh_token}`；现实中是 Redis / 数据库
- 用 `store.get(user_id)` 而不是 `store[user_id]`：用户登出后 key 不存在，`[]` 抛 `KeyError`，`.get()` 返回 `None` 交给 if 判断，最终抛约定的 `ValueError`
- 新 access 的 role 从 `payload["role"]` 取（服务端签名过、可信），函数签名里没有 role 参数

### 概念纠偏：`type` vs `role`

| 字段 | 含义 | 取值 |
|------|------|------|
| `type` | 这张 token 的用途 | `"access"` / `"refresh"` |
| `role` | 用户的身份/权限 | `"user"` / `"admin"` |

`create_access_token` 内部已固定写 `type="access"`，第二个参数要的是 **role**。写成 `"access"` 会让 token 里 `role: "access"`，权限信息错误。

### 练习 6：dict 删除 key

- `del store[key]` / `store.pop(key)`：key 不存在抛 `KeyError`
- `store.pop(key, None)`：不存在返回 `None`，不报错 —— 满足“记录不存在也不报错”
- 对称记忆：`dict.get()` 是安全地读，`dict.pop(key, default)` 是安全地删

### 代码 Review

1. 长行拆分：payload 构造和 encode 分两步（练习 1、3）
2. 错误消息具体化：`raise ValueError("不对劲")` → `"refresh token 已失效或已被吊销"`
3. 引号风格统一为双引号（测试代码里的单引号不动）

---

## 四、踩坑速查表

| 错误写法 | 现象 | 正确写法 |
|----------|------|----------|
| `"exp": 15` | 签出来就已过期（1970 年） | `"exp": datetime.now(timezone.utc) + timedelta(minutes=15)` |
| `jwt.decode(..., algorithm=[...])` | `TypeError: unexpected keyword argument 'algorithm'` | `algorithms=[...]`（复数） |
| `datetime.now(timezone)` | `TypeError`（传了类不是实例） | `datetime.now(timezone.utc)` |
| `timedelta(day=30)` | `TypeError: unexpected keyword argument 'day'` | `timedelta(days=30)` |
| `"type": "refresh_token"` | 类型校验永远不匹配 | `"type": "refresh"` |
| `{"a": 1, "a": 2}` | 静默覆盖，不报错，key 只剩一个 | 检查 key 是否重复 |
| `payload.type` | `AttributeError: 'dict' object has no attribute` | `payload["type"]` |
| `return JWTError` | 不抛异常，调用方以为成功 | `raise JWTError("...")` |
| `store[user_id]`（登出后） | `KeyError` | `store.get(user_id)` 再判断 |
| `del store[key]`（key 不存在） | `KeyError` | `store.pop(key, None)` |
| `create_refresh_token(uid, "refresh")` | role 字段变成字符串 `"refresh"` | `create_refresh_token(uid, role)` |
| `create_access_token(uid, "access")` | role 变成 `"access"` | 第二个参数是 **role**，不是 type |
