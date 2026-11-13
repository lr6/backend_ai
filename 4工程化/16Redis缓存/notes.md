# 16 Redis 缓存 — 学习笔记

> 状态：✅ 已完成（练习 1–7 全部通过，2026-11-13 归档）
> 日期：2026-11-12 ~ 2026-11-13
> 环境：Redis 8.10.3（brew）、redis-py 8.1.0、练习统一使用 db=15

---

## 一、知识点讲解

### 1. 缓存的本质：用内存空间换数据库时间

```
没有缓存：
  浏览器 → FastAPI → PostgreSQL 查表 → 返回

有缓存：
  浏览器 → FastAPI → Redis 里有没有？有 → 直接返回
                         └→ 没有 → 查 PostgreSQL → 存进 Redis → 返回
```

前端类比：

| 前端 | 后端 |
|------|------|
| `computed`：依赖没变，不重新算，直接用上次结果 | Redis：数据没变，不查库，直接返回上次结果 |
| 计算很贵（遍历大数组）才值得用 computed | 查询很贵（JOIN、聚合、慢 SQL）才值得加缓存 |
| 依赖一变，computed 自动重算 | **数据库一变，缓存需要你手动失效** |

关键差别：Vue 的 `computed` 靠响应式系统自动知道依赖变了；后端缓存没有魔法，数据改了缓存不会自己更新。本章大部分复杂度都来自这里。

### 2. Cache-Aside（旁路缓存）

读路径：

```
1. GET cache_key
2. 命中   → 直接返回（不碰数据库）
3. 未命中 → 查数据库
4. 查到   → SET cache_key 结果 + EX 60（带 TTL 写回）
5. 返回
```

第 4 步一定要带过期时间。TTL 是最后的安全网：一旦哪里漏删缓存，脏数据最多存活到 TTL 到期。

### 3. 写时的失效策略

| 做法 | 写操作时做什么 | 特点 |
|------|---------------|------|
| **删缓存**（最常用） | 更新 DB → `DEL cache_key` | 下次读时自然回填；缓存里没有脏数据窗口 |
| **更新缓存** | 更新 DB → 同时 `SET cache_key 新值` | 两次写可能不一致；数据没人读就白写 |
| **只靠 TTL** | 什么都不做，等过期 | 最终一致，简单；适合晚几十秒也能接受的数据 |

主流：**读 Cache-Aside + 写时删缓存 + TTL 兜底**。

为什么是「删」而不是「更新」：并发下两次 SET 的顺序不一定和 DB 提交顺序一致；「删」只留一个空位，下次读谁按 DB 当时的值回填，天然以 DB 为准。

### 4. 先删缓存 还是 先更新数据库？

**结论：先更新数据库，再删缓存。**

先删缓存再更新 DB 的翻车时间线：

```
读请求 R:        查缓存 miss ─→ 查 DB（读到旧值"买菜"）─────────→ SET 缓存="买菜"
写请求 W:   DEL 缓存 ─→ 更新 DB（改成"做饭"，提交）
```

结果：DB 是「做饭」，缓存是「买菜」，不一致要挂到 TTL 到期。窗口很宽，因为「删缓存」到「DB 提交」之间有实打实的时间差。

先更新 DB 再删缓存的失败风险小得多：DB 更新失败时缓存根本没删，仍然一致。最坏情况是极刁钻的**缓存回填竞争**：

```
R: 查缓存 miss → 查 DB 读到旧值 "买菜"
W:        更新 DB 为 "做饭" → DEL 缓存
R:                                    SET 缓存 = "买菜"  ← 又把旧值写回去了
```

窗口只有「R 查完库到 R 写缓存」这一小段。生产中常见的兜底：

- **TTL** 当最终保险
- **延迟双删**：写完 DB 删一次，隔几百毫秒再删一次
- 接受**最终一致性**，不追求强一致

### 5. redis-py 基本 API

```python
import redis

r = redis.Redis(host="localhost", port=6379, db=15, decode_responses=True)
```

- `decode_responses=True`：读出来是 `str`，不加则是 `bytes`（打印成 `b"world"`）
- `db=15`：Redis 默认有 16 个逻辑库（0–15），练习用 15 号库，不污染别的数据

