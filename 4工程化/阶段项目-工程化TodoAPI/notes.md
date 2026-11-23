# 阶段项目 · 工程化 Todo API — 学习笔记（Task 1–2）

> 完成日期：2026-11-18（Task 1A / 1B / 1C）
> 数据库：`eng_todo_db`（`alembic_version = aa893607ca00`）
> 项目目录：`4工程化/阶段项目-工程化TodoAPI/`
> 依赖：仓库根目录 `.venv`（fastapi / sqlalchemy / alembic / passlib / bcrypt / python-jose / python-multipart）

---

## 一、项目结构

```
main.py              组装 app：include_router + 全局路由（/users/me）
  │
  ├─→ routers/auth.py      /auth/register · /auth/login · /auth/refresh
  ├─→ routers/todos.py     /todos CRUD（每条都只操作自己的）
  │        │
  │        └─→ deps.py     get_current_user（从 Bearer token 认人）
  │
  ├─→ schemas.py           Pydantic 请求/响应模型
  ├─→ models.py            User（含 password_hash）/ Todo
  ├─→ security.py          纯函数：bcrypt + JWT
  └─→ database.py          engine / SessionLocal / Base / get_db
           │
           └─→ config.py   环境变量只在这一处读取

alembic/env.py ──→ config.DATABASE_URL + Base.metadata + models
```

依赖方向是单向的：

```
config.py（根，不 import 项目内任何模块）
   ↑
database.py / security.py
   ↑
models.py / schemas.py
   ↑
deps.py
   ↑
routers/*.py
   ↑
main.py
```

`database.py` **不 import models**（否则 models → database → models 循环引用），
`deps.py` 单独存在是为了让 `routers/todos.py` 不用 import `routers/auth.py` ——
否则 router 之间互相依赖，拆包就白拆了。

---

## 二、任务拆解

| Task | 内容 | 状态 |
|------|------|------|
| 1A | `config.py` + `database.py` —— 配置集中、连接 `eng_todo_db` | ✅ |
| 1B | `models.py` / `schemas.py` / `security.py` / Alembic 建表 | ✅ |
| 1C | `deps.py` + `routers/` + `main.py` 组装 | ✅ |
| 2 | Redis 缓存层 | ⬜ |
| 3 | pytest 测试体系 | ⬜ |
| 4 | Nginx 反向代理 | ⬜ |
| 5 | CI/CD | ⬜ |

---

## 三、知识点讲解

### Task 1A · config.py + database.py

**为什么单独一个 config.py？**

- 数据库地址、Redis 地址、密钥如果散落在各模块，换环境要翻遍代码；
- 第三阶段 `security.py` 里 `SECRET_KEY` 是硬编码的 —— 源码一旦进 Git 就是泄露；
- 同一份代码要能跑在 dev / test / prod，差异只应该来自环境变量。

```python
DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg:///eng_todo_db")
REDIS_URL: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-only-secret-change-me")
```

- `os.getenv(名字, 默认值)`：环境变量优先，读不到用默认值；
- 默认值只给本地开发用，部署时环境里必须设置真实密钥；
- Redis URL 末尾的 `0` 是 db 编号（学习项 16 练习用 15，生产用 0），不同用途分不同 db 互不干扰。

**测试里为什么要 `importlib.reload`？**

模块只在第一次 `import` 时执行，之后改 `os.environ` 不会让已经读过的常量更新。
`importlib.reload(模块)` 会重新执行一遍模块代码 —— 模拟「进程用新环境变量重新启动」。

**database.py 的关键改动**：`DATABASE_URL` 不再写死，而是 `create_engine(config.DATABASE_URL)`。

### Task 1B · models / schemas / security / Alembic

**models.py**：users 表多一列 `password_hash: Mapped[str] = mapped_column(String(255))`

- 列名是 `password_hash` 不是 `password` —— 名字说明「存的是哈希」；
- `Mapped[str]`（非 `str | None`）→ 自动 NOT NULL；
- 长度 255 给算法迁移留余量（bcrypt 是 60 位，将来换 argon2 可能更长）。

**schemas.py**：

- `password: str = Field(min_length=8, max_length=72)`
  - 下限 8：太短在离线爆破面前等于没有；
  - 上限 72：bcrypt 只处理前 72 **字节**，超出部分会被静默截断；
- `UserRead` 里没有 `password_hash` —— 响应模型就是白名单；
- `TodoCreate` 删掉 `user_id` —— 身份从 token 来，客户端传了也不采信（防 IDOR）。

**security.py**：`SECRET_KEY = config.SECRET_KEY`，不再是硬编码。

**Alembic**：`env.py` 里三件事

1. `import config as app_config` + `import models`（不 import 模型，metadata 是空的）；
2. `target_metadata = Base.metadata`；
3. `context.config.set_main_option("sqlalchemy.url", app_config.DATABASE_URL)`。

