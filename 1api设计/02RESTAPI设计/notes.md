# 第一阶段 · 2 REST API 设计 — 学习笔记

> 完成日期：2026-08-24
> 状态：✅ 4 个练习全通

---

## 一、知识点讲解

### 1. REST 是什么

REST = **Re**presentational **S**tate **T**ransfer，本质是一套**约定**：用「资源 + HTTP 方法」描述对数据的操作。

**前端类比**：就像组件化的命名约定。React 里 `props` 叫 `todos`、回调叫 `onToggle`，不是语法要求，但大家遵守后新同事秒懂。REST 就是后端接口届的这套「命名习惯」。遵守它换来的是**接口可预测**：看到 `GET /todos/42`，不用查文档就知道「查 id=42 的 todo」。

### 2. 资源建模：URL 是名词，动作交给 HTTP 方法

| ❌ 反例（动词塞 URL） | ✅ 正确（名词 + 方法） |
|---|---|
| `GET /getUser?id=1` | `GET /users/1` |
| `POST /createOrder` | `POST /orders` |
| `POST /deleteTodo` | `DELETE /todos/1` |

**为什么坏**：一个资源有很多操作，但 URL 只有一个。`getUser`/`updateUser`/`deleteUser` 会让一个 User 冒出 5 个 URL。正确做法：`/users/:id` 一个 URL，配合 5 个 HTTP 方法覆盖所有操作。

**前端类比**：`/user/:id` 是一个页面，页面上有「查看/编辑/删除」三个按钮，动作由 `onClick` 决定，URL 只代表「这是用户详情页」。REST 的 URL 是「详情页」，HTTP 方法是那些 `onClick`。

命名约定：
- 复数名词：`/todos`（表示集合）
- 小写：`/users`
- 层级表达关系：`/users/1/orders`
- 用 ID 定位单个资源：`/todos/42`（id 唯一，title 不唯一）

### 3. HTTP 方法语义 + 幂等性

| 方法 | 职责 | 副作用 | 幂等 |
|------|------|--------|------|
| GET | 读 | 无 | ✅ |
| POST | 创建 | 有 | ❌ |
| PUT | 整体替换更新 | 有 | ✅ |
| PATCH | 局部更新 | 有 | ✅ |
| DELETE | 删除 | 有 | ✅ |

**幂等 = 同一个请求发多次，结果和发一次一样**。GET 幂等（刷新不变），POST 不幂等（发两次建两条），PUT/DELETE 幂等。

**前端类比**：`setState(5)` 幂等，`setState(prev => prev+1)` 不幂等。前端天然会重发请求（双击、断网重试），所以接口要清楚自己是哪种，才能约定「可不可以安全重试」。

### 4. 状态码：用数字传达结果

5 大类，看第一位：

| 类别 | 含义 | 例子 |
|------|------|------|
| 2xx | 成功 | 200 OK、201 Created、204 No Content |
| 3xx | 重定向 | 301、302 |
| 4xx | **客户端的错** | 400 参数错、401 未登录、403 无权限、404 不存在 |
| 5xx | **服务端的错** | 500、503 |

**前端类比**：axios 拦截器依赖状态码：
```js
if (status === 401) → 跳登录
if (status === 403) → 提示没权限
if (status >= 500) → 提示服务器开小差
```

**新手最容易犯的错**：所有情况都返回 200，在 body 里塞 `{"success": false}`。这样拦截器就废了。**状态码本身就是结果，body 只放数据**。

### 5. 分页 / 过滤 / 排序

列表必须分页（10 万条一次返回会卡死）。

```
GET /todos?page=1&size=10
```

返回结构带元信息，前端才能渲染分页条：
```json
{"items": [...], "page": 1, "size": 10, "total": 57}
```

**前端类比**：el-table / antd Table 的 `pagination` 要的那组数据。`items` 渲染当前页，`total`+`size` 算总页数，`page` 高亮当前页。

统一原则：**定位数据用「路径参数」（`/todos/42`），改变数据范围用「查询参数」（`?page=2`）**。

### 6. 统一响应格式和错误格式

FastAPI 抛 `HTTPException`，前端收到的一定是 `{"detail": "..."}` + 对应状态码。

**为什么要统一**：前端写一处错误处理就能覆盖所有接口：
```js
const msg = error.response?.data?.detail || "未知错误"
```

（成功响应包不包一层，是团队约定，FastAPI 默认裸数据就够。）

---

## 二、练习 ↔ 知识点映射

| 练习 | 知识点 | 关键 API/语法 |
|------|--------|--------------|
| 1 资源建模判断 | URL 名词化 | `in` 判断子串、for 循环 + 提前 return |
| 2 创建资源 | POST + 201、状态码 vs body | `max()` 生成器、Pydantic `.属性` |
| 3 分页 | 查询参数、元信息结构 | list 切片 `todos[start:start+size]` |
| 4 错误处理 | 404 + 统一错误格式 | `raise HTTPException(404, detail=...)` |

