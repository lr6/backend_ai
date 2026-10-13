# 9 Normalization — 范式化与反范式化

> 学习日期：2026-09-07 开始，2026-10-13 完成
> 练习文件：`practice.py`（5 个练习全通）

---

## 一、知识点讲解

### 1. 范式化是什么

**范式化 = 拆表消除冗余，让每份数据只有一个「家」。** 代价是读的时候要 JOIN 回来。

前端类比：就像把重复的 JSX 抽成一个 `<ProductName />` 组件、把重复数据在 store 里只放一份 —— 范式化干的是「提取公共部分、单一数据源」这件事，只不过对象是数据库的**列**。

**反范式化 = 故意存回冗余**，用「写的一致性」换「读的快」，本质就是缓存。

### 2. 三层范式（口诀先记）

> **每个非主键列，都要「直接、完整」地依赖主键**
> （直接 = 3NF，完整 = 2NF）

| 范式 | 要求 | 违规的名字 |
|---|---|---|
| **1NF** | 一格只装**一个值**（原子） | — |
| **2NF** | 非主键列必须**完整**依赖主键 | 部分依赖 |
| **3NF** | 非主键列必须**直接**依赖主键 | 传递依赖 |

### 3. 1NF — 原子性

一格塞了多个值就违规。判断方法：

- 值是 `list` / `tuple` → 违规
- 值是字符串但含逗号 `","`（多个值拼在一个字符串里）→ 违规

```python
rows = [{"order_id": 1, "product": "键盘,鼠标"},   # ← "键盘,鼠标" 一格两值，违规
        {"order_id": 2, "product": "耳机"}]
# 违规列 -> ["product"]
```

### 4. 2NF — 部分依赖

**定义**：非主键列只依赖**复合主键的一部分**。

```
order_items(order_id, product_id, product_name, qty)
主键 = (order_id, product_id)
```

- `product_name` 依赖的列 = `{product_id}`
- 主键 = `{order_id, product_id}`
- `{product_id}` 是主键的**真子集** → 主键「没被完整地用上」→ **部分依赖，违反 2NF**

**⚠️ 关键前提：部分依赖只有在「复合主键」下才可能存在。** 主键只有一列时，谈不上「一部分」，2NF 天然满足。

**判断代码**：`set(dep) < set(pk)` —— 真子集判断

**代价**：`product_name` 在每个订单行重复存 N 遍，商品改名要改 N 行，漏一行就出现「一个商品两个名字」。

**解法**：

```
products(product_id, product_name)         ← 商品名只留一份
order_items(order_id, product_id, qty)     ← 只留真正依赖整个主键的东西
```

### 5. 3NF — 传递依赖

**定义**：非主键列**隔着一个非主键列**拐弯依赖主键。

```
users(user_id, city_id, city_name)
主键 = user_id       ← 单列主键
```

依赖链：

```
user_id ──→ city_id ──→ city_name
（主键）    （非主键列）   （隔了一层）
```

- `city_id` 依赖主键 → 直接，✅
- `city_name` 依赖 `city_id`（非主键）→ 拐弯了 → **传递依赖，违反 3NF**

**为什么它不可能是部分依赖？**（本次探底题 2，用户答不上来，直接讲解）
因为部分依赖的前提是**主键复合**，这里主键只有 `user_id` 一列，没有「部分」可言 → 只剩传递依赖这一种可能。

**判断代码**：`deps[col]` 里只要有一列 `not in pk` → 传递依赖

**解法**：

```
cities(city_id, city_name)         ← 城市名单独一份
users(user_id, city_id, ...)       ← 只存外键，要用时 JOIN 出来
```

**3NF 的态度**：别存派生的东西，要用时算 / JOIN 出来。

### 6. 两种依赖对照表（核心速查）

| | 部分依赖 → 违反 2NF | 传递依赖 → 违反 3NF |
|---|---|---|
| 违规长什么样 | 只依赖主键的**一部分** | 隔着**非主键列**拐弯依赖主键 |
| 前提条件 | 主键必须是**复合**的 | 主键几列都行 |
| 依赖链 | `(A,B) → C`，但只有 `A → C` | `A → B → C`，且 B **不是**主键 |
| 代码判断 | `set(deps[c]) < set(pk)`（真子集） | `deps[c]` 里有列 `∉ pk` |

### 7. 复合主键为什么存在

