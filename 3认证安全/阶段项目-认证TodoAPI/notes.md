# 阶段项目 · 认证 Todo API — 学习笔记

> 完成日期：2026-11-11
> 数据库：`auth_todo_db`
> 项目目录：`3认证安全/阶段项目-认证TodoAPI/`
> 依赖：仓库根目录 `.venv`（fastapi / sqlalchemy / alembic / passlib / bcrypt / python-jose / python-multipart）

---

## 一、项目结构

```
HTTP
  ↓
schemas.py          请求/响应模型（UserCreate / UserRead / TokenPair / TodoCreate ...）
  ↓
main.py             路由：
                      POST /auth/register   注册
                      POST /auth/login      登录（form）
                      POST /auth/refresh    刷新
                      GET  /users/me        当前用户
                      GET/POST/PATCH/DELETE /todos   受保护 CRUD
  ↓
security.py         纯函数：hash_password / verify_password / JWT 签发与解码
  ↓
models.py           User（含 password_hash）/ Todo
  ↓
database.py         engine / SessionLocal / get_db
  ↓
PostgreSQL          users / todos / alembic_version
```

依赖方向：

```
main.py ──→ security.py（纯函数，不依赖项目其它模块）
   ├─────→ schemas.py
   ├─────→ models.py ──→ database.py
   └─────→ database.py
alembic/env.py ──→ database.Base + models
```

---

## 二、任务拆解

| Task | 内容 | 状态 |
|------|------|------|
| 1 | 数据层：`database.py` / `models.py`（User 加 password_hash）/ Alembic 建表 | ✅ |
| 2 | `security.py`：bcrypt 哈希 + JWT 签发/解码 | ✅ |
| 3 | `schemas.py`：注册/登录/Token/Todo 模型 | ✅ |
| 4 | `main.py`：注册 / 登录 / 刷新 + `get_current_user` + 受保护 Todo CRUD | ✅ |
| 5 | uvicorn + curl 端到端验证 | ✅ |

---

## 三、知识点讲解

### Task 1 · 数据层

**User 加一列 `password_hash`：**

```python
password_hash: Mapped[str] = mapped_column(String(255))
```

- 字段名写 `password_hash` 而不是 `password`：名字直接说明里面存的是**哈希**，防止后来的人误以为可以读出明文
- `Mapped[str]` → 自动 `NOT NULL`
- `String(255)` 不是给 bcrypt 用的（bcrypt 固定 60 字符），是给**算法迁移**留余量：
  - argon2id 的 PHC 串约 97 字符
  - 参数/版本/盐长度都编码在字符串里，长度会变
  - PG 的 `varchar(n)` 长度只是约束，不预分配空间，255 不浪费

**Alembic 三步：**

```bash
../../.venv/bin/alembic init alembic
# 改 alembic.ini：sqlalchemy.url = postgresql+psycopg:///auth_todo_db
# 改 alembic/env.py：from database import Base + import models + target_metadata = Base.metadata
../../.venv/bin/alembic revision --autogenerate -m "create users and todos"
../../.venv/bin/alembic upgrade head
```

关键检查：`Detected added table 'users'` / `'todos'`；`\d users` 里 `password_hash` 是 `character varying(255) not null`。

### Task 2 · security.py

**密码：**

```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)
```

- 同样密码两次哈希不同（随机盐）
- verify 从哈希串里取出盐，重算后比对

**JWT：**

```python
payload = {
    "user_id": user_id,
    "type": "access",          # 或 "refresh"
    "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
}
jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)      # 签发：单数 + 字符串
jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])     # 验证：复数 + 列表
```

encode / decode 的参数**不对称**：

| 操作 | 参数 | 类型 | 原因 |
|------|------|------|------|
| encode | `algorithm` | 字符串 | 签发只能用一种算法 |
| decode | `algorithms` | 列表 | 验证可以接受多种（算法轮换） |

列表里只放自己用的算法，绝不能允许 `"none"` 之类的攻击者可控算法。

**`decode_token`: 异常类型就是「原因」**

```python
def decode_token(token: str, expected_type: str) -> dict:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("type") != expected_type:
        raise JWTError("invalid token type")
    return payload
```

不做 `try/except` —— 让 jose 的异常原样往外抛：

| 情况 | 异常 |
|------|------|
| 过期 | `ExpiredSignatureError`（`JWTError` 子类） |
| 签名被篡改 / 格式错 | `JWTError` |
| 类型不对 | 手动 `raise JWTError(...)` |

调用方用 `except ExpiredSignatureError` / `except JWTError` 区分「该刷新」和「该拒绝」。

**为什么 access 短、refresh 长：**

- access 每个请求都带 → 暴露面大；JWT 无状态，签出去收不回 → 只能靠短有效期止损
- refresh 使用频率低 → 可以长；但要能吊销（本项目简化：未做服务端 store）