| 操作 | 方法 | 注意 |
|------|------|------|
| 写 | `r.set(key, value)` | 返回 `True` |
| 写 + 过期 | `r.set(key, value, ex=60)` | `ex` 单位是**秒** |
| 读 | `r.get(key)` | 不存在返回 `None` |
| 删 | `r.delete(key)` | 返回删掉了几个 key |
| 剩余寿命 | `r.ttl(key)` | `-1`=永不过期，`-2`=key 不存在 |
| 是否存在 | `r.exists(key)` | 返回 `0/1` |

**Redis 只存字符串**（严格说是二进制），Python 对象要自己序列化：

```python
r.set("todo:1", json.dumps(todo_dict), ex=60)
todo = json.loads(r.get("todo:1"))
```

### 6. 缓存穿透与哨兵值

缓存穿透：请求的 id 在数据库里根本不存在，导致每次请求都缓存未命中、每次都查库。缓存完全没起作用，请求「穿过」缓存直接打到 DB。恶意刷不存在的 id 可以打挂数据库。

解法（本次练习）：数据库也查不到时，**别让缓存空着**，写入约定标记 `"__missing__"`，TTL 30 秒。

```
请求 999 → 缓存没有 → 查库 → 没有 → SET todo:999 = "__missing__" (30s) → 返回 None
请求 999 → 缓存命中 "__missing__" → 直接返回 None，不碰数据库
```

- 「哨兵值」= 占位标记，意思是「这个 id 数据库里也没有，别再查了」
- 缓存里会有三种值：`None`（没缓存）/ `"__missing__"`（查无此数据）/ JSON 字符串（真实数据）
- 顺序：**先判断 `"__missing__"`，再 `json.loads`**，否则 `json.loads("__missing__")` 抛 `JSONDecodeError`
- 哨兵 TTL 要短：如果这个 id 后来真的被创建了，哨兵过期后第一次请求就能查到新数据；永不过期会把真数据挡住

### 7. Hash：一个 key 下挂多个字段

之前练习 3–5 用 `json.dumps` 把整个对象塞成一个字符串 —— 对应前端 `localStorage.setItem('todo', JSON.stringify(obj))`：改一个字段要整个取出来 parse、改完再整个写回去。

Hash 更像 Vue 的 `reactive({ name, age })`：一个 key 下挂多个 field，每个字段能单独读写。

```
user:1  →  { name: "阿波",  age: "30" }
```

| 操作 | 方法 | 注意 |
|------|------|------|
| 批量写字段 | `r.hset(key, mapping=data)` | `mapping=` 直接吃一个 dict |
| 读全部字段 | `r.hgetall(key)` | 只接受 key 一个参数；key 不存在返回 `{}` |

- Redis 存的仍是字符串：`{"age": 30}` 写进去，`hgetall` 读出来是 `{"age": "30"}`
- `hgetall` 是**读**方法，不能拿来写 —— 写必须用 `hset`
- 改单个字段只需 `hset(key, "age", 31)`，不用搬动整个对象，这是 Hash 相对 JSON 字符串的收益

### 8. Sorted Set：排行榜

和 Hash 长得像，区别是每个成员带一个**分数（score）**，Redis 自动按分数排好序。

前端类比：Vue 里做排行榜你会写

```js
const top3 = computed(() => list.sort((a, b) => b.score - a.score).slice(0, 3))
```

Sorted Set 是**存进去就排好了**，取的时候不用自己 sort。

| 操作 | 方法 | 注意 |
|------|------|------|
| 写/更新分数 | `r.zadd(key, mapping={name: score})` | 同名成员分数被覆盖，不会多出一行 |
| 取前 N 名 | `r.zrevrange(key, 0, 2)` | 按分数从高到低；返回成员名列表 |

- `zrevrange` 的 `0, 2` 是**闭区间**（start、stop 都包含），正好是前 3 名；和 Python 的 `[:3]` 左闭右开不同
- 按分数从低到高是 `zrange`，从高到低是 `zrevrange`（rev = reverse）

---

## 二、练习 ↔ 知识点映射