**主键的作用是「唯一标识一行」**，取的是「能唯一标识一行的**最小列组合**」。一列做不到，就多列拼起来。

| order_id | product_id | product_name | qty |
|---|---|---|---|
| 1 | 101 | 键盘 | 2 |
| 1 | 102 | 鼠标 | 1 |
| 2 | 101 | 键盘 | 5 |

- `order_id = 1` 出现两次 → 单独不唯一
- `product_id = 101` 出现两次 → 单独不唯一
- `(1, 101)` 只出现一次 → 组合才唯一

前端类比：React 列表的 `key`。同商品出现在多张订单里，光用 `product_id` 当 key 会撞，得用 `` `${order_id}-${product_id}` ``。

**如果主键只写 order_id 会怎样？**
1. 数据库直接拒绝第二行（duplicate key 报错）—— 因为主键的定义本身就含「唯一」
2. 就算插进去，也没法单独指认「订单 1 里的键盘」—— `WHERE order_id = 1` 会改到两行

### 8. 反范式化决策

读多写少 + 一致性要求不高 → 反范式化缓存热点。

```
read_per_sec > 100  AND  write_per_day < 10  AND  consistency == "low"
  → "denormalize"，否则 "normalize"
```

### 9. 语言点（Python / JS 差异）

| 点 | Python | JavaScript |
|---|---|---|
| 遍历 dict 的键值 | `for k, v in d.items():` | `Object.entries(obj)` |
| 遍历 list | `for x in lst:` | `for (const x of arr)` |
| **空列表的真假** | `[]` 是 **falsy**（假） | `[]` 是 **truthy**（真）！ |
| **空对象的真假** | `{}` 是 **falsy** | `{}` 是 **truthy**！ |

> ⚠️ 空集合真假是前端转 Python 最容易踩的跨语言坑：Python 里 `if my_list:` 就等于「非空」。

**dict 只能用 `d["key"]`，不能用 `d.key`**（JS 两者皆可，Python 点号访问会 `AttributeError`）。

**变量命名原则**：名字要说清「里面**装的是什么**」，不是「它是个什么东西」。
反例：把装着违规列名的 set 命名成 `key`。

**循环里不要重复算不变量**：整个循环都不变的东西提到循环外算一次。
同类问题（更严重）：数据库查询写在循环里。

**`list(set)` 顺序不确定** —— set 无序。测试只比单元素/空列表时看不出来，但比较 `["a","b"]` vs `["b","a"]` 会莫名失败。要顺序稳定用 `list` 或 `sorted()`。

---

## 二、练习 ↔ 知识点映射

| 练习 | 函数 | 对应知识点 |
|---|---|---|
| 1 | `find_1nf_violations` | 1NF 原子性；list/dict 嵌套遍历 |
| 2 | `find_partial_dependency` | 2NF 部分依赖；真子集 `set(dep) < set(pk)` |
| 3 | `find_transitive_dependency` | 3NF 传递依赖；双层循环 |
| 4 | `highest_normal_form` | 综合判断；**函数复用**；Python 空列表 falsy |
| 5 | `denormalize_advice` | 反范式化决策；dict 取值；`and` 串联条件 |

---

## 三、练习纠错全记录

> 本次会话错误密度很高，按时间顺序完整记录。

### ① 探底题 1：「为什么主键有两个？」

**现象**：抛给你表 `order_items(order_id, product_id, product_name, qty)`，你没答范式问题，先反问「为啥主键两个？」

**说明**：**不知道复合主键存在的理由** —— 没建立起「主键 = 唯一标识一行的最小列组合」这个心智模型。

**讲解**：用三行真实数据展示 order_id 重复、product_id 重复、组合才唯一。前端类比 React 列表 key（`` `${order_id}-${product_id}` ``）。

**检查题**：「如果主键只写 order_id 一列会怎样？」
**你的回答**：「相同主键，不同数据」→ 方向对，已理解。

### ② 探底题 1（继续）：`product_name` 违反哪一条？

**你的回答**：「product_name 只依赖 product_id，这就不对了啊」→ 感觉到不对，但**说不出范式的名字和原因**。

**讲解**：命名它 = 部分依赖，违反 2NF。用集合对照表展示 `{product_id} ⊂ {order_id, product_id}`，点出这是主键「没被完整地用上」。

### ③ 探底题 2：单列主键下 `city_name` 是什么依赖？

