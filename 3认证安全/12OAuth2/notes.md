# 12 FastAPI OAuth2 — 学习笔记

> 第三阶段：认证与安全 · 学习项 12
> 完成日期：2026-11-09
> 练习：`practice.py`（5 个练习全部通过）
> 依赖补充：`python-multipart`（`OAuth2PasswordRequestForm` 解析表单必需）

---

## 一、知识点讲解

### 1. token 放在请求的哪里：`Authorization: Bearer <token>`

探底时答成「放在 payload 里」——混淆了 **token 内部结构** 和 **HTTP 请求位置**：

- **payload** 是 JWT 内部的第二段（`Header.Payload.Signature`），属于 token 自身；
- token 本身是一整串字符串，需要前端装进 HTTP 请求。

HTTP 请求可以装数据的位置：

| 位置 | 例子 | 是否合适 |
|------|------|---------|
| 路径 | `/todos/123` | ❌ 用来定位资源 |
| 查询参数 | `/todos?token=xxx` | ⚠️ 能跑，但不规范 |
| 请求体 | `{"token": "xxx"}` | ❌ GET 没有 body |
| **请求头** | `Authorization: Bearer eyJ...` | ✅ 标准做法 |

- `Bearer` = OAuth2 规定的认证方案名（持票人），与 token 之间是**一个空格**；
- Vue 里用拦截器统一加：

```js
axios.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
```

```python
# JS 发表单（登录接口用）
const params = new URLSearchParams()
params.append('username', username)
params.append('password', password)
axios.post('/login', params)   // Content-Type: application/x-www-form-urlencoded
```

### 2. 为什么 token 不放 query string

用户答不出，直接讲了两个理由：

1. **URL 到处都是记录点**：浏览器历史、服务器 access log、代理/CDN 日志、外链的 `Referer` 头。`?token=xxx` 等于把 token 抄进一堆日志；header 默认不进日志。
2. **URL 天生用于分享**：复制地址栏、发链接、截图都会带走 token。

一句话：**认证信息放 header，业务数据放 body，资源定位用 path。**

### 3. 中间件 vs Depends：公共逻辑放哪里

探底答「中间件」，方向对（公共逻辑要有公共位置），但 FastAPI 的答案是 **依赖注入**。

中间件不适合做认证的原因：

| 问题 | 说明 |
|------|------|
| 不知道哪些路由要登录 | 中间件跑在路由匹配之前，只能靠白名单/黑名单，容易漏 |
| 无法把 user 交给路由函数 | 只能塞 `request.state.user`，丢失类型提示与补全 |
| 错误处理不统一 | 手动返回 401 别扭，不如 `raise HTTPException` |
| Swagger 不参与 | 依赖能生成 Authorize 🔒 按钮 |

中间件适合**对所有请求一视同仁**的事：日志、计时、CORS、压缩。

**依赖可以套娃**，FastAPI 自动按顺序解析：

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),   # 依赖 1：读 header
    db: Session = Depends(get_db),         # 依赖 2：拿 Session
) -> User:
    ...

@app.get("/todos")
def list_todos(user: User = Depends(get_current_user)):
    ...
```

执行顺序：读 `Authorization` → 验 token → 查用户 → 注入路由参数。任何一步失败都在依赖里 `raise`，**路由函数不会执行**。

**为什么不用中间件 + 白名单**：`/login`、`/health` 这类公开路由，Depends 方案天然不写就不保护；中间件方案默认全保护，反而要维护白名单，容易漏。

### 4. 登录接口：`OAuth2PasswordRequestForm` 收表单不收 JSON

```python
from fastapi.security import OAuth2PasswordRequestForm

@app.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    # form.username / form.password
    return {"access_token": token, "token_type": "bearer"}