### Task 1C · 拆包：deps / routers / main

**deps.py 的职责：认人。**

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def auth_error(detail: str = "invalid credentials") -> HTTPException:
    return HTTPException(401, detail, headers={"WWW-Authenticate": "Bearer"})
```

- `auth_error` **返回**一个异常对象，调用方再 `raise` —— 复用了「401 + WWW-Authenticate」的构造；
- `tokenUrl` 只影响 Swagger 的 Authorize 按钮，不影响真实请求。

```python
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        claims = security.decode_token(token, "access")   # refresh 不能访问业务接口
    except JWTError:
        raise auth_error("invalid token")
    user = db.get(models.User, claims["user_id"])
    if user is None:
        raise auth_error("invalid token")
    return user
```

**router 拆包**：路径只写相对部分，`prefix` 拼在前面。

```python
router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", ...)      # 实际是 /auth/register
```

`main.py` 只做三件事：创建 app、挂路由、挂全局中间件（Task 2 才加）。
`include_router(A)` 传的是 **router 对象**，不是模块、也不是 `APIRouter` 类：

```python
app.include_router(auth.router)
app.include_router(todos.router)
```

**所有权 = 防 IDOR**：每条 todo 操作都同时按 `id` + `user_id` 查，
别人的资源统一 **404**（不是 403 —— 403 等于告诉对方「存在但你无权」）。

这段逻辑在三个路由里重复，Review 后抽成了私有函数：

```python
def _get_owned_todo(todo_id: int, current_user: models.User, db: Session) -> models.Todo:
    stmt = select(models.Todo).where(
        models.Todo.id == todo_id,
        models.Todo.user_id == current_user.id,
    )
    todo = db.scalar(stmt)          # 一条或 None
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="todo not found")
    return todo
```

放在 `routers/todos.py` 而不是 `deps.py`：它只服务 todo 的数据访问；
`deps.py` 放跨路由共享的依赖（如 `get_current_user`）。

**scalar vs scalars**：

| 方法 | 返回 | 用途 |
|------|------|------|
| `db.scalars(stmt)` | `ScalarResult`（一组，永远不是 None） | 列表 → `.all()` |
| `db.scalar(stmt)` | 一个模型对象 或 `None` | 单条 → 判 404 |

**PATCH 的部分更新**：

```python
data = payload.model_dump(exclude_unset=True)   # 只含客户端真的传了的字段
for key, val in data.items():                   # dict 直接 for 只给 key！
    setattr(todo, key, val)
db.commit()
db.refresh(todo)
```

`exclude_unset=True` 是为了区分「没传」和「传了 False / None」——
`if done:` 会把 `False` 当成没传。

**response_model 已经负责 ORM → dict 的转换**：`TodoRead` 有
`model_config = ConfigDict(from_attributes=True)`，路由里直接 `return todo` 即可，
不要手工 `schemas.TodoRead(id=todo.id, ...)` —— 加字段时会漏。

### 补充提问 1 · 已经声明 `response_model`，为什么还要 `return` 构造对象？

**提问原话**：「auth.py 里实现登录和刷新已经写了 `response_model=schemas.TokenPair`，
为啥还要 `return schemas.TokenPair(...)`，我不是很理解。」

`response_model` 不生产数据，它只做「出口检查 + 说明书」：

| 职责 | 说明 |
|------|------|
| OpenAPI 文档 | Swagger 的响应示例、字段类型从这里来 |
| 响应校验 | 返回的东西不符合 → `ResponseValidationError` |
| 字段白名单 | `UserRead` 没有 `password_hash`，多返回的字段会被过滤 |
| 序列化 + 默认值 | 转 JSON；`token_type` 这类默认值在校验时补上 |

最硬的证据：`get_todo` 返回 `ScalarResult` 时，`response_model=TodoRead` 就在，
但它没能把 `ScalarResult`「变」成 `TodoRead`，只会报
`ResponseValidationError: 'id': Field required, input: <ScalarResult>`。

**前端类比**：TypeScript 的返回类型标注不会替你创建对象，函数体还得 `return`：

```ts
function login(): TokenPair {
  return { accessToken, refreshToken }   // 标注只是合同
}
```

**为什么这里要构造**：两个 token 是两个函数调用现造的字符串，不像 `todo` 那样背后
有一个现成 ORM 对象（靠 `from_attributes` 自动读属性），所以必须装进某种结构。
两种写法等价：

```python
return schemas.TokenPair(access_token=..., refresh_token=...)   # Pydantic 实例：类型检查
return {"access_token": ..., "refresh_token": ...}              # dict：短，默认值由 response_model 补
```

最终采用 dict 写法，`token_type` 由 `TokenPair` 的默认值在校验时补上。
**要不要构造，取决于手里已经有什么，而不是 response_model 有没有声明。**

### 补充提问 2 · `=` 什么时候加空格？

**提问原话**：「是只有变量赋值才加吗，剩下的场景统统不加吗？」

准确说：**「绑定一个名字」加空格，「给参数起个名字」不加**。

| 场景 | 写法 | 空格 |
|------|------|------|
| 普通赋值 | `x = 1` | ✅ |
| 增强赋值 | `count += 1` | ✅ |
| 类型注解赋值 | `x: int = 1` | ✅ |
| 元组解包 | `a, b = 1, 2` | ✅ |
| 函数调用关键字参数 | `User(username="a")` | ❌ |
| 函数定义默认值（无注解） | `def f(x=1):` | ❌ |
| 函数定义默认值（**有注解**） | `def f(x: int = 1):` | ✅ |
| lambda 默认值 | `lambda x=1: x` | ❌ |

反直觉点：同样在 `def` 里，有没有类型注解决定了要不要加空格。

### 补充 · 并发注册的兜底（生产细节）

「先查重 → 再插入」是两步，两个并发请求可能同时通过查重、同时插入，
其中一个触发数据库唯一约束 → `IntegrityError` → 默认变成 500。

修法：让数据库约束做最终裁判，并接住异常：

```python
try:
    db.commit()