| 练习 | 内容 | 对应知识点 | 状态 |
|------|------|-----------|------|
| 1 | `get_client` 建立连接 | redis-py 连接、`decode_responses` | ✅ |
| 2 | `set_with_ttl` / `get_ttl` | `set(ex=)`、`ttl` 的 -1/-2 | ✅ |
| 3 | `get_todo_cached` | Cache-Aside 读 + JSON 序列化 | ✅ |
| 4 | `update_todo` | 写时删缓存（先库后缓存） | ✅ |
| 5 | `get_todo_cached_v2` | 缓存穿透、空值哨兵 | ✅ |
| 6 | `save_user_hash` / `load_user_hash` | Hash 存对象 | ✅ |
| 7 | `add_score` / `top3` | Sorted Set 排行榜 | ✅ |

---

## 三、练习纠错全记录

### 检查问题（课上回答）

1. **缓存 60 秒内新建 todo，再读列表能看到吗？** → 答对：看不到，旧缓存没过期。思路提出「数据库更新后通知缓存失效」→ 正是 Cache-Aside。
2. **先删缓存再更库 vs 先更库再删缓存？** → 选对 2（先更库），但不知道选错会怎样。讲解了时间线与缓存回填竞争。
3. **读接口的步骤？** → 答对：先查缓存，没有则查库，然后写缓存。

### 练习 1：参数写死

```python
# 错误
def get_client(host="localhost", port=6379, db=15):
    return redis.Redis(host="localhost", port=6379, db=15, decode_responses=True)
```

- 现象：测试通过，但函数收了参数却不用
- 原因：参数成了摆设，换环境（测试库/远程 Redis）时不听调用方
- 解决：`host=host, port=port, db=db`
- 知识点：函数参数即契约

### 练习 3：四轮才改对

**第 1 版**

```python
todo = client.get(todo_id)
if todo is None:
    todo = FAKE_DB[todo_id]
    if todo is not None:
        client.set(todo_id, f"todo: {todo_id}", ex=60)
    return None
```

问题：
1. key 没有 `todo:` 前缀，且读写没有统一
2. 缓存命中分支没有返回值
3. 回填的内容是 `f"todo: {todo_id}"` 这行字，不是 todo 的 JSON
4. `FAKE_DB[todo_id]` 对不存在的 id 抛 `KeyError`

**第 2 版**

```python
todo = client.get(todo_id)
if todo is None:
    todo = FAKE_DB[todo_id]
    if todo is not None:
        client.set(f"todotodo_id: {todo_id}", json.dumps(todo), ex=60)
    return None
return json.loads(todo)
```

进步：命中路径 `json.loads` 对了，回填用 `json.dumps` 了。
剩余：读仍用 `todo_id`；写成了 `f"todotodo_id: {todo_id}"`（f-string 拼错，输出 `todotodo_id: 1`）；查到了仍 `return None`；`FAKE_DB[...]` 仍会 KeyError。

**第 3 版**

```python
todo = client.get(todo_id)
if todo is None:
    todo = FAKE_DB[todo_id]
    if todo is not None:
        client.set(f"todo_id:{todo_id}", json.dumps(todo), ex=60)
        return todo
    return None
return json.loads(todo)
```

进步：`return todo` 对了。
剩余：写成了 `todo_id:` 而不是 `todo:`；读仍未加前缀；`FAKE_DB[...]` 仍 KeyError。

**第 4 版（正确）**

```python
key = f"todo:{todo_id}"
todo = client.get(key)
if todo is None:
    todo = FAKE_DB.get(todo_id)
    if todo is not None:
        client.set(key, json.dumps(todo), ex=60)
        return todo
    return None
return json.loads(todo)
```

核心教训：**key 只在一处定义（`key = f"todo:{todo_id}"`），读写共用同一个变量**，手拼 key 容易出现「读一个、写另一个」。

### 练习 4：两轮改对

**第 1 版**

```python
todo = FAKE_DB[todo_id]
if todo is None: return
todo["title"] = new_title
FAKE_DB[todo_id] = todo
client.delete(todo_id)
```

问题：
1. `FAKE_DB[todo_id]` 对 999 抛 `KeyError` → `.get(todo_id)`
2. `client.delete(todo_id)` 删的是 `"2"`，缓存实际在 `"todo:2"`
3. `FAKE_DB[todo_id] = todo` 多余（同一个 dict 对象）