```

- 期望 Content-Type 是 `application/x-www-form-urlencoded`，不是 `application/json`；
- 这是 OAuth2 规范要求，同时也是 Swagger Authorize 按钮的工作方式；
- 响应字段名必须是 `access_token` + `token_type`；
- `OAuth2PasswordBearer(tokenUrl="/login")` 里的 `tokenUrl` 告诉 Swagger「去哪个地址换 token」。

前端直接 `axios.post('/login', { username, password })` 会 422（发的是 JSON）。

### 5. `get_current_user` 的标准实现

```python
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise auth_error() from None

    if payload.get("type") != "access":     # 防止 refresh 冒充 access
        raise auth_error()

    user = db.get(models.User, payload.get("user_id"))
    if user is None:
        raise auth_error()
    return user
```

401 统一构造（练习中最终提取为 `auth_error()` 函数）：

```python
def auth_error(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
```

要点：

- **`WWW-Authenticate: Bearer` 是 401 的配套规范**，告诉客户端用 Bearer 方案重新认证；
- **三种失败合成同一句提示**（过期/签名错/用户不存在），故意不区分——否则等于告诉攻击者「密钥猜对了」；
- 未带 `Authorization` 头时 `OAuth2PasswordBearer` 默认 `auto_error=True`，自己返回 401，函数不会执行。

### 6. 401 vs 403

| 状态码 | 含义 | 场景 |
|--------|------|------|
| **401** Unauthorized | 「你是谁？」——未认证/认证失败 | 没带 token、过期、签名错 |
| **403** Forbidden | 「我知道你是谁，但你不能做」 | 普通用户删别人文章 |

401 的名字叫 Unauthorized，实际语义是 Unauthenticated，属历史命名坑。

### 7. 双向 type 校验（真实漏洞）

`get_current_user` 必须检查 `type == "access"`。删掉后果：

- refresh token 有效期 30 天，且通常只能用于 `/refresh`；
- 一旦不检查，**refresh token 可直接当 access token 用 30 天**，短效 access 的设计失效；
- 对称地，`/refresh` 必须检查 `type == "refresh"`，否则 access token 也能换来新 token。

原则：**验证任何凭证时，都要检查「这个凭证是不是给这个用途的」。**

### 8. Router 级依赖

```python
admin_router = APIRouter(
    prefix="/admin",
    dependencies=[Depends(get_current_user)],   # 列表，可挂多个
)

@admin_router.get("/dashboard")
def admin_dashboard():        # 不用写 Depends，自动受保护
    ...
```

价值是**默认安全**：以后往该 router 新增路由，不会因为忘写 `Depends` 而暴露。

---

## 附：dict 的 `.` 与 `[]`（本次反复踩坑）

Python 里两套机制完全独立：

- `obj.attr` → 属性查找（`__getattribute__`）
- `obj[key]` → 下标查找（`__getitem__`）

`dict` 只实现了 `__getitem__`，所以只能 `d["key"]`；点访问只能拿到 dict 的方法（`d.get`、`d.items`），数据和方法**天然分家**。若允许点访问 key，会出现 `d.keys` 到底要方法还是 key `"keys"` 的歧义。

JS 对比：

| | 点访问 | 方括号/`get` |
|---|---|---|
| Python dict | 只能拿方法 | 只能拿数据 |
| JS `Map` | 只能拿方法 | 只能拿数据（数据在内部槽） |
| JS 普通对象 | **数据与方法共用命名空间** ← 歧义来源 | 同一点访问 |

- JS 普通对象没有真正解决冲突：`m.items = 42` 会覆盖方法；ES2022 才补了 `Object.hasOwn`；
- 干净解法是 `Map`（数据在内部槽，方法在 prototype）或无原型对象 `Object.create(null)`；
- 用户可控 key 用普通对象还可能有**原型污染**风险（`__proto__`），Map 不会。

ORM / Pydantic 对象能点访问，是因为类上真的定义了属性（`Mapped[int]` / Pydantic 字段）。

---

## 二、练习 ↔ 知识点映射

| 练习 | 内容 | 对应知识点 |
|------|------|-----------|
| 1 | `POST /login` 发 token | 表单 vs JSON、响应字段、`OAuth2PasswordRequestForm` |
| 2 | `get_current_user` | Depends 套娃、验签、type 检查、401 + `WWW-Authenticate` |
| 3 | `GET /me` 受保护路由 | 依赖注入把 user 交给路由、响应不回传密码 |
| 4 | `APIRouter(dependencies=[...])` | router 级依赖、默认安全 |
| 5 | `POST /refresh` 换 access | 双向 type 校验、凭证用途检查 |

---

## 三、练习纠错全记录

### 探底

| 问题 | 用户答案 | 判定 |
|------|---------|------|
| token 放在 HTTP 请求哪里 | 「放到 payload 里面」 | ❌ 混淆 token 内部结构与请求位置 |
| 用什么机制让公共逻辑生效 | 「中间件吗」 | ❌ 方向对（公共位置），机制错（应为 Depends） |
| 为什么 token 不放 query | 「不知道，想不出来」 | 直接讲解 |

### 练习 1：登录接口

**问题 A：按 username 用了 `db.get()`**

```python
user = db.get(form.username)     # ❌ 永远 None
```

- **现象**：合法用户也走 401 分支。
- **原因**：`USERS_DB` 的 key 是 id（int），username 只是 value 里的字段；`dict.get(key)` 只能按 key 查。
- **对应知识点**：dict key 与数据结构。
- **解决**：遍历 `db.values()` 比较 `u["username"]`，找到即 break；找不到走 401。

```python
user = None
for u in db.values():
    if u["username"] == form.username:
        user = u
        break
if user is None:
    raise HTTPException(401, "用户名或密码错误")
```

**问题 B：漏了密码校验**

- **现象/风险**：任何密码都能登录。
- **原因**：只判断用户存在，没有比较密码。
- **解决**：`if user is None or user["password"] != form.password: raise ...`（两个条件合成同一句 401，避免泄露用户名是否存在）。

**问题 C：dict 点访问（第 3 次）**

```python
u.username / user.id / user.role      # ❌ AttributeError
u["username"] / user["id"] / user["role"]   # ✅
```

### 练习 2：`get_current_user`

- 逻辑一次正确：`try/except JWTError`、type 检查、用户不存在检查、`WWW-Authenticate` 头。
- 讲评后的优化：db 的 key 就是 id，可以直接 `db.get(payload.get("user_id"))`，不必遍历。
- 细节：`payload["user_id"]` 缺字段会 `KeyError` → 500；改用 `.get()` 后变成 `db.get(None)` → None → 401。
- 因为已经遍历过 `db.values()` 找 username，这里差点又用循环；提示「key 是什么决定怎么查」后改成 `db.get`。

### 练习 3：`/me`

- **问题**：又写成 `current_user.id / current_user.username / current_user.role`（dict 点访问第 4 次）。
- **解决**：全部改方括号；返回 `{"id", "username", "role"}`，不带 password。
- **习惯**：函数参数标了 `dict`，就只用 `[]`。

### 练习 4：Router 级依赖

| 错误尝试 | 问题 |
|---------|------|
| 给 `admin_dashboard` 加 `Depends(get_current_user)` | 能过测试，但只是路由级，不是本题要考的 router 级 |
| 单独写一行 `APIRouter(prefix="/admin", dependencies=[...])` | 返回值没接住，创建后丢弃；生效的仍是原 `admin_router` |
| `app.include_router(admin_router, APIRouter)` | 第二个位置参数不存在，且 `APIRouter` 是类；会 TypeError |

**正确**：依赖挂到 `admin_router = APIRouter(prefix="/admin", dependencies=[Depends(get_current_user)])`，路由函数不写 Depends，include 恢复单参数。

**收获**：router 级依赖的价值是新增路由自动受保护（默认安全）。

### 练习 5：`/refresh`

从练习 2 复制后未逐行核对，连续 5 个问题：

| # | 错误 | 后果 | 正确 |
|---|------|------|------|
| 1 | `jwt.decode(body, ...)` | body 是 Pydantic 模型不是字符串 | `body.refresh_token` |
| 2 | `type != "access"` | refresh token 全被拒 | `type != "refresh"` |
| 3 | 只判断 `payload.get("user_id") is None` | 用户不存在但 claim 有值时漏检 | `user = db.get(...)`，`user is None` → 401 |
| 4 | `create_refresh_token(...)` | 发的是 refresh 不是 access | `create_access_token(...)` |
| 5 | `user["user_id"]` | user dict 无此字段 → KeyError → 500 | `user["id"]` |

还有一个**测试抓不到**的 bug：

```python
create_access_token(user["id"])      # 漏传 role，用默认 "user"
```

- alice 的 role 恰好是 `"user"`，与默认值相同，测试全绿；
- 若 bob（admin）换票，角色会被静默降级为 user；
- 与 11 JWT 的 `create_refresh_token(uid, "refresh")` 是同一类错误：**默认值往往是错的**。
- 纠正：`create_access_token(user["id"], user["role"])`。

### Review（测试全绿后）

| 问题 | 改法 |
|------|------|
| 401 写了三份，且练习 1 用魔法数字 401 | 提取 `auth_error(detail=...)` 函数（函数而非常量，每次新建实例） |
| `raise` 后还有 `else` | 提前 return，平铺 |
| `except JWTError: raise f401` 带异常链 | `raise ... from None` |
| `auth_error` 函数体缩进 6 空格 | 改为 4 空格 |
| 残留 `# TODO` | 删除 |

---

## 四、踩坑速查表

| 错误写法 | 现象 | 正确写法 |
|---------|------|---------|
| `Authorization: token` / 放 body | 401 | `Authorization: Bearer <token>` |
| 登录接口发 JSON | 422 | 发 form（`URLSearchParams` / `data=`） |
| `db.get(form.username)` | 永远 None | 遍历 `db.values()` 按 username 找 |
| `user.id`（user 是 dict） | AttributeError | `user["id"]` |
| `payload["user_id"]` 缺字段 | KeyError → 500 | `payload.get("user_id")` |
| `type != "access"` | refresh 可冒充 access | 必须检查 type |
| refresh 接口用 `type != "access"` | 合法 refresh 被拒 | 用 `type != "refresh"` |
| `jwt.decode(body, ...)` | 类型错误 | `jwt.decode(body.refresh_token, ...)` |
| `create_access_token(user["id"])` | 角色被默认值降级，测试可能绿 | 传 `user["role"]` |
| `raise` 后 `else` | 冗余 | 提前 return |
| `raise HTTPException(...)` 不带 `WWW-Authenticate` | 不标准 | `headers={"WWW-Authenticate": "Bearer"}` |
| router 依赖写在路由参数上 | 新路由忘写就裸奔 | `APIRouter(dependencies=[Depends(...)])` |
| `include_router(router, APIRouter)` | TypeError | `include_router(router)` |
| 缺 `python-multipart` | 启动即 RuntimeError | `pip install python-multipart` |

---

## 五、本章结论

- OAuth2 在 FastAPI 里 = `OAuth2PasswordBearer`（读 header）+ `OAuth2PasswordRequestForm`（收表单）+ `Depends` 链（验 token → 查用户 → 注入路由）；
- 认证是「部分路由才需要」的逻辑 → 用依赖注入按需挂载，而不是中间件全局拦截；
- 凭证检查必须**双向**：业务接口只认 access，换票接口只认 refresh；
- 请求凭证通过 header 传递，绝不放 URL；
- dict 与类实例的取值方式要分清：看到 `{}` 用 `[]`，看到类实例才用 `.`。