except IntegrityError:
    db.rollback()                  # 必须！失败事务不清掉，后续查询会 PendingRollbackError
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="username already taken",
    ) from None                    # 不把数据库原始错误栈暴露出去
```

`IntegrityError` 是笼统的（外键、非空、其他唯一约束都抛它）；这张表只有 username
一个唯一约束，所以可以放心当 409 处理。预检查留不留都行：留 = 常见情况走快路径，
不留 = 只剩数据库一条真理来源。

---

## 四、练习 ↔ 知识点映射

| Task | 检查点 | 对应知识点 |
|------|--------|-----------|
| 1A config.py | 环境变量优先 + 默认值 + reload | 配置集中、依赖树根 |
| 1A database.py | engine/SessionLocal/get_db、连接归还 | 生成器依赖、连接池 |
| 1B models.py | password_hash 非空 + String(255) | Mapped 类型注解决定可空性 |
| 1B schemas.py | 72 上限、UserRead 白名单、TodoCreate 无 user_id | Pydantic 约束、响应模型即白名单 |
| 1B Alembic | autogenerate 出两张表并 upgrade | 迁移=数据库的 Git |
| 1C deps.py | auth_error + get_current_user | 401 头、token 类型校验 |
| 1C auth.py | 注册 409 / 登录 form / 刷新 | OAuth2 password flow、双 token |
| 1C todos.py | 所有权 404、`db.scalar`、`exclude_unset` | IDOR 防御、ORM 查询 |
| 1C main.py | 全部 30 条端到端断言 | 分包组装 |

---

## 五、本次纠错全记录（Task 1C）

### 问题 1：`where(id == todo_id, user_id == current_user.id)`

- **现象**：`NameError: name 'user_id' is not defined`，通过 TestClient 冒出来；
- **原因**：
  - `user_id` 在当前作用域、全局、内置里都找不到 → NameError；
  - `id` 是 **Python 内置函数**（`id(obj)` 返回内存地址）→ 不报错，`id == todo_id` 静默为 `False`，SQL 变成 `WHERE false`；
  - 类属性不在名字查找链里，必须显式 `models.Todo.user_id`；
- **对应知识点**：名字解析 LEGB；Vue 里 `this.userId` vs 裸 `userId`；
- **解决**：所有列写成 `models.Todo.xxx`；
- **Claude 的锅**：练习 docstring 里的伪代码没带 `models.Todo.` 前缀，被照抄后直接踩坑。已修正提示文本。
- **顺带记**：`id / type / list / dict / all / any / sum / max / min / filter / next / input` 都是内置名字，裸用不报错但拿到的是内置对象。

### 问题 2：构造了语句却没存，`db.scalars(select)`

- **现象**：`ArgumentError: Executable SQL or text() construct expected, got <function select at 0x...>`；
- **原因**：`select(...)` 的结果被丢掉，`db.scalars(select)` 传入的是 `from sqlalchemy import select` 的函数对象；
- **对应知识点**：学习项 6「构造 ≠ 执行」；
- **解决**：`stmt = select(...)`，再 `db.scalar(stmt)`。

### 问题 3：`db.scalars` 当成单条查

- **现象**：`ResponseValidationError: missing id/title/done/user_id, input: <ScalarResult object>`；
  且 `if todo is None` 永远不成立；
- **原因**：`scalars` 返回结果集，不是模型对象，也不可能是 `None`；
- **解决**：单条查询用 `db.scalar(stmt)`。

### 问题 4：`for key, val in data:`（data 是 dict）

- **现象**：`ValueError: too many values to unpack (expected 2)`；
- **原因**：直接遍历 dict 拿到的是 key，`"done"` 是 4 个字符的字符串，塞不进两个变量；
- **对应知识点**：dict 遍历 `/ .items()`（学习项 9/10 同款错）；
- **解决**：`for key, val in data.items():`。

### 问题 5：`update_todo` 漏了 404 判断

- **现象**：`AttributeError: 'NoneType' object has no attribute 'done'`；
- **原因**：`db.scalar` 查别人的 todo 返回 None，接着 `setattr(None, "done", True)`；
- **解决**：`scalar` 之后统一

```python
if todo is None:
    raise HTTPException(404, "todo not found")
