# 14 CORS — 学习笔记

> 第三阶段：认证与安全 · 学习项 14
> 完成日期：2026-11-11
> 练习：`practice.py`（5 个练习全部通过）

---

## 一、知识点讲解

### 1. 同源策略（Same-Origin Policy）：浏览器拦，不是服务器拦

前端开发常碰到：Vite 跑在 `http://localhost:5173`，后端 FastAPI 跑在 `http://localhost:8000`，前端 `fetch` 后端接口就报跨域错。

- **Origin = 协议 + 域名 + 端口** 三者的组合，任一不同就算跨域；
- 同源策略是**浏览器**的安全机制：一个 origin 的 JS **默认读不到**另一个 origin 的响应；
- 关键认知：**请求其实发出去了，服务器也处理了、也回了响应，只是浏览器拦着不让 JS 读**。CORS 不是服务器"阻止请求"，而是服务器"回一个头告诉浏览器：这个源允许读"。

**前端类比**：CORS 是后端写给浏览器看的一张「放行名单」。前端代码一行不用改，改的是后端的响应头。

### 2. 简单请求 vs 预检（练习 1）

| | 简单请求 | 非简单请求 |
|---|---------|-----------|
| method | 只能是 GET / HEAD / POST | PUT / DELETE / PATCH 等 |
| 头 | 只能有安全头：accept、accept-language、content-language、content-type | 带 `Authorization` 等自定义头 |
| content-type | 只能 `application/x-www-form-urlencoded` / `multipart/form-data` / `text/plain` | `application/json` 等 |
| 流程 | **直接发**，只用响应头有无 `ACAO` 决定 JS 能否读 | 先发 `OPTIONS` **预检**，服务器放行才发真请求 |

**为什么是这几类算"简单"**：不是"没有副作用"，而是"**传统 HTML `<form>` 本来就能发的请求**"。`<form>` 从 90 年代起就只能 `GET`/`POST` + 那三种编码。这些能力浏览器认为风险可控 → 直接发。

而 `application/json`、`PUT`/`DELETE`、`Authorization` 头是**传统表单做不到的**，浏览器怕服务器被"不明请求"打懵，就先 `OPTIONS` 问一句"你允许吗"，服务器回 200 + 允许的头，才放真正请求过去。这就是**预检**。

> 所以：Todo 前端用 `fetch` 发 `Content-Type: application/json` 的 POST → **会触发预检**，因为 `application/json` 不在三种简单 content-type 里。

### 3. `CORSMiddleware` 参数（练习 2 / 4 / 5）

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],   # 精确匹配列表
    allow_origin_regex=r"http://localhost:\d+", # 正则匹配（动态端口）
    allow_methods=["*"],                        # ⚠️ 必须显式写，默认只有 GET
    allow_headers=["*"],                        # ⚠️ 必须显式写，默认空
    allow_credentials=True,                     # 允许带 cookie
    max_age=600,                                # 预检结果缓存 600 秒
)
```

| 参数 | 含义 | 坑 |
|------|------|-----|
| `allow_origins` | 精确字符串匹配的允许列表 | 不认正则；协议/域名/端口/末尾斜杠任一不同都不算命中 |
| `allow_origin_regex` | 用**正则**匹配 origin | 参数名别和上面搞混 |
| `allow_methods` | 预检时允许的方法 | 默认只有 GET，不写的话预检直接 400 |
| `allow_headers` | 预检时允许的头 | 默认空，不写 `Authorization` 预检直接 400 |
| `allow_credentials` | 允许响应带 cookie 的跨域 | True 时 `allow_origins` **绝不能 `*`** |
| `max_age` | 预检结果缓存时长（秒） | 缓存期内不发重复 OPTIONS |

### 4. 为什么 `allow_credentials=True` 时不能 `*`（练习 4）

cookie 由浏览器按**目标域名**自动附带、自动管理。evil.com 的页面一旦往 your-api.com 发请求，浏览器会**自动带上 your-api.com 的 cookie**（httpOnly cookie 也照带，因为 cookie 本来就不是 JS 主动读的）。

如果服务器回 `Access-Control-Allow-Origin: *` + `Access-Control-Allow-Credentials: true`，等于告诉浏览器"**任何网站的 JS 都能带着你的登录态调我**"——evil.com 的 JS 就能冒充你的身份操作。这就是 CSRF 的跨域放大版。

所以规范规定：带 credentials 时 `ACAO` 必须是**具体 origin（回显请求方）**，不能是 `*`。浏览器自己会校验——看到 `*` + credentials 组合**直接拒绝**，不用服务器操心。

### 5. `allow_origin_regex`：开发环境动态端口（练习 5）

Vite 端口可能在 5173 / 5174 之间跳，用正则一次性放行 `http://localhost:<任意端口>`：