**第 2 版（正确）**

```python
key = f"todo:{todo_id}"
todo = FAKE_DB.get(todo_id)
if todo is None:
    return
todo["title"] = new_title
client.delete(key)
```

### 练习 5：三轮改对（含一次观点分歧）

**第 1 版**

```python
if todo == "__missing__": return None
if todo is None:
    todo = FAKE_DB.get(todo_id)
    if todo is None:
        client.set(key, "__missing__", ex=30)
    client.set(key, json.dumps(todo), ex=30)
    return todo
```

问题：
1. 写完哨兵后没有停下，下一行 `json.dumps(None)` 得到 `"null"`，把哨兵盖掉
2. 缓存命中真实 JSON 时没有 `return json.loads(todo)`，二次调用返回 `None`
3. 正常数据 TTL 写成 30，应 60
4. 测试没覆盖「二次调用命中缓存」，所以第 2 个 bug 测试抓不到——**测试全绿 ≠ 没 bug**

**分歧点：用户认为「FAKE_DB 查到 / 查不到本来就是两个分支」**

```python
        if todo is None:
            client.set(key, "__missing__", ex=30)   # 比 if 多缩进 → 属于 if
        client.set(key, json.dumps(todo), ex=30)    # 和 if 对齐 → 在 if 外面
```

讲解：
- Python 没有大括号，**缩进就是大括号**。第 128 行和内层 `if` 左对齐，说明它已经退出内层 if，无条件执行。
- 等价 JS：`if (todo === null) { set哨兵 } set正常值;` —— 第二条 set 不在 if 块里。
- 铁证：测试实际缓存值是 `"null"` 而不是 `"__missing__"`，说明第二次 set 确实执行了。
- 改法：哨兵分支里 `return None`，或补 `else:`。

**第 2 版（正确）**

```python
key = f"todo:{todo_id}"
todo = client.get(key)

if todo == "__missing__":
    return None

if todo is None:
    todo = FAKE_DB.get(todo_id)
    if todo is None:
        client.set(key, "__missing__", ex=30)
    else:
        client.set(key, json.dumps(todo), ex=60)
    return todo

return json.loads(todo)
```

额外手动验证（测试没覆盖的路径）：

```
第一次（查库）: {'id': 3, 'title': '健身', 'done': False}
第二次（命中缓存）: {'id': 3, 'title': '健身', 'done': False}
不存在 id: None | 缓存: __missing__
```

### 练习 6：读写方法混用（两处）

**第 1 版**

```python
def save_user_hash(client, user_id, data):
    key = f"user:{user_id}"
    client.hgetall(key, json.dumps(data))

def load_user_hash(client, user_id):
    key = f"user:{user_id}"
    # 空
```

问题：
1. `hgetall` 是**读**方法，不是写方法 —— 写 Hash 要用 `hset`
2. `hgetall` 只接受 key **一个**位置参数，多塞的 `json.dumps(data)` 会被当成非法参数
3. Hash 是结构化的，不该再 `json.dumps` 整个对象再塞进去（那就退回字符串存储了）
4. `load_user_hash` 没写

**第 2 版（正确）**

```python
def save_user_hash(client, user_id, data):
    key = f"user:{user_id}"
    client.hset(key, mapping=data)

def load_user_hash(client, user_id):
    key = f"user:{user_id}"
    return client.hgetall(key)
```

`hgetall` 对不存在的 key 天然返回 `{}`，不需要额外判断。

### 练习 7：方法名手滑 + 读写 key 不一致

**第 1 版**

```python
def add_score(client, name, score):
    key = '1cc'
    client.zdd(key, mapping={name: score})

def top3(client):
    key = '1cc'
    return client.zrevrange(key, 0, 2)
```

问题：
1. `zdd` 不存在 → `AttributeError`，正确方法是 `zadd`
2. key 写成了 `'1cc'`，和 docstring / 测试约定的 `"leaderboard"` 不一致 —— 练习 3 踩过的「读一个 key、写另一个 key」再现

**第 2 版（正确，测试却报错）**