```

### 问题 6：`delete_todo` 也是 `scalars`

- **现象**：`UnmappedInstanceError: Class 'ScalarResult' is not mapped`；
- **原因**：`setattr` 能往任意对象挂属性所以没报，直到 `db.refresh()` 拿 `ScalarResult` 去问 SQLAlchemy「这是哪张表」才炸；
- **解决**：同样换 `db.scalar`。

### 问题 7：注册提示拼写错误（测试绿没发现）

- **现象**：`main.py` 全绿，但跑真实请求看到的响应是
  `{"detail": "useranme alerady taken"}`；
- **原因**：测试只断言 `r.status_code == 409`，没看 `detail` 的内容；
- **解决**：两处都改成 `"username already taken"`；
- **教训**：**测试绿 ≠ 无 bug**（第三次 —— 学习项 13 的 verify 返回值丢失、
  学习项 16 的哨兵被写成 `"null"`）。测试只覆盖它断言过的东西，
  用户可见的字符串要自己核对。

> **这一串错误的共同根**：以为「手里拿到的东西」和「实际拿到的东西」一样。
> 每次报错都先读最后一行异常类型 + 信息，它通常直接把答案写出来了（`got <function select>`、`input: <ScalarResult>`、`'NoneType'`）。

---

## 六、踩坑速查表

| 错误写法 | 报错 | 正确写法 |
|----------|------|----------|
| `.where(id == todo_id)` | 不报错，永远查不到（WHERE false） | `.where(models.Todo.id == todo_id)` |
| `.where(user_id == ...)` | `NameError: name 'user_id' is not defined` | `.where(models.Todo.user_id == ...)` |
| `select(...)` 不赋值，`db.scalars(select)` | `ArgumentError ... got <function select>` | `stmt = select(...)` → `db.scalar(stmt)` |
| 单条用 `db.scalars(stmt)` | `ResponseValidationError` / 永远不 404 | `db.scalar(stmt)` |
| `for k, v in data:`（data 是 dict） | `ValueError: too many values to unpack` | `for k, v in data.items():` |
| `setattr(None, ...)` | `AttributeError: 'NoneType' object has no attribute ...` | 先判 `if todo is None: raise 404` |
| `db.refresh(ScalarResult)` | `UnmappedInstanceError: ... not mapped` | 传模型对象 |
| 手工 `schemas.TodoRead(id=..., ...)` | 不漏但容易忘字段 | `return todo`（`from_attributes`） |
| 以为声明了 `response_model` 就不用产出数据 | 不报错，但逻辑错 / 500 | `response_model` 只校验和序列化，数据要自己 return |
| `db.commit()` 失败不 `rollback` | 后续查询 `PendingRollbackError` | `except IntegrityError: db.rollback()` |
| 用户可见字符串写错（`useranme`） | 测试绿但接口文案错 | 断言 `detail`；真实请求看响应 |

---

## 七、常用命令

```bash
# 均在仓库根目录 backend_ai 下执行
.venv/bin/python "4工程化/阶段项目-工程化TodoAPI/config.py"
.venv/bin/python "4工程化/阶段项目-工程化TodoAPI/database.py"
.venv/bin/python "4工程化/阶段项目-工程化TodoAPI/models.py"
.venv/bin/python "4工程化/阶段项目-工程化TodoAPI/schemas.py"
.venv/bin/python "4工程化/阶段项目-工程化TodoAPI/security.py"
.venv/bin/python "4工程化/阶段项目-工程化TodoAPI/main.py"      # Task 1C 端到端

# Alembic（在项目目录内）
cd "4工程化/阶段项目-工程化TodoAPI"
../../.venv/bin/alembic current
../../.venv/bin/alembic upgrade head
```

---

# Task 2 · Redis 缓存层（cache.py + 路由接入）

## 一、cache.py 设计

| 层 | 内容 |
|----|------|
| key 设计 | `todo:{user_id}:{todo_id}` 单条、`todos:user:{user_id}` 列表 —— **user_id 写进 key**，命中即已授权，不可能绕过所有权检查 |
| 三种返回值 | `CACHE_MISS`（object() 标记，key 不存在）/ `None`（哨兵，确认不存在）/ `dict`·`list`（命中） |
| `set_json` | `json.dumps` + `set(ex=ttl)`；`value=None` 就是写哨兵（`"null"` 字符串） |
| TTL | 单条/列表 300s；哨兵 60s（确认不存在，短 TTL 防止数据后来被创建了还一直 404） |
| `delete(*keys)` | 一次删多个，返回删除个数 |

**为什么 `CACHE_MISS` 不能和 `None` 混用**：`None` 是「查过，确认不存在」，`CACHE_MISS` 是「没查过」。混用会让不存在的 id 每次都查库（缓存穿透）。

## 二、路由接入（routers/todos.py）

### 读路径 Cache-Aside

```python
key = cache.todo_key(current_user.id, todo_id)
cached = cache.get_json(key)
if cached is not cache.CACHE_MISS:   # 命中（含哨兵）
    if cached is None:
        raise HTTPException(404)      # 哨兵命中，不查库
    return cached                     # dict，直接返回
