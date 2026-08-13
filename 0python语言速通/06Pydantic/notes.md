# 0.6 Pydantic — 学习笔记

> 两部分：**① 知识点讲解** + **② 练习期间遇到的问题**（每个问题关联对应知识点）。
> 环境：Pydantic **2.13.2**（v2 语法）。

---

## 一、核心知识点讲解

### 前端类比

Pydantic ≈ **TypeScript 的 interface + Zod 的合体**：

| 前端 | Pydantic |
|------|----------|
| `interface User { name: string }` | `class User(BaseModel): name: str` |
| Zod 运行时校验 `z.string()` | Pydantic 运行时校验（自动） |
| 手动 `Number("25")` 转类型 | 自动 coercion（宽松模式） |
| `JSON.stringify(obj)` | `model_dump_json()` |
| `JSON.parse(str)` | `model_validate(dict)` |

**关键区别**：TypeScript 的 interface 编译后就不存在了（运行时啥也拦不住），Pydantic 是**运行时真正校验**——传错类型直接抛 `ValidationError`，这点很像 Zod。

### 定义模型

```python
from pydantic import BaseModel, Field, ValidationError

class User(BaseModel):
    name: str
    age: int

user = User(name="Alice", age=30)   # ✅
User(name="Alice", age="abc")       # ❌ 抛 ValidationError
```

继承 `BaseModel` + 类型注解 = 数据模型，自动获得校验、转换、序列化能力。

### 自动类型转换（coercion）

```python
user = User(name="Alice", age="25")  # 传了字符串 "25"
print(user.age, type(user.age))      # 25 <class 'int'> —— 自动转成 int
```

这是 Pydantic 和 TS 最大的不同：默认**宽松模式**，尽量帮你把值转成目标类型（`"25"` → `25`）。想要严格模式需显式 `Field(strict=True)`。

### 默认值 & Field 约束

```python
class Article(BaseModel):
    title: str
    views: int = 0                 # 默认值

class Product(BaseModel):
    name: str
    price: float = Field(gt=0)     # 约束：必须 > 0
```

`Field` 常用约束：`gt`（>）、`ge`（≥）、`lt`（<）、`le`（≤）、`min_length`、`max_length`、`pattern`（正则）。

### 序列化 & 嵌套模型

```python
user.model_dump()            # -> {"name": "Dave", "age": 28}（dict）
user.model_dump_json()       # -> '{"name":"Dave","age":28}'（JSON 字符串）
User.model_validate(d)       # <- 从 dict 构建模型

class Order(BaseModel):
    id: int
    user: User                # 嵌套模型

# user 传 dict 会自动转成 User 实例
order = Order(id=1, user={"name": "Eve", "age": 22})
print(order.user.name)        # "Eve"
```

### 捕获校验错误 + 读懂 ValidationError 报错

```python
try:
    User(name="x", age="abc")
except ValidationError as e:
    print(e)
```

`ValidationError` 是一个普通异常类，用 `try/except` 接住即可。

**怎么读懂报错信息**（练习里真实出现的一条）：

```
ValidationError: 1 validation error for Product
price
  Input should be greater than 0 [type=greater_than, input_value=-5, input_type=int]
  For further information visit https://errors.pydantic.dev/2.13/v/greater_than
```

逐行拆解：

| 片段 | 含义 |
|------|------|
| `1 validation error for Product` | 模型名 + 错误数量 |
| `price` | 出错的是哪个字段 |
| `Input should be greater than 0` | 人类可读的原因 |
| `[type=greater_than, input_value=-5, input_type=int]` | 错误类型、输入值、输入类型 |
| `errors.pydantic.dev/.../greater_than` | 点击可看该错误类型的官方文档 |

调试技巧：报错里 **`type=` 和 `input_value=` 是最有用的**——一眼看出"哪条规则没满足"和"传进去的值是什么"。

### 常用 API 速查（v2 语法）