**你的回答**：「传递依赖」✅ + 「为什么不可能部分依赖」= **我不知道** ❌

**讲解**：部分依赖的前提是**主键复合**，单列主键没有「部分」可言。
→ 已在笔记「3NF」一节记为**必背点**。

### ④ 练习 3 初版：拿错了层 + 返回类型错

**你写的**：

```python
for d in deps:
    if d not in pk:
        return d
```

**报错**：
```
练习3-例1 ❌ 期望 ['user_city'] 实际 user_city     ← 值对，格式错
练习3-例2 ❌ 期望 []           实际 created_at     ← 值本身就错
```

**根因（两个）**：
1. **拿错了层**：`for d in deps` 里 `d` 是 **dict 的 key（被决定的列名）**，不是**决定列**。决定列在 `deps[col]` 这个 value 里。要比的是 value 里的元素。
2. **返回类型错**：题目要 `list`，你 `return d` 返回的是**单个字符串**。

**引导过程**：让你新建 `tmp.py` 跑
```python
for d in deps: print(d)      # 打印出 user_city / created_at  → 确认 d 是 key
```
**你的回答**：「user_city, created_at」→ 确认了 d 是列名。

**修复**：需要**两层循环** + 先攒后返回：
```python
for col, dep in deps.items():
    for d in dep:
        if d not in pk:
            ...
```
（`deps.items()` ≈ JS 的 `Object.entries()`）

### ⑤ 修复练习 3 时误伤练习 1：多套了一层 `[]`

**现象**：报错从 8 个涨到 **11 个**，练习 1 开始报错。

**你写的**：`return [list(key)]`
**报错**：`练习1-例1 ❌ 期望 ['product'] 实际 [['product']]`

**根因**：`list(key)` **本身已经是 list**，外面再套 `[]` → 嵌套列表。这是把「练习 3 要返回 list」的错误修到了练习 1 头上（**串台**）。

**修复**：`return list(key)`

### ⑥ 修复练习 3：list 用了 set 的方法

**你写的**：

```python
key = []          # 第 98 行：list
...
key.add(col)      # 第 102 行：.add 是 set 的方法
```

**报错**：
```
AttributeError: 'list' object has no attribute 'add'
```

**根因**：类型和操作对不上。

**关键技巧（已教）**：**报错信息冒号后面那句就是诊断结论** —— `'list' object has no attribute 'add'` 直接告诉你「你是 list，但你用了 add」。

**二选一**：

| 攒进什么 | 初始化 | 添加 | 返回 |
|---|---|---|---|
| set | `key = set()` | `key.add(col)` | `list(key)` |
| list | `key = []` | `key.append(col)` | `key` |

你选了 **list + append**。

### ⑦ 练习 4：一遍过 ✅

复用练习 2、3 的函数，无报错。

**讲解点**：Python 里空列表 `[]` 是 **falsy**，所以 `if find_partial_dependency(...):` 就等于「有内容」—— 不用写 `len(x) > 0`。并对照 JS：**JS 里 `[]` 是 truthy，这是跨语言大坑**。

### ⑧ 练习 5：「不会写」→ 给骨架 → 要答案

**你的反馈**：「5 不会写」→ 给了 `if` 骨架（三处 `____` 待填）→ 「你直接把答案给我吧」

**按规则直接给了完整答案**（用户明确要答案时不再引导，避免干耗）：

```python
def denormalize_advice(scenario):
    if (
        scenario["read_per_sec"] > 100
        and scenario["write_per_day"] < 10
        and scenario["consistency"] == "low"
    ):
        return "denormalize"
    return "normalize"
```

**讲到的点**：
1. `and` = 同时成立，只要一条不满足就落到最后那行 → **不需要写 `else`**
2. `==` 是比较，`=` 是赋值（写错直接语法报错）
3. dict 取值只能用 `scenario["key"]`，**不能** `scenario.key`（第一阶段踩过，本次再记）

### ⑨ 代码 Review（测试全绿 ≠ 学完）

全绿后让你返工的三处「能过但糙」：

| # | 问题 | 你的进度 |
|---|---|---|
| ① | 变量名 `key` 装的其实是「违规列名」；`dict_item` 就是列名 | 第一轮改了练习 1、2 一半；练习 2/3 的 `key` 最终 Claude 一并改掉 |
| ② | 练习 2 里 `set(pk)` 写在**循环内**，每轮重算（不变量） | 最终 Claude 改掉 |
| ③ | 练习 1 可以像练习 3 一样用 `.items()` | 最终 Claude 改掉 |