# 未命中 → 查库
todo = db.scalar(select(...).where(id, user_id))
if todo is None:
    cache.set_json(key, None, ttl=cache.TTL_MISSING)   # 先写哨兵，再 404
    raise HTTPException(404)
data = schemas.TodoRead.model_validate(todo).model_dump()  # ORM → dict
cache.set_json(key, data)
return data
```

关键点：
- 判断必须 `is not cache.CACHE_MISS`，**不能** `if cached:` —— 空列表 `[]` 是合法结果但 falsy，会被误判成未命中。
- 查库步骤手写、不复用 `_get_owned_todo`：helper 查不到直接 raise，拿不到「查不到」分支去写哨兵。
- ORM 对象不能进 Redis（`json.dumps` TypeError），先 `TodoRead.model_validate(todo).model_dump()`。

### 写路径：先 commit，再删缓存

| 操作 | 删哪些 key | 为什么 |
|------|-----------|--------|
| POST | `todos:user:{uid}` | 列表变了；单条 key 本来不存在 |
| PATCH | `todo:{uid}:{id}` + `todos:user:{uid}` | **两个 key 都装过这条数据的副本** |
| DELETE | `todo:{uid}:{id}` + `todos:user:{uid}` | 不删单条 → 删完还能从缓存读到「幽灵 todo」 |

规则记法：**不是删「这条数据的 key」，而是删「所有装过这条数据的 key」。**

## 三、探底问答

| 问题 | 回答 | 结论 |
|------|------|------|
| `get_json` 三种返回值分别怎么处理 | `CACHE_MISS` 查库、`None` 直接 404、`dict` 直接返回 | ✅ 正确 |
| PATCH 后除了单条 key 还要删哪个、为什么 | 猜到「user 那条」列表，但**不知道原因** | ❌ 补讲：列表缓存里是完整副本 |

## 四、纠错全记录（用户手写 → Claude 重写）

| # | 现象 | 原因 | 知识点 |
|---|------|------|--------|
| 1 | `elselif` | 拼写错误 → SyntaxError；还专门问「正确的是啥」 | `else` + `if` = `elif` |
| 2 | `cache = cache.get_json(key)` 后 `cache.CACHE_MISS` 报 AttributeError | **变量名把模块覆盖**（同名遮蔽） | 模块名不要当变量名，用 `cached` |
| 3 | `db.get(todo_id)` | ① 丢掉 `user_id` 过滤 = **IDOR 越权**（A 能读 B 的 todo）；② 签名应为 `db.get(实体类, 主键)` | 复习第三阶段 IDOR；db.get 用法 |
| 4 | `cache.set_json(key, todo, ...)` 存 ORM 对象 | `json.dumps(Todo)` → TypeError | ORM → `model_validate().model_dump()` |
| 5 | `elif cache is None` | `cache` 是模块，永远不为 None，哨兵分支死代码；未命中时把 `CACHE_MISS` 对象 return 出去 → ResponseValidationError | 哨兵分支必须比较 `cached` |
| 6 | 末尾 `return cache_todo` | 未命中查库后也会走到，逻辑分叉不闭合 | 三条路各自 return |
| 7 | `return dict` | `dict` 是内置类型不是变量 | 返回值要返回数据本身 |

用户明确说「你直接把代码写好」后，Claude 完整实现并逐行讲解；`db.get` 的 IDOR 问题用户跳过了提问，由 Claude 直接给出答案。

## 五、端到端验证（uvicorn :8099 + curl + redis-cli，11 步全过）

| 步骤 | 结果 | 验证点 |
|------|------|--------|
| 首次 GET 单条 | Redis 出现 key，ttl=300 | 未命中查库回填 |
| 二次 GET | 200 | 命中 |
| GET 列表 | 列表 key 回填 ttl=300 | 列表读路径 |
| PATCH | 两个 key 都存在=0 | 写时删缓存 |
| PATCH 后 GET | 标题是「改」 | 回填新值 |
| B 读 A 的 todo | 404，B 名下哨兵 `null` ttl=60 | 所有权 + 哨兵 |
| B 再读 | 404 | 哨兵命中不查库 |
| DELETE | 两个 key 都消失 | 删除路径 |
| 删后 GET | 404，哨兵 ttl=60 | 删除后哨兵 |
| 空列表 | `[]` 进缓存 ttl=300 | falsy 不误判 |

验证脚本：`/tmp/task2_e2e.sh`（临时文件，不入库）。

## 六、踩坑速查

| 错误写法 | 报错/后果 | 正确写法 |
|---------|----------|---------|
| `elselif` | SyntaxError | `elif` |
| `cache = cache.get_json(key)` | AttributeError（模块被覆盖） | `cached = cache.get_json(key)` |
| `if cached:` 判未命中 | 空列表 [] 每次穿透查库 | `if cached is cache.CACHE_MISS:` |
| `db.get(todo_id)` | IDOR 越权 / 参数错 | `select().where(id==, user_id==)` |
| `set_json(key, todo)` | TypeError: not JSON serializable | `TodoRead.model_validate(todo).model_dump()` |
| PATCH 只删单条 | 列表挂旧值 5 分钟 | 单条 + 列表一起删 |
| 先删缓存再 commit | 未命中查库回填旧值 | **先 commit 再删** |

## 七、常用命令（Task 2）

```bash
cd "4工程化/阶段项目-工程化TodoAPI"
../../.venv/bin/python cache.py          # cache.py 自测
../../.venv/bin/uvicorn main:app --port 8099
redis-cli -n 0 --scan --pattern 'todo*'
```

---

# Task 3 · pytest 测试体系

## 一、测试分层：这 32 个测试是什么级别

| 层级 | 是什么 | 我们有没有 |
|------|--------|-----------|
| 单元测试 | 单个函数，外部依赖全 mock | 基本没有（测的都是接口） |
| **集成测试** | 多个真实组件一起跑（API + DB + Redis） | ✅ 本项目全部 |
| 端到端 E2E | 真实浏览器/网络/部署环境 | 没有（那是 Task 4/5 的事） |

`TestClient` 是**进程内**调用 ASGI app：不走网络、不起 uvicorn，但路由、依赖注入、中间件、数据库、Redis 全是真的。所以它属于集成测试，不是单元测试。

## 二、测试环境隔离（最重要的知识点）

```
开发环境                     测试环境
eng_todo_db          →      eng_todo_test_db
Redis db 0           →      Redis db 14
```

实现方式有两层：

1. **环境变量 + import 顺序**：`conftest.py` 在所有业务 import 之前写
   `os.environ["DATABASE_URL"] = ...`，因为 `config.py` 是「import 那一刻」读环境变量，之后再改环境变量没用。
2. **`app.dependency_overrides[get_db] = override_get_db`**：依赖注入的替换点，`key` 必须是函数对象，`yield` 后要 `clear()`（app 是全进程单例）。

## 三、fixture 设计

| fixture | scope | 作用 |
|---------|-------|------|
| `prepare_database` | session, autouse | 开始：drop_all + create_all；结束：drop_all + dispose |
| `clean_data` | function, autouse | 每个测试前 TRUNCATE todos + flushdb |
| `client` | function | 覆盖 get_db + TestClient，结束 clear |
| `db_session` | function | 测试自己直连测试库（验缓存命中用） |
| `auth` / `other_auth` | session | 只注册+登录一次，返回 headers / user_id |

### 一个必须理解的冲突：scope 不匹配

- `auth` 是 **session** scope：token 里的 user_id 固定。
- 如果 `clean_data` 每个测试都 `TRUNCATE users`，第二个测试开始时该用户已不存在 → 所有登录测试 401。
- 解决：**只清 todos，不清 users**。user 行留着无害，会话结束 drop_all 一并清掉。
- 另一条路：auth 改 function scope，每测试注册一次 —— 慢（bcrypt cost=12 每次约 0.25s）、彻底隔离。这里选性能。

> 通用规则：session-scoped fixture 依赖的数据，不能被 function-scoped fixture 清掉。

## 四、怎么证明「真的命中了缓存」

缓存测试最容易写成「测了等于没测」。本项目的做法：

1. GET 一次 → 缓存回填
2. **绕过 API**，用 `db_session` 直接 `UPDATE todos SET title = '数据库里的新标题'`
3. 再 GET 一次：
   - 返回**旧标题** → 读的是缓存 ✅
   - 返回新标题 → 根本没走缓存 ❌

同样的思路可以验哨兵、验双删（`redis_client.exists(key) == 0`）、验 TTL（`0 < ttl <= TTL`）。

## 五、32 个测试覆盖了什么

| 文件 | 数量 | 覆盖 |
|------|------|------|
| test_smoke.py | 4 | 地基自检：401、auth fixture、测试间隔离 |
| test_auth.py | 8 | 注册（成功/重复 409/短密码 422）、登录（成功/错密码 401 + WWW-Authenticate/不存在同提示）、刷新（成功/access 冒充 refresh 401）、未认证 401 |
| test_todos.py | 9 | CRUD、伪造 user_id 被忽略、只列自己的、exclude_unset、done=False 生效、204 无 body、IDOR 读改删全 404 且 B 数据未动 |
| test_cache.py | 11 | 单条/列表回填、命中（改库验证）、空列表缓存、PATCH/DELETE 双删、CREATE 删列表、哨兵（值 "null"、ttl、二次 404）、越权哨兵写在自己 key 空间 |

## 六、运行方式

```bash
cd "4工程化/阶段项目-工程化TodoAPI"
../../.venv/bin/python -m pytest tests/ -q        # 必须 -m pytest，cwd 进 sys.path 才能 import 项目模块
../../.venv/bin/python -m pytest tests/test_cache.py -v
```

为什么用 `python -m pytest` 而不是直接 `pytest`：`-m` 会把当前目录加进 `sys.path`，`import cache / models` 才能找到。直接跑 `pytest` 时 pytest 只把 tests/ 目录加进去，导入会失败。

---

# Task 4 · Nginx 反向代理

## 一、最终配置在干什么

```
浏览器 ──> nginx :8088
            ├─ /api/...  ──转发──> upstream todo_api ──轮询──> uvicorn :8001 / :8002
            └─ 其他路径   ──try_files──> nginx/static/（找不到就回 index.html）