### Task 3 · schemas.py

三个设计点：

1. **密码只进不出**：`UserCreate` 收 `password`；`UserRead` 绝不含 `password_hash`。响应模型就是白名单。
2. **`TodoCreate` 没有 `user_id`**：身份从 token 推导，不信客户端（防 IDOR）。
3. **`TokenPair`**：`access_token` + `refresh_token` + `token_type="bearer"`（小写，OAuth2 约定）。

**bcrypt 的 72 字节上限（实测）**

bcrypt 只使用密码的**前 72 个字节**，超出部分静默丢弃：

```python
h = hash("a" * 72 + "AAAAAAAA")
verify("a" * 72 + "ZZZZZZZZ", h)   # → True  ⚠️
```

后果：

- 前 72 字节相同的两个密码能登录同一个账号
- 用户改密码最后几位 → 旧密码仍能登录
- 第 72 字节之后全是「虚假强度」

所以 schema 里 `max_length=72`。注意 **Pydantic 的 max_length 数字符不数字节**（30 个汉字 = 90 字节），更严格的做法：

```python
@field_validator("password")
@classmethod
def password_within_bcrypt_limit(cls, v: str) -> str:
    if len(v.encode("utf-8")) > 72:
        raise ValueError("password too long")
    return v
```

**`Field` 签名（踩过的坑）：**

```python
Field(default=..., *, min_length=..., max_length=...)
```

第一个位置参数是 `default`。`Field(1, max_length=120)` 等于「默认值 1 + 最长 120」，不是 min_length=1。约束参数一律用关键字。

### Task 4 · main.py

**注册：**

```python
existing = db.scalar(select(models.User).where(models.User.username == payload.username))
if existing is not None:
    raise HTTPException(409, "username already taken")

user = models.User(
    username=payload.username,
    email=payload.email,
    password_hash=security.hash_password(payload.password),
)
db.add(user); db.commit(); db.refresh(user)
return user
```

- `select(...)` 只是构造语句，必须 `db.scalar(...)` / `db.scalars(...)` 执行
- **不能** `models.User(**payload.model_dump())`：多出 `password` 字段 → `TypeError: 'password' is an invalid keyword argument for User`

**登录（OAuth2 password flow）：**

```python
user = db.scalar(select(models.User).where(models.User.username == form.username))
if user is None or not security.verify_password(form.password, user.password_hash):
    raise auth_error()
return schemas.TokenPair(
    access_token=security.create_access_token(user.id),
    refresh_token=security.create_refresh_token(user.id),
)
```

- `OAuth2PasswordRequestForm` 收 **form**，不收 JSON；字段是 `form.username` / `form.password`
- 用户不存在与密码错误返回**同一个** 401，不泄露用户名是否存在
- 401 必须带 `WWW-Authenticate: Bearer`

**刷新：**

```python
try:
    claims = security.decode_token(payload.refresh_token, "refresh")
except JWTError:
    raise auth_error("invalid refresh token")

user = db.get(models.User, claims["user_id"])
if user is None:
    raise auth_error("invalid refresh token")

return schemas.TokenPair(
    access_token=security.create_access_token(user.id),
    refresh_token=security.create_refresh_token(user.id),
)
```

- `decode_token(..., "refresh")` 的第二个参数防止 access token 拿来换新 token
- 刷新时也查库：token 有效 ≠ 用户还在（被删/禁用）
- `db.refresh(obj)` 是「把该对象字段从库里重读」，参数是这个实例；不是刷新数据库

**`get_current_user`：**

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    try:
        claims = security.decode_token(token, "access")
    except JWTError:
        raise auth_error("invalid token")
    user = db.get(models.User, claims["user_id"])
    if user is None:
        raise auth_error("invalid token")
    return user
```

Depends 链：`Authorization: Bearer` → 取 token → 验签 + 查类型 → 查库 → User。

**受保护 Todo CRUD + 所有权：**

```python
todo = db.scalar(
    select(models.Todo).where(
        models.Todo.id == todo_id,
        models.Todo.user_id == current_user.id,   # ← 关键
    )
)
if todo is None:
    raise HTTPException(404, "todo not found")
```

- 一次查询同时判断「存在」和「归属」
- 越权统一 **404**（403 等于告诉对方「资源存在，只是不属于你」）
- 创建时 `user_id=current_user.id`，忽略请求体里的任何 `user_id`

**PATCH 部分更新（Unit of Work）：**

```python
data = payload.model_dump(exclude_unset=True)
for key, value in data.items():
    setattr(todo, key, value)