**②讲解**：`pk` 整个循环不变却每轮 `set()` 一次 —— 同类更严重的版本是**数据库查询写在循环里**（100 条数据查 100 次库）。**循环里不变的东西，都该提到外面。**

### ⑩ 最严重的一处：同一行卡 3 次（`rows.items()`）

**你写的**（改了三次，始终是这一行）：

```python
for row in rows.items():        # ← rows 是 list，没有 .items()
```

**报错**（三次完全一样）：
```
AttributeError: 'list' object has no attribute 'items'
```

**根因**：`rows` 是 `list[dict]`，**两层结构**：

```python
rows = [
    {"order_id": 1, "product": "键盘,鼠标"},   # ← 元素是 dict，有 .items()
    {"order_id": 2, "product": "耳机"},
]
#  ↑ 整体是 list，没有 .items()
```

正确写法：

```python
for row in rows:                  # 外层：list → for 直接遍历
    for col, v in row.items():    # 内层：dict → 才有 .items()
```

**为什么改了三次都没对**：
1. 第一次：把外层循环整个删了，直接 `rows.items()`
2. 第二次：`for d in rows.items()` —— 只改了变量名，`.items()` 还在
3. 第三次：`for row in rows.items()` —— 又只改变量名，`.items()` 还在

→ **一直在改名字，没改「方法用错了类型」这件事。**

**现场验证（Claude 最后代跑）**：
```bash
python3 -c 'rows = [{"order_id": 1, "product": "键盘,鼠标"}]; print(type(rows)); print(type(rows[0]))'
# rows    的类型是: <class 'list'>
# rows[0] 的类型是: <class 'dict'>
```

**最终 Claude 直接改掉**（同一行卡 3 次不再反问，避免干耗）。

**⚠️ 这是一个模式，不是一次意外**：本次会话**两次**栽在同一件事上：
- 练习 3 初版 `for d in deps`：以为 `d` 是决定列，其实是 key → **拿错层**
- 练习 1 `rows.items()`：以为 `rows` 是 dict，其实是 list → **拿错层**

**经验（必记）**：遇到嵌套结构，先问「**我现在摸到的这一层，到底是什么类型？**」，然后 `print(type(x))` 验证，**不要猜**。

---

## 四、踩坑速查表

| # | 错误写法 | 报错 / 现象 | 正确写法 |
|---|---|---|---|
| 1 | `for d in deps:` 然后比 `d` | 例1 返回字符串、例2 结果错 | `for col, dep in deps.items():` 再 `for d in dep:` |
| 2 | `return d`（单个字符串） | `期望 ['user_city'] 实际 user_city` | 先攒进容器，末尾 `return list(...)` |
| 3 | `return [list(key)]` | `期望 ['product'] 实际 [['product']]` | `return list(key)` |
| 4 | `key = []` + `key.add(x)` | `AttributeError: 'list' object has no attribute 'add'` | list 用 `.append()`；set 才用 `.add()` |
| 5 | `for row in rows.items():` | `AttributeError: 'list' object has no attribute 'items'` | `for row in rows:`（list 直接遍历），`.items()` 只给 dict |
| 6 | `scenario.read_per_sec` | `AttributeError` | `scenario["read_per_sec"]` |
| 7 | 循环内 `set(pk)` | 不报错，但每轮重算 | 提到循环外 `pk_set = set(pk)` |
| 8 | 变量名 `key` 装违规列名 | 不报错，但**误导读者** | 用 `violations` / `bad_cols` |
| 9 | `if len(x) > 0:` | 不报错，但啰嗦 | Python 里 `if x:` —— 空集合天然为假 |

---

## 五、本次会话小结

**掌握 ✅**
- 三层范式的定义、违规形态、判断代码
- 部分依赖的前提（复合主键）与传递依赖的依赖链
- 复合主键存在的理由
- `deps.items()`、真子集判断、先攒后返回

**薄弱 ⚠️（下次重点）**
- **嵌套结构里「当前这一层是什么类型」** —— 本次两次栽在这里，练习 3 和练习 1
- 报错信息的阅读：报错冒号后的句子就是结论（`list` 没有 `add`），但改了三次还没对着报错改
- 变量命名、循环内不变量提取

**下一步**：学习项 10 — N+1 Problem（selectinload / joinedload）