```python
allow_origin_regex=r"http://localhost:\d+",
```

- Starlette 用 `re.fullmatch` **整串匹配**（不是 search），所以 `http://localhost:5173.evil.com` 不会命中；
- `https://localhost:5173`（协议不同）、`http://127.0.0.1:5173`（域名不同）、`http://evil.com` 都不会命中。

---

## 附：`in`/`not in` 后面的 `()` 和 `{}` 区别（本次主动提问）

用户提问：「`not in` 后面一会是 `()` 一会是 `{}`，为什么？」

**核心**：`in`/`not in` 是「成员判断」，跟**任何容器**都配合用，`()` 和 `{}` 只是两种容器，判断「在不在」时结果一样。

| 写法 | 类型 | 特点 | 成员判断速度 | JS 类比 |
|------|------|------|-------------|---------|
| `("get", "head", "post")` | tuple 元组 | 有序、不可变、允许重复 | O(n) | `arr.includes(x)` |
| `["a", "b"]` | list 列表 | 有序、可变、允许重复 | O(n) | `arr.includes(x)` |
| `{"a", "b"}` | set 集合 | 无序、自动去重 | **O(1)** 哈希 | `new Set([...]).has(x)` |

- method 用 `()`：固定小清单，tuple（不可变）是 Python 写常量的习惯；
- safe_headers 用 `{}`：语义是「一组被允许的值」，set 天然表达集合。

**必踩坑**：`{}` 只有在**里面有值**时才是 set；**空 `{}` 是 dict（字典）**！空 set 得写 `set()`。`{"a", "b"}` 是 set（只有值、无冒号），`{"a": True}` 就变 dict。

---

## 二、练习 ↔ 知识点映射

| 练习 | 内容 | 对应知识点 |
|------|------|-----------|
| 1 | 判断简单请求 | 简单请求三条件（method / 安全头 / content-type）、大小写不敏感 |
| 2 | 基础 CORSMiddleware | `add_middleware`、`allow_methods`/`allow_headers` 必须显式写、`max_age` |
| 3 | CORS 对账（纯逻辑） | `allow_origins` 精确字符串匹配，`in` 成员判断 |
| 4 | 带 cookie 的 CORS | `allow_credentials=True` + 不能 `*`（回显具体 origin） |
| 5 | 动态端口 | `allow_origin_regex` 正则匹配、raw 字符串 `\d` |

---

## 三、练习纠错全记录

### 探底（练习全绿后的两个检查问题）

| 问题 | 用户答案 | 判定 |
|------|---------|------|
| 什么时候发 OPTIONS 预检？`application/json` 的 POST 会触发吗？ | 「会触发，因为 application/json 不支持」 | ✅ 核心对；「副作用」说法需修正为「传统表单能发的请求」 |
| 为什么 credentials 时 `allow_origins` 不能 `*`？ | 「evil.com 带上你的 cookie 发请求，有危险」 | ✅ 危险点对；补「浏览器会直接拒绝 `*`+credentials」 |

### 练习 1：判断简单请求（3 个 bug）

**问题 A：method 大小写敏感**

```python
if method in ["get", "head", "post"]:   # ❌ "GET" 不命中
```

- **现象**：`("GET", [], None)` 期望 True，实际 False。
- **原因**：Python 字符串比较大小写敏感（和 JS `===` 一样）。
- **解决**：`method.lower() not in ("get", "head", "post")`。

**问题 B：`headers in [...]` 是「整个列表在不在」，不是「每个元素在不在」**

```python
if headers in ["accept", "accept-language", ...]:   # ❌ 永远 False
```

- **现象**：`["Accept", "Accept-Language"]` 这种该放行的全被拦。
- **原因**：`headers` 是 list，`in` 判断「这个 list 对象」是否等于安全列表里的某个**字符串**——list 不可能等于 string。
- **解决**：遍历每个 header，逐个 `h.lower() not in safe_set`（对应 JS `.every()`）。顺手 `.lower()` 处理大小写。

**问题 C：`or` 短路 + `None` 漏判**

```python
if content_type or content_type in [...]:   # ❌
```

