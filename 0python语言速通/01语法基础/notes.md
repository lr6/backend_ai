# 0.1 Python 语法基础 — 学习笔记

> 日期：2026-08-11
> 前端对照视角：JavaScript → Python

---

## 变量

```python
name = "zhio"       # 不需要 let/const/var
age = 25
is_done = True      # 大写 True / False
MAX_SIZE = 100      # 约定：全大写 = 常量
```

## 函数

```python
def greet(name):
    return "Hello " + name

def add(a, b):
    return a + b
```

## 字符串（f-string）

```python
f"Hello {name}"     # JS: `Hello ${name}`
name.upper()        # JS: name.toUpperCase()
"hi" in name        # JS: name.includes("hi")
```

## 条件

```python
if age >= 18:
    print("adult")
elif age >= 13:     # 注意是 elif，不是 else if
    print("teen")
else:
    print("child")
```

⚠️ **最重要的区别**：没有 `{}`，靠缩进（4 空格）

## 循环

```python
for i in range(5):          # 0,1,2,3,4
for item in items:          # JS: for...of
for i, item in enumerate(): # 同时拿索引和值
```

## 列表

```python
arr = [1, 2, 3]
arr.append(4)     # push
arr.pop()         # pop
arr[1:3]          # slice(1,3) — 切片语法
```

---

## 踩坑记录

| 坑 | JS 习惯 | Python 正确写法 |
|----|---------|----------------|
| f-string 忘加 f | `` `Hello ${name}` `` | `f"Hello {name}"` |
| for 遍历了 range 而不是参数 | `for (let i=0; i<n; i++)` | `for i in numbers` |
