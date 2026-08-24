# 1 FastAPI 入门 — 学习笔记

> 两部分：**① 知识点讲解** + **② 练习期间遇到的问题**。
> 环境：Python 3.12.9 / FastAPI 0.141.1 / uvicorn 0.52.4 / httpx 0.28.1（venv 在项目根 `.venv/`）。

---

## 一、核心知识点讲解

### FastAPI 是什么 —— 后端版的「前端框架」

前端框架管「用户交互 → 更新 DOM」，FastAPI 管「HTTP 请求 → 返回响应」。它是一个**请求分发器**：URL 进来 → 路由匹配 → 调用函数 → 返回 JSON。

| 前端 | FastAPI（后端） |
|------|----------------|
| `createApp()` / `new Vue()` | `app = FastAPI()` |
| 路由表 `{path, component}` | `@app.get("/users")` 装饰器 |
| `<Route path="/users/:id">` | `@app.get("/users/{user_id}")` |
| `location.search` / `URLSearchParams` | 查询参数 `?q=xxx` |
| `fetch(url, {body: JSON.stringify(x)})` | POST 请求体 + Pydantic 模型 |

**核心差别**：前端框架管「UI 怎么变」，FastAPI 管「一个 URL 请求进来，该调用哪个函数、返回什么 JSON」。

### 最小应用结构

```python
from fastapi import FastAPI

app = FastAPI()                    # 1. 创建应用 ≈ createApp()

@app.get("/")                      # 2. 声明路由：GET / 交给下面这个函数
def read_root():                   # 3. 处理函数：请求进来就调用它
    return {"message": "Hello World"}  # 4. 返回 dict，FastAPI 自动转成 JSON
```

「路由 → 函数」，函数 return 的 dict 自动序列化成 JSON。

### ⭐ 核心概念：请求的数据从哪里来？

一个 HTTP 请求，数据能藏在**三个地方**：

```
POST /users/42?source=web         ← URL：路径 + 查询参数
Content-Type: application/json
                                  ← 空行
{"name": "Alice", "age": 30}      ← body（请求体）
```

#### 1. 路径参数（path parameter）—— 数据在 URL 路径里

```python
@app.get("/users/{user_id}")      # {user_id} 是占位符
def get_user(user_id: int):       # 同名参数接住它
    return {"user_id": user_id}
```

请求 `GET /users/42` → `user_id` 就是 `42`。**等于 React Router 的 `/users/:user_id`**。
写了 `user_id: int`，FastAPI 会自动把字符串 `"42"` 转成 int（Pydantic coercion 同款）。

#### 2. 查询参数（query parameter）—— 数据在 `?` 后面

```python
@app.get("/search")
def search(q: str = None):        # 不在路径里、有默认值 → 查询参数
    return {"q": q}
```

请求 `GET /search?q=fastapi` → `q` 是 `"fastapi"`。**等于 `URLSearchParams(location.search).get("q")`**。

#### 3. 请求体（request body）—— 数据在 POST 的 body 里

```python
from pydantic import BaseModel

class Item(BaseModel):            # 用 Pydantic 定义 body 的形状
    name: str
    price: float

@app.post("/items")
def create_item(item: Item):      # 参数是 Pydantic 模型 → 请求体
    return {"name": item.name, "price": item.price}
```

**等于前端**：
```javascript
fetch("/items", { method: "POST", body: JSON.stringify({ name: "apple", price: 3.5 }) })
```

### 怎么判断参数属于哪种？—— 约定优于配置

FastAPI 的「魔法」，不用手动声明参数来源：

| 参数特征 | FastAPI 判定为 |
|----------|---------------|
| 名字出现在路径的 `{...}` 里 | **路径参数** |
| 是 Pydantic 模型类型 | **请求体** |
| 其余（有默认值、基础类型） | **查询参数** |

按这几种方式写函数签名，FastAPI 自己搞定剩下的。

### 怎么测试 —— TestClient

前端在控制台 `fetch("/")` 看结果，后端用 `TestClient` 做同样的事（不用真的起服务器）：

```python
from fastapi.testclient import TestClient
client = TestClient(app)

r = client.get("/users/42")       # 模拟 GET 请求
r.status_code                      # 200
r.json()                           # {"user_id": 42}
```

---

## 二、练习 ↔ 知识点映射

| 练习 | 内容 | 对应知识点 |
|------|------|-----------|
| 1 | 根路由返回 `{"message": "Hello World"}` | 路由 + 返回 dict（自动转 JSON） |
| 2 | `/users/{user_id}` 返回 user_id | 路径参数 + 自动类型转换（str → int） |
| 3 | `/search?q=xxx` 返回 q | 查询参数 + 默认值 `None` |
| 4 | POST `/items` 接收 Item 模型 | 请求体 + Pydantic 模型 |

---

## 三、练习期间遇到的问题（本次会话交流）

### 问题 1：练习 4 把字段写成了「嵌套类定义」

- **现象**：前 3 个练习全过，练习 4 报错：
  ```
  AttributeError: 'Item' object has no attribute 'name'
  ```
- **用户原写法**：

```python
class Item(BaseModel):
    """
    Item 模型，定义两个字段...
    """
    # TODO: 写两个字段
    class Item(BaseModel):      # ← 又在类体里定义了一遍 class Item
        name: str
        price: float
```

- **原因**：Pydantic 模型的**字段是直接写在类体里的、带类型注解的变量**（`name: str`），不是在类里再嵌套一个 class。嵌套的 `class Item` 只是一个类属性，`name`/`price` 根本没成为外层 `Item` 的字段，所以 `item.name` 取不到 → `AttributeError`。

- **对应知识点**：Pydantic `BaseModel` 的字段定义语法。前端类比：模型 ≈ TS 的 `interface`，字段直接写在里面，不会在 `interface Item` 里再包一层 `interface Item`。

- **引导过程**：没有直接给答案，而是让用户对比 0.6 里 `User` 模型的定义（`name: str` 直接写在类体里），自己找出「多出来的那一层」。

- **解决**：删掉嵌套的 `class Item(BaseModel):`，字段直接写在类体：

```python
class Item(BaseModel):
    name: str
    price: float
```

### 结果：全部通过 🎉

4 个练习全过，路径参数 / 查询参数 / 请求体 / 路由 全部掌握，练习 4 的「字段 vs 嵌套类」纠错到位。

---

## 四、踩坑速查

| 错误 | 后果 | 正确做法 |
|------|------|---------|
| 在 `class X(BaseModel)` 里再写 `class X(BaseModel)` | `AttributeError: 'X' object has no attribute '...'`（字段没被定义） | 字段直接写在类体里：`name: str` |
| 路径参数 `{user_id}` 没写类型注解 `int` | 拿到的是字符串 `"42"` 而不是 int | 写 `user_id: int`，FastAPI 自动转换 |
| 查询参数忘了给默认值 | 参数变成「必填」，不带 `?q=` 会 422 | 需要可选时写 `q: str = None` |

---

## 五、环境备注

- 运行 `TestClient` 时会看到一条 `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead`——**不影响练习**，是 Starlette 提示未来会改用 `httpx2` 包，现在可以忽略。
- 练习运行命令（在 `1api设计/01FastAPI入门/` 目录下）：
  ```bash
  .venv/bin/python practice.py          # 或 ../../.venv/bin/python practice.py
  ```