```

| 配置块 | 作用 | 关键点 |
|--------|------|--------|
| `upstream todo_api` | 两个后端实例 | 必须写在 `http {}` 里；默认轮询 |
| `location /api/` | API 转发 | `proxy_pass http://todo_api/;` 末尾 `/` 剥前缀 |
| `proxy_set_header` 三件套 | 透传客户端信息 | `Host $host` / `X-Real-IP $remote_addr` / `X-Forwarded-For $proxy_add_x_forwarded_for` |
| `location /` | 静态文件 + SPA 回退 | `try_files $uri $uri/ /index.html;` |

## 二、知识点

### 1. proxy_pass 末尾的 `/` 是「替换」而不是「追加」

- `proxy_pass http://todo_api/;` → `/api/auth/login` 的后端路径 = `/auth/login`（前缀被 `/` 替换）
- `proxy_pass http://todo_api;`（无尾斜杠）→ 后端收到 `/api/auth/login`

### 2. 三个透传头的作用

| 头 | 不配的后果 |
|----|-----------|
| `Host $host` | 后端看到 `127.0.0.1:8001`，暴露内网结构；生成绝对 URL / 校验域名时会错 |
| `X-Real-IP $remote_addr` | 后端拿不到真实客户端 IP（日志、限流、风控全失效） |
| `X-Forwarded-For $proxy_add_x_forwarded_for` | 同上；用 `$proxy_add_x_forwarded_for` 而不是 `$remote_addr` 是为了**追加**经过的代理链 |