db.commit()          # Session 跟踪属性变化 → 自动 UPDATE
db.refresh(todo)
return todo
```

`db.add(todo)` 对已在 Session 中的对象是空操作；对象没被修改就 commit，什么都不会发生。

### Task 5 · 端到端验证

```bash
../../.venv/bin/uvicorn main:app --port 8765
```

curl 验证链路：

1. 注册 → 201，响应无密码字段
2. 登录 → 200，拿到双 token
3. 创建 todo 并伪造 `user_id=99999` → 201，实际 `user_id` 是 token 里的用户
4. 列表只能看到自己的
5. refresh 冒充 access 访问 `/todos` → 401
6. `/auth/refresh` 换新 token → 200
7. 新 access 访问 `/users/me` → 200
8. 不带 token → 401 + `WWW-Authenticate: Bearer`

---

## 四、练习 ↔ 知识点映射

| 文件 / 测试 | 覆盖知识点 |
|-------------|-----------|
| `models.py` 测试 | metadata、password_hash 非空/String(255)、无明文 password 列、relationship |
| Alembic 迁移 | autogenerate 差异驱动、upgrade、`\d users` |
| `security.py` 11 条 | bcrypt 哈希/随机盐、access/refresh 签发、type 双向校验、过期/篡改/乱码异常 |
| `schemas.py` 12 条 | 密码长度约束、UserRead 不泄露、TokenPair 默认值、TodoCreate 无 user_id、Field 约束 |
| `main.py` 35 条 | 注册 201/409、登录 form/401、刷新、401 头、未认证拦截、越权 404、PATCH exclude_unset |
| uvicorn + curl | 真实 HTTP 链路 |

---

## 五、本次纠错全记录

### 问题 1：`String(100)` vs `String(255)`

- **现象**：测试报 `password_hash 长度应为 255，实际 100`
- **提问**：bcrypt 只有 60 字符，为什么留 255？
- **讲解**：为算法迁移留余量（argon2id ~97 字符）；哈希串长度随算法/参数变化；varchar 长度不占额外空间
- **解决**：`String(255)`

### 问题 2：`arget_metadata` 拼写

- **现象**：`NameError: name 'arget_metadata' is not defined`
- **解决**：`target_metadata = Base.metadata`

### 问题 3：`create_refresh_token` 的 `"refesh"`

- **现象**：刷新测试失败，`type` 匹配不上
- **解决**：`"refresh"`

### 问题 4：`decode_token` 的四连错

1. 没有检查 `expected_type` → **安全漏洞**：refresh 可当 access 用
2. `raise ("401")` → `TypeError: exceptions must derive from BaseException`（raise 的必须是异常对象）
3. `try/except JWTError` 把 `ExpiredSignatureError` 降级成泛化 `JWTError` → 测试「过期 token 抛 ExpiredSignatureError」失败
4. `algorithms=ALGORITHM` 传字符串（此版本 jose 宽容，但官方 API 是列表）

- **解决**：三行版本（decode → 查 type → return），不加 try/except

**用户提问：函数怎么区分「token 不对」还是「过期」？**

- 答：靠**异常类型**，不靠返回值。过期 → `ExpiredSignatureError`，签名/格式/类型 → `JWTError`。不 catch 就是为了保住这个区分。

### 问题 5：`TodoCreate` 的 `Field(1, max_length=120)`

- **现象**：`TodoCreate()` 不报错（默认值 1），空 title 不被拒（无 min_length）
- **原因**：第一个位置参数是 `default`，不是 `min_length`；默认值默认不校验
- **解决**：`Field(min_length=1, max_length=200)`

### 问题 6：注册路由的一连串错误

```python
u = select(models.User).where(...)   # 只是构造，不是执行
if u is None:                        # 永远 False
    payload["password"] = ...        # Pydantic 不支持下标
    db.add(u)                        # add 了 Select 对象
    db.refresh()                     # 缺参数