- **现象/风险**：`"application/json"` 是非空字符串（真值），`or` 短路直接放行，后面的判断不执行。
- **另一个坑**：`content_type = None` 时 `None or (None in [...])` = `False`，但 None 表示"没带 content-type 头"，**应该算满足**。
- **解决**：`if content_type is not None and content_type not in (...)`。

### 练习 2：基础 CORS 应用

**问题：忘 `return app`**

- **现象**：`AttributeError: 'NoneType' object has no attribute 'add_api_route'`。
- **原因**：函数没有 `return`，Python 默认返回 `None`。
- **解决**：`app.add_middleware(...)` 之后单独 `return app`。
- **注意**：`add_middleware` 是「修改 app 本身」，无返回值，不能 `return app.add_middleware(...)`。
- ⚠️ 这是本项目「忘记 return」问题的**又双叒一次**（此前 PROGRESS 里已有多次「return 当 raise」记录）。

### 练习 3：CORS 对账

- 一次正确：`if origin in allowed_origins: return {"Access-Control-Allow-Origin": origin}`，否则 `{}`。

### 练习 4：带 cookie 的 CORS

- 一次正确：`allow_credentials=True` + `allow_origins` 用传入的明确列表（没写 `*`）+ 忘 return 的坑在练习 2 已踩过、这次记得 return。

### 练习 5：动态端口（2 个 bug）

**问题 A：参数名用错 —— `allow_origins` ≠ `allow_origin_regex`**

```python
allow_origins=r"http://localhost:\d+",   # ❌ 正则当字面量
```

- **现象**：该放行的 origin 全不放行，响应里没有 `access-control-allow-origin`。
- **原因**：`allow_origins` 是**精确字符串匹配**的列表，不认正则；放行任意端口要用 `allow_origin_regex`。

**问题 B：正则 `\\d` 多了个反斜杠**

```python
r"http://localhost:\\d+"   # ❌ raw 字符串里 \\ 是字面反斜杠，\d 变「反斜杠+d」
```

- **原因**：练习提示里写的 `\\d` 是因为那句提示本身在**普通（非 raw）docstring** 里，`\\` 渲染出来才是 `\`。用户从源码直接抄 `\\d`，但自己的代码是 raw 字符串，规则不同。
- **解决**：raw 字符串里 `\d` 就是数字，应写 `r"http://localhost:\d+"`。
- **附带清理**：`allow_credentials=True` 本题用不到（测试没查），去掉保持干净。

### Review

- 全部练习结构清晰、用了提前 return，无明显「能过但糙」写法，无需额外工程质量 Review。

---

## 四、踩坑速查表

| 错误写法 | 现象 | 正确写法 |
|---------|------|---------|
| `method in ["get", ...]` | `"GET"` 不命中 | `method.lower() not in (...)` |
| `headers in [安全头]` | 永远 False，全被拦 | 遍历每个 header `h.lower() not in safe_set` |
| `if content_type or content_type in [...]` | json 被短路放行、None 被误拦 | `content_type is not None and content_type not in (...)` |
| 函数末尾忘 `return app` | `AttributeError: NoneType` | `add_middleware` 后单独 `return app` |
| `allow_methods`/`allow_headers` 不写 | 预检直接 400 | 显式写 `["*"]` |
| `allow_credentials=True` 配 `allow_origins=["*"]` | 浏览器拒绝，CSRF 风险 | `allow_origins` 写具体列表 |
| 正则写进 `allow_origins` | 正则当字面量，不匹配 | 用 `allow_origin_regex` |
| raw 字符串里 `\\d` | 匹配「反斜杠+d」非数字 | `r"...\d+"`（单个 `\d`） |
| 空 `{}` 当空 set | 实际是 dict | `set()` |

---

## 五、本章结论

- CORS 是**浏览器**的同源策略在起作用：请求照发、响应照回，浏览器拦着 JS 不让读；后端配合回响应头即可；
- **简单请求**（表单能发的 GET/HEAD/POST + 三种 content-type）直接发；**非简单请求**（JSON、PUT/DELETE、自定义头）先 `OPTIONS` 预检；
- `CORSMiddleware` 三件套：`allow_origins`（精确）、`allow_origin_regex`（正则）、`allow_methods`/`allow_headers`（**必须显式写**）；
- 带 cookie 的跨域（`allow_credentials=True`）`allow_origins` 不能 `*`，否则等于把登录态拱手让给任何网站；
- 开发环境 Vite 端口乱跳，用 `allow_origin_regex` 一次性放行 `localhost:<任意端口>`。