### 3. try_files 的三个参数

`try_files $uri $uri/ /index.html;`
1. `$uri` —— 原样路径的真实文件（`/hello.txt`、`/assets/app.js`）
2. `$uri/` —— 当目录找 index
3. `/index.html` —— 前导斜杠是**内部重定向**，让请求重新走 location 匹配；写 `index.html` 没有前导斜杠会被当成相对文件名

### 4. 为什么 `/api/nope` 返回 404 JSON 而不是 index.html

location 匹配规则：`/api/` 是更长的前缀，`/api/nope` 先命中它 → 转发给后端 → 后端 404。不会落到 `location /` 的 SPA 回退。这是正确行为（前端路由不该吞掉 API 的 404）。

### 5. upstream 轮询的验证方式

`wrapped_app.py` 每个实例往响应里加 `X-Instance: api-1/api-2`，连续 6 次请求观察两个实例都出现。

## 三、验证脚本架构（check.py）

```
prepare_tables()     python -c 建测试库表（pytest 结束会 drop）
flush_test_redis()   清 Redis db 14
start_uvicorn(8001,"api-1") / (8002,"api-2")
nginx -t             先语法检查，失败直接返回
nginx 启动 :8088
12 项断言：静态 4 / API 转发 5 / 请求头 3 / 轮询 1
finally: nginx -s stop + 终止 uvicorn + 清 Redis
```

## 四、本次纠错全记录