---

## 三、练习纠错全记录

### 练习 1：`in` 的方向 + `return` 的位置（改 2 次才过）

**第 1 版（错）**：
```python
arr = ['get', 'create', ...]
if url in arr:      # ❌ 判断「整个 url 是否等于某个动词」
    return False
else:
    return True
```
- **现象**：`/getUser` 返回 `True`（期望 `False`），因为 `/getUser` 不等于 `get`
- **原因**：混淆了 `in` 的两种语义 —— `item in list`（整体相等）vs `substr in str`（子串包含）
- **知识点**：Python 的 `in` 一个运算符干两件事，方向靠「谁 in 谁」决定
- **解决**：改成 `x in url`（动词是不是 url 的子串）

**第 2 版（错）**：
```python
for x in arr:
    if x in url:
        return False
    else:
        return True     # ❌ 循环第一次迭代就退出
```
- **现象**：`/deleteUser` 返回 `True`（期望 `False`），因为只检查了第一个动词 `'get'` 就退出了
- **原因**：`return` 会立刻结束整个函数（包括循环）
- **知识点**：`return` 是「提前下班」，一旦执行循环立刻终止
- **解决**：`return True` 移到循环外，与 `for` 平级

**最终版（对）**：
```python
arr = ['get', 'create', 'update', 'delete', 'remove', 'edit']
for x in arr:
    if x in url:
        return False
return True
```

### 练习 2：对象取值 + 状态码塞 body（改 1 次才过）

**第 1 版（错）**：
```python
new_todo: Todo = {'id': new_id, 'title': todo}   # ❌ 把整个对象当 title
return { 'code': 201, 'data': new_todo }          # ❌ 包一层 + 状态码塞 body
```
- **现象**：`r.json().get("title")` 拿到嵌套对象而非字符串；测试 `.get("title")` 得 None
- **原因 1**：`todo` 是 Pydantic 模型对象，不是字符串，取值要用 `todo.title`
- **原因 2**：混淆了「状态码（响应头）」和「响应体（return）」
- **知识点**：Pydantic 对象用 `.属性` 取字段；状态码由 `status_code=201` 装饰器管，`return` 只管 body
- **解决**：
```python
new_id = max(t['id'] for t in todos) + 1
new_todo = {'id': new_id, 'title': todo.title}
todos.append(new_todo)
return new_todo
```

### 练习 3：一次通过 ✅

`start = (page-1)*size` + 切片 + 四件套，直接对。

### 练习 4：dict vs 对象 + return vs raise（改 1 次才过）

**第 1 版（错）**：
```python
for t in todos:
    if t.id == todo_id:      # ❌ dict 用了点访问
        return t
return { 'code': 404 }        # ❌ 状态码塞 body，实际还是 200
```
- **现象**：`t.id` 触发 `AttributeError`；`r.status_code` 是 200 不是 404
- **原因 1**：`todos` 里的元素是 dict，取值用 `t['id']`（方括号），不是 `t.id`
- **原因 2**：`return {'code': 404}` 只是正常返回 body，没抛错，状态码还是 200
- **知识点**：dict 用 `[]`，Pydantic 对象用 `.`（对照练习 2）；`return` 正常返回，`raise` 抛错
- **解决**：
```python
for t in todos:
    if t['id'] == todo_id:
        return t
raise HTTPException(status_code=404, detail="Todo not found")
```

---

## 四、踩坑速查表

| 错误写法 | 报错/现象 | 正确写法 | 知识点 |
|----------|----------|---------|--------|
| `if url in arr` | `/getUser` 返回 True | `if x in url` | `in` 方向：`item in list` vs `substr in str` |
| 循环里 `else: return True` | 只查第一个词 | `return True` 移循环外 | `return` 立刻结束函数 |
| `'title': todo` | title 变嵌套对象 | `'title': todo.title` | Pydantic 对象用 `.属性` |
| `return {'code': 201, 'data': ...}` | `.get("title")` 得 None | `return new_todo` | 状态码（响应头）≠ 响应体（return） |
| `t.id`（t 是 dict） | `AttributeError` | `t['id']` | dict 用 `[]`，对象用 `.` |
| `return {'code': 404}` | `status_code` 还是 200 | `raise HTTPException(404, detail=...)` | `return` 正常返回，`raise` 抛错 |

**核心心法**：
- **URL 定「是什么」，HTTP 方法定「做什么」，状态码定「结果如何」，响应结构定「前端怎么接」**
- `return` = JS 的 `return`/`resolve`；`raise` = JS 的 `throw`/`reject`
- dict 和 Pydantic 对象是两回事，取值一个用 `[]` 一个用 `.`