raise HTTPException(409)             # 无条件抛
```

- **踩坑 1**：`select` 构造 ≠ 执行（学习项 6 老坑），应 `db.scalar(select(...))`
- **踩坑 2**：`payload["password"]`（dict 点访问第 5 次），应 `payload.password`
- **踩坑 3**：`user` 写成了 dict，`db.add(dict)` 不行，必须是 `models.User(...)`
- **踩坑 4**：`payload.uaername` 拼写
- **逻辑**：查重应为「存在才 409」，不是「最后无条件 409」

### 问题 7：登录条件写反（三次才对）

| 版本 | 结果 |
|------|------|
| `if user is not None or verify(form.password_hash)` | 存在用户就 401；`form` 没有 password_hash |
| `if user is None or verify(form.password, user.password_hash)` | 密码正确反而 401，错误 200（致命） |
| `if user is None or not verify(...)` | ✅ |

- **教训**：布尔条件要用测试反推 —— 「正确密码应该 200，错误密码应该 401」，而不是只看代码读起来顺不顺

### 问题 8：PATCH 不生效

- **现象**：PATCH 返回 200，但 `done` 仍为 False（`done 变为 True` 测试失败）
- **原因**：完全没有使用 `payload`，`db.add(todo)` 是空操作，commit 没有变更
- **解决**：`model_dump(exclude_unset=True)` → `setattr` → commit

### 用户主动提问

| 问题 | 答案要点 |
|------|---------|
| String(255) 为什么不是 60 | 给算法迁移留余量；varchar 长度不占空间 |
| decode 的 algorithms 是数组，encode 呢？ | encode 用单数 `algorithm="HS256"`；decode 用列表支持算法轮换 |
| 函数怎么区分 token 不对还是过期？ | 异常类型：`ExpiredSignatureError` vs `JWTError` |
| `raise JWTError("...")` 文本能换吗？ | 可以；文本只给人看，逻辑看类型 |
| `db.refresh(user)` 为什么要带 user？ | 刷新的是「这个对象」的字段，不是数据库；`db.get` 是按 id 捞对象 |
| `not` 和 JS 的 `!` 一样吗？ | 一样；`!=` ≈ `!==` |
| 为什么 `schemas.TokenPair(...)`？ | 构造 Pydantic 实例；有校验/默认值/IDE 提示；返回 dict 也能被 response_model 序列化 |

---

## 六、踩坑速查表

| 错误写法 | 报错 / 现象 | 正确写法 |
|---------|------------|---------|
| `String(100)` 存哈希 | 长度不够未来算法 | `String(255)` |
| `target_metadata` 拼错 | `NameError` | 检查拼写 |
| `type: "refesh"` | 刷新永远类型不匹配 | `"refresh"` |
| `decode_token` 不查 type | refresh 可当 access（越权） | `payload.get("type") != expected_type` → `JWTError` |
| `raise ("401")` | `TypeError: exceptions must derive from BaseException` | `raise HTTPException(401, ...)` |
| `except JWTError` 全包 | 过期的 `ExpiredSignatureError` 被降级 | 不 catch，让异常原样抛 |
| `jwt.decode(..., algorithms="HS256")` | 此版本能跑，但不可靠 | `algorithms=["HS256"]` |
| `Field(1, max_length=120)` | 1 成了 default；空串不拦 | `Field(min_length=1, max_length=200)` |
| `u = select(...)` 然后 `if u is None` | Select 对象永不为 None | `u = db.scalar(select(...))` |
| `payload["password"]` | `TypeError: not subscriptable` | `payload.password` |
| `db.add({...})` | `UnmappedInstanceError` | `db.add(models.User(...))` |
| `db.refresh()` | 缺 instance | `db.refresh(user)` |
| `db.add(todo)` 后 commit（没改字段） | 返回 200 但值没变 | `setattr` 后再 commit |
| 单条查询只按 id | 能读到/改到别人的 todo | `where(id == ..., user_id == current_user.id)` |
| 越权返回 403 | 泄露资源存在性 | 统一 404 |
| 登录 `if user is None or verify(...)` 少了 `not` | 密码正确被拒、错误放行 | 加 `not` |
| `@app.post("/todos")` 用 `payload.user_id` | 客户端可伪造归属 | `user_id=current_user.id` |

---

## 七、常用命令速查

```bash
cd 3认证安全/阶段项目-认证TodoAPI

# 建库（已存在）
createdb auth_todo_db

# 迁移
../../.venv/bin/alembic revision --autogenerate -m "xxx"
../../.venv/bin/alembic upgrade head
../../.venv/bin/alembic current

# 测试
../../.venv/bin/python models.py
../../.venv/bin/python security.py
../../.venv/bin/python schemas.py
../../.venv/bin/python main.py

# 启动
../../.venv/bin/uvicorn main:app --reload
# Swagger: http://127.0.0.1:8000/docs

# 看表
psql -d auth_todo_db -c "\dt"
psql -d auth_todo_db -c "\d users"
```

---

## 八、待改进（留到后续阶段）

1. **refresh token 无法吊销**：无状态 JWT 签出去就收不回。生产要存服务端（Redis/DB），实现登出、强制下线、token 轮换（rotation）
2. **SECRET_KEY 硬编码**：应改为环境变量 / `.env`（第四阶段 CI/CD、Docker 时处理）
3. **登录无限流**：可被暴力破解（第六阶段 30 Rate Limiting）
4. **无邮箱验证 / 密码重置**
5. **测试写成 pytest**（学习项 17/18）
6. **`get_current_user` + 所有权查询可以抽成依赖 / service**（第四阶段工程化）
7. **bcrypt 72 字节限制只按字符数校验**：更严格应校验字节数