| # | 现象 | 原因 | 正确写法 |
|---|------|------|---------|
| 1 | nginx -t：`line 41 unexpected "}"` | L40 `server 127.0.0.1:8002` **缺分号**，报错行号漂到下一行 | `;` 结尾 |
| 2 | `unknown directive "ocation"` | 拼写错误（与学习项 19 的 `serve` 同款） | `location` |
| 3 | L66 proxy_pass 缺分号 | 同 #1 | `;` |
| 4 | L82 try_files 缺分号 | 同 #1 | `;` |
| 5 | proxy_pass 指向 `127.0.0.1:8000/` | 8000 没人监听（实例是 8001/8002）→ 502；直连单实例还会让 upstream 失效 | `http://todo_api/` |
| 6 | 三个 proxy_set_header 全没写 | Host 暴露内网端口；X-Real-IP / XFF 为 None | 三件套补齐 |
| 7 | `try_files index index.html` | `index` 被当成文件名；`index.html` 缺前导 `/` | `$uri $uri/ /index.html` |
| 8 | `X-Request-IP` 头名写错 | 后端读的是 `x-real-ip`；HTTP 头名是关键契约，大小写不敏感但名字必须对 | `X-Real-IP` |
| 9 | L68 改完头名后缺分号 | nginx 报 `line 69 invalid number of arguments` —— 又是报错行上一行的问题（第 4 个分号） | `;` |

**分号问题本轮出现 4 次**，「报错行上一行缺 `;`」这条规律必须记住。

## 五、常用命令

```bash
cd "4工程化/阶段项目-工程化TodoAPI"

# 语法检查（不起服务）
nginx -t -p "$PWD/nginx" -c "$PWD/nginx/nginx.conf"

# 完整验证（自动起 2 uvicorn + nginx，结束自动清理）
../../.venv/bin/python nginx/check.py
```

---

# Task 5 · CI/CD（GitHub Actions + PostgreSQL + Redis）

## 一、workflow 结构

`.github/workflows/project-ci.yml`

```
on: push(master) / pull_request / workflow_dispatch
job test（ubuntu-latest）
  services:
    postgres:16  → localhost:5432，POSTGRES_DB=eng_todo_test_db，health: pg_isready
    redis:7      → localhost:6379，health: redis-cli ping
  env:
    DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/eng_todo_test_db
    REDIS_URL=redis://127.0.0.1:6379/14
  steps:
    checkout → setup-python 3.12（pip cache）→ pip install → ruff lint → pytest tests
```

## 二、知识点

### 1. services = 和 runner 同网络的附属容器

GitHub 的 runner 是临时 VM，里面没有 PG / Redis。`services` 让 GitHub 用 Docker 起这些容器，并映射到 runner 的 localhost。所以 `DATABASE_URL` 直接写 `127.0.0.1:5432`。

### 2. health check 解决「容器起来了但还没就绪」

PostgreSQL 从容器启动到能接受连接有几秒空窗。不配 health check，steps 可能先跑、连库失败。`options: --health-cmd ...` 让 GitHub 等健康再开始。

### 3. 测试代码要「环境无关」——conftest 的 setdefault

本地：

```python
os.environ["DATABASE_URL"] = "postgresql+psycopg:///eng_todo_test_db"   # ❌ 覆盖一切
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg:///eng_todo_test_db")  # ✅
```

`setdefault` 的语义：**有值就不动，没值才填默认**。CI 里 workflow 的 `env` 已经设好，测试不需要知道自己在哪运行。这是「测试能在本地和 CI 跑同一套」的关键。

### 4. lint 放在 test 前面

ruff（E9/F63/F7/F82 = 语法级、未定义名字；F401 = 未使用 import）几十毫秒跑完，能快速失败。测试要起服务、连库，慢得多。

### 5. pip cache

`setup-python` 的 `cache: pip` + `cache-dependency-path` 指向 requirements.txt，依赖没变时直接命中缓存，省 10~20 秒。

### 6. CI 的 runner 是用完即焚的

所以部署必须靠 SSH / 镜像 / self-hosted runner 把产物送出去，不能指望机器上留下的东西（学习项 20 讲过）。

## 三、验证

- 本地：`ruff check` 通过、32 个测试通过
- 远程：push 后 GitHub Actions run `45178185293`，**34 秒**全部步骤 success
  - 验证方式：公开 API `https://api.github.com/repos/lr6/backend_ai/actions/runs`，不需要 gh / token

## 四、本 Task 的额外修正

| 问题 | 原因 | 修正 |
|------|------|------|
| conftest 强行覆盖 env | CI 里的 DATABASE_URL 会被盖成本机 socket | `os.environ.setdefault` |
| ruff F401（models 未使用） | `import models` 是**副作用导入**（注册表到 metadata），变量本身不用 | `# noqa: F401`（alembic/env.py、conftest.py） |
| 依赖无清单 | CI 空机器不知道装什么、装哪个版本 | `requirements.txt` 锁版本（bcrypt 必须 4.0.1） |

## 五、常用命令

```bash
# 本地模拟 CI 的 lint
cd "4工程化/阶段项目-工程化TodoAPI"
../../.venv/bin/ruff check --select E9,F63,F7,F82,F401 .

# 看 GitHub 上的真实运行（公开 API）
curl -s "https://api.github.com/repos/lr6/backend_ai/actions/runs?per_page=5" | jq '.workflow_runs[] | {name, status, conclusion, head_sha}'
```