```python
key = "leaderboard"
client.zadd(key, mapping={name: score})
...
return client.zrevrange(key, 0, 2)
```

测试提示 `期望 ['carol', 'bob', 'alice']，实际 ['bob', 'carol', 'alice']`。

**这次是 Claude 的测试期望值写错了**：

```
redis-cli -n 15 zrange leaderboard 0 -1 withscores
alice 100 / carol 120 / bob 150   ← bob 最后一次被更新成 150
```

分数从高到低应为 `bob(150) → carol(120) → alice(100)`，用户实现完全正确。测试期望值和 `top3` 的 docstring 示例一并修正。

教训（两边都适用）：
- **测试失败先怀疑测试本身**：拿真实数据验证（`redis-cli` 看现场），而不是直接改实现去迎合期望值 —— 这次如果反过来改代码，就会写出一个错误的降序逻辑
- 加分数是「更新」语义，同名成员不会重复；这正是 `zadd` 相对于 list 的价值

### 通过后的代码 Review

测试全绿后按三层检查（能跑 → 逻辑对 → 工程质量）：

1. **练习 1 参数写死**：签名收了 `host/port/db`，函数体仍写死 `"localhost"`、`6379`、`15` → 改为传参
2. **残留 `# TODO`**：练习 1、2 里代码已实现但 TODO 注释没删 → 删除
3. **练习 4 冗余赋值**：`todo["title"] = new_title` 后 `FAKE_DB[todo_id] = todo` 是空操作（同一个 dict 对象）→ 删除
4. **格式**：行尾空格 2 处、连续空行、单双引号不统一、练习 5 的 `if ...: return` 单行写法 → 统一清理

### 用户主动提问

1. **「命中哨兵值是什么意思？」** → 重新解释了缓存穿透、哨兵值的作用、三种缓存值、判断顺序
2. **「问题 1 我不认可，这是两个分支呀」** → 缩进即大括号，代码实际不是互斥分支

---

## 四、踩坑速查表

| 错误写法 | 报错 / 现象 | 正确写法 |
|----------|------------|---------|
| `client.get(todo_id)` / `set(f"todo_id:{id}")` | 缓存 key 对不上，测试读不到 | `key = f"todo:{todo_id}"`，读写共用 |
| `f"todotodo_id: {todo_id}"` | key 变成 `todotodo_id: 1` | `f"todo:{todo_id}"` |
| 内层 `if` 后直接写 `set` | 哨兵被覆盖成 `"null"` | 分支内 `return None` 或用 `else` |
| `json.dumps(None)` | 得到字符串 `"null"` | 查无数据时写哨兵或不写 |
| `FAKE_DB[todo_id]` | `KeyError` | `FAKE_DB.get(todo_id)` |
| 缓存命中无 `return` | 二次调用返回 `None`，测试可能漏测 | `return json.loads(cached)` |
| `client.delete(todo_id)` | 删错 key，缓存还在 | `client.delete(key)` |
| 函数参数写死 | 测试通过但换环境失效 | 用传入的参数 |
| `json.loads("__missing__")` | `JSONDecodeError` | 先判断哨兵，再 loads |
| `hgetall(key, json.dumps(data))` | 用读方法写；多传参数报错 | `hset(key, mapping=data)` 写，`hgetall(key)` 读 |
| Hash 存对象前再 `json.dumps` | 退回字符串存储，失去 Hash 的意义 | 直接 `mapping=data` |
| `client.zdd(...)` | `AttributeError` | `zadd` |
| `add_score` 和 `top3` 用不同 key | 写进去读不到 | 两处都用 `"leaderboard"` |
| 测试期望值和真实数据不符 | 断言失败但实现没问题 | 用 `redis-cli ... withscores` 看现场再决定改哪边 |

---

## 五、完成情况

- 练习 1–7 全部通过（`.venv/bin/python 4工程化/16Redis缓存/practice.py` → 🎉）
- 代码 Review 已完成：参数写死、残留 TODO、冗余赋值、格式问题全部清理
- 学习项 16 → ✅，总进度 22/32
- 踩过的 key：`todo:{id}`（Cache-Aside）、`user:{id}`（Hash）、`leaderboard`（ZSet）
- 下一学习项：**17 pytest**