```python
from pydantic import BaseModel, Field, ValidationError

class M(BaseModel): ...
m = M(**data)
m.model_dump()          # 转 dict
m.model_dump_json()     # 转 JSON 字符串
M.model_validate(d)     # dict -> 模型
m.model_fields          # 查看字段元信息
```

> ⚠️ 版本注意：Pydantic v2 用 `model_dump()` / `model_validate()`；老教程里的 `.dict()` / `.parse_obj()` 是 v1 写法，已废弃。

---

## 二、练习 ↔ 知识点映射

| 练习 | 内容 | 对应知识点 |
|------|------|-----------|
| 1 | 定义 `User` 模型 | `BaseModel` + 类型注解 |
| 2 | `validate_age` 校验 | `try/except ValidationError` |
| 3 | `coerced_age_type` | coercion 自动类型转换 |
| 4 | `default_views` | 字段默认值 |
| 5 | `negative_price_raises` | `Field(gt=0)` 约束 + 捕获异常 |
| 6 | `dump_user` | `model_dump()` 序列化 |
| 7 | `order_user_name` | 嵌套模型（dict 自动转子模型） |

---

## 三、练习期间遇到的问题（本次会话交流）

### 问题 1：练习 2 函数体空着

- **现象**：`validate_age` 只留了 `# TODO` 注释和空行，函数体没写，返回 `None`
- **知识点**：`try/except` 捕获 `ValidationError` 是 Pydantic 校验的标配用法
- **解决**：用 try 尝试创建模型，`except ValidationError` 分支处理非法输入

### 问题 2：练习 5 异常没捕获，程序崩溃

- **现象**：运行到练习 5 直接崩了，报错 `ValidationError: price — Input should be greater than 0`
- **关键认知**：这条报错其实说明 `Field(gt=0)` **写对了**——约束成功拦下了 `price=-5`。问题不在模型，在于函数里 `Product(name='x', price=-5)` 抛出的异常**没人接住**，直接冒泡到测试代码把程序炸停
- **知识点**：`try/except ValidationError` 捕获校验异常，别让它冒泡
- **解决**：用 try 包住 `Product(...)`，`except ValidationError` 里返回结果

### 问题 3：练习 5 的 True/False 语义反了

- **现象**：只剩练习 5 失败 `期望 True，实际 False`
- **用户写法**：

```python
try:
    Product(name='x', price=-5)
    return True          # ← 永远执行不到（上一行已抛错）
except ValidationError:
    return False         # ← 实际走这里
```

- **知识点**：**语义反转**——练习 2 和练习 5 问的问题相反：

| | 函数问的问题 | 抛错意味着 |
|---|-------------|-----------|
| 练习 2 `validate_age` | 这个值**合法吗**？ | 非法 → `False` |
| 练习 5 `negative_price_raises` | 负价格**会被拦截吗**？ | 被拦截 → `True` |

练习 5 里「抛错」不是 bug，而是"Pydantic 按预期拦下了非法数据"——恰恰是它该有的行为，所以是**好消息**，返回 `True`。

- **解决**：`try` 块（没抛错，约束失效）返回 `False`，`except` 块（抛错，约束生效）返回 `True`

### 结果：全部通过 🎉

7 个练习全过，练习 2/5 的 try/except 捕获 + 语义理解到位。

---

## 四、踩坑速查

| 错误 | 后果 | 正确做法 |
|------|------|---------|
| 校验错误不捕获 | `ValidationError` 冒泡，程序崩溃 | 用 `try/except ValidationError` 接住 |
| 把"抛错"当坏事 | 测试语义写反 | 先想清楚：函数是在**验证约束生效**，抛错=符合预期 |
| 用 v1 的 `.dict()` / `.parse_obj()` | v2 报 `AttributeError` | 用 `.model_dump()` / `.model_validate()` |
| 以为 Pydantic 是编译期检查 | 误以为运行时不用管 | Pydantic 是**运行时**校验，传错类型当场抛错 |
| 读不懂 ValidationError 报错 | 排查慢 | 重点看 `type=`（哪条规则）和 `input_value=`（传了什么） |
