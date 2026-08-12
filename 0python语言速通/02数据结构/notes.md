# 0.2 数据结构 — 笔记

## 四大核心数据结构

| Python | JS 对照 | 可变 | 有序 | 可重复 |
|--------|---------|------|------|--------|
| `list` | `Array` | ✅ | ✅ | ✅ |
| `tuple` | 无（类似 `Object.freeze([])`） | ❌ | ✅ | ✅ |
| `dict` | `Object` / `Map` | ✅ | ✅(3.7+) | key 不可重复 |
| `set` | `Set` | ✅ | ❌ | ❌（自动去重） |

## list — 列表

```python
# 列表推导式（Python 杀手锏）
[x**2 for x in nums if x > 6 and x % 2 == 0]

# 切片 [start:end:step] — 左闭右开
items[1:-1]   # 去掉头尾
items[::-1]   # 反转
items[::2]    # 隔一个取一个
```

## tuple — 元组

- **不可变**，创建后不能修改
- 函数返回多个值其实返回的是 tuple：`return x, y` → `(x, y)`
- 单元素 tuple 必须加逗号：`(1,)`
- 可以做 dict 的 key（list 不行）

## dict — 字典

```python
# 安全访问
d.get("key")          # 不存在返回 None，不报错
d.get("key", "默认值") # 不存在返回默认值

# 字典推导式
{x: x**3 for x in range(1, n+1)}

# 统计频率模式
for char in text:
    count[char] = count.get(char, 0) + 1
```

## set — 集合

```python
# 集合运算
a & b   # 交集
a | b   # 并集
a - b   # 差集
a ^ b   # 对称差集

# 去重
set([1, 2, 2, 3])  # {1, 2, 3}
```

## 内置函数：min / max / sum

```python
min([5, 2, 9, 1, 7])     # 1
max([5, 2, 9, 1, 7])     # 9
sum([1, 2, 3, 4, 5])     # 15
sum([1, 2, 3], 10)       # 16（第二个参数是初始值，默认 0）
```

**JS 对比**：`Math.min(...arr)` / `arr.reduce((a,b)=>a+b, 0)` — Python 直接传列表，不需要展开。

**本质**：就是封装好的 for 循环。

## 列表推导式深度解析

**公式**：`[对x做什么  for x in 可迭代对象  if 条件]`

**本质就是 for 循环的压缩写法**：

```python
# ❌ 传统写法（4行）
result = []
for n in nums:
    if n > 6 and n % 2 == 0:
        result.append(n ** 2)

# ✅ 列表推导式（1行）
result = [n**2 for n in nums if n > 6 and n % 2 == 0]
```

**JS 对比**：
```javascript
// JS 两步：filter → map
nums.filter(n => n > 6 && n % 2 === 0).map(n => n ** 2)
// Python 一步搞定
[n**2 for n in nums if n > 6 and n % 2 == 0]
```

## 生成器表达式 — 列表推导式的"省内存版"

**区别**：`[]` vs `()` — 一个生成全量列表，一个"用到才给"。

```python
# 列表推导式：100万个元素全在内存里
[x**2 for x in range(1000000)]

# 生成器表达式：只是个"配方"，还没计算
(x**2 for x in range(1000000))
```

**什么时候用生成器？**

| 场景 | 用哪个 | 原因 |
|------|--------|------|
| `sum(x**2 for x in data)` | 生成器 | sum 逐个取，不用先生成列表 |
| `max(item.price for item in cart)` | 生成器 | 同理，逐一遍历 |
| `"\n".join(line.upper() for line in file)` | 生成器 | 大文件不会爆内存 |
| `squares[3]` 需要索引访问 | 列表 | 生成器不支持下标 |
| `len(squares)` 需要长度 | 列表 | 生成器没有长度 |
| 需要遍历多次 | 列表 | 生成器用完就没了 |

**决策口诀**：
```
需要索引/长度/遍历多次  → [x for ...] 列表推导式
只管挨个取一遍           → (x for ...) 生成器表达式
```

> `sum( ... )` 里可以省略生成器的括号：`sum((x**2 for x in data))` = `sum(x**2 for x in data)`

## 字典推导式

**公式**：`{key表达式: value表达式  for 变量 in 可迭代对象  if 条件}`

```python
# 基础
{x: x**3 for x in range(1, 4)}        # {1:1, 2:8, 3:27}

# 翻转 key/value
{v: k for k, v in {"a":1, "b":2}.items()}  # {1:"a", 2:"b"}

# 带筛选
{k: v for k, v in d.items() if v > 1}      # 只保留 value > 1 的
```

**本质就是 for 循环填字典的压缩版：**
```python
# 推导式
{x: x**3 for x in range(1, 4)}

# 等价于
result = {}
for x in range(1, 4):
    result[x] = x**3
```

## 三种推导式对比

| | 列表 | 字典 | 生成器 |
|--|------|------|--------|
| 符号 | `[ ]` | `{ }` | `( )` |
| 结构 | `[表达式 for x in ...]` | `{k: v for x in ...}` | `(表达式 for x in ...)` |
| 结果 | `[1, 4, 9]` | `{1:1, 2:8}` | 一个"配方" |
| 占内存 | 全量 | 全量 | 逐个 |
| 可索引 | ✅ | ✅ (by key) | ❌ |

## 踩坑记录

| 坑 | 原因 | 修复 |
|----|------|------|
| `range(n)` 从 0 开始 | Python range 默认 start=0 | 用 `range(1, n+1)` |
| `range(1, n)` 不含 n | range 左闭右开 `[start, stop)` | 用 `range(1, n+1)` |

## 前端类比速查

- `arr.push(x)` → `list.append(x)`
- `arr.slice(1, -1)` → `list[1:-1]`
- `arr.map().filter()` → `[f(x) for x in list if cond]`（列表推导式）
- `obj?.key ?? default` → `dict.get("key", default)`
- `new Set(arr)` → `set(list)`
- `Object.freeze(arr)` → `tuple(arr)`
