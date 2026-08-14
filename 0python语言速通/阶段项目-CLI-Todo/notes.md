# 阶段项目：CLI Todo 工具 — 学习笔记

> 第零阶段 · 阶段项目（纯 Python，不碰 FastAPI）
> 本笔记随开发实时沉淀，工具完成后定稿。

---

## 一、项目规划

### 目标

用**纯 Python** 写一个命令行 Todo 工具，把第零阶段学的东西串起来用。

### 知识点 → 用途映射

| 学过的知识点 | 在这个项目里的用途 |
|-------------|------------------|
| 0.2 数据结构 | `list` 存所有 todo，`dict` 存单条 todo |
| 0.3 类型提示 | 给所有函数写类型注解 |
| 0.4 venv + pyproject.toml | 搭项目骨架、装 Pydantic |
| 0.6 Pydantic | `Todo` 模型 + 输入校验 |
| 🆕 argparse | 解析命令行参数（标准库，本项目新学） |

### MVP 功能（4 个命令 + 持久化）

```bash
todo add "学习 FastAPI"     # 添加一条 todo
todo list                  # 列出所有（带序号 + ✅/⬜ 状态）
todo done 1                # 把第 1 条标记为完成
todo delete 1              # 删除第 1 条
# 数据存到 todos.json，重启不丢
```

### 分步实现

1. 搭骨架（venv + pyproject.toml + 目录结构）
2. `models.py` — `Todo` 模型（Pydantic）
3. `storage.py` — `load_todos()` / `save_todos()` JSON 读写
4. `cli.py` — argparse + add/list/done/delete 逻辑
5. 跑起来手动测试每个命令

---

## 二、models.py（✅ 已完成）

### 知识点讲解

**1. Pydantic 定义模型**（串 0.6）

```python
from pydantic import BaseModel, Field

class Todo(BaseModel):
    title: str = Field(min_length=1)   # 标题，非空
    done: bool = False                 # 完成状态，默认 False
```

| 字段 | 类型 | 约束/默认值 | 为什么 |
|------|------|------------|--------|
| `title` | `str` | `Field(min_length=1)` | 防止 `add ""` 空标题 |
| `done` | `bool` | `= False` | 新建时默认未完成 |

**2. 模型也能有方法（`mark_done`）**

Pydantic 模型默认是可变对象，所以 `self.done = True` 这种直接赋值是允许的。模型里可以定义自己的方法。

**3. 一个设计决策：MVP 不加 `id` 字段**

「序号」直接用 list 的位置（`index + 1`）表示——`todo done 1` 就是操作 `list[0]`，删掉后重新编号。等数据进了数据库（第二阶段）再引入真正的 `id`。

### 纠错记录

**问题 1：`mark_done` 方法不会写 —— 核心是 `self` 是什么**

- **现象**：用户问「你说的 mark_done 方法不知道咋弄」。
- **原因**：对类方法里 `self` 的含义不清楚。
- **知识点**：在 `class` 里定义方法，第一个参数固定是 `self`，代表「当前这个实例」。调用时不用传，Python 自动传。
- **前端类比**：`self` 相当于 JS 里的 `this`。

```python
def mark_done(self) -> None:
    self.done = True   # self ≈ JS 的 this
```

```js
class Todo { markDone() { this.done = true; } }  // this ≈ Python 的 self
```

- **解决**：`self.done = True` 就是「把当前这个 todo 实例的 done 改成 True」。

**问题 2：类名写成小写 `todo`（反复两次才改对）**

- **现象**：`class todo` 小写，review 两轮才改成 `Todo`。
- **原因**：Python 命名规范（PEP8）不熟。
- **知识点**：**类名用 PascalCase（`Todo`）**，变量和函数用 snake_case（`todo`）。
- **为什么重要**：后面 `cli.py` 要 `from todo.models import Todo` 引用它，类名一致才清晰。

### 踩坑速查表

| 错误写法 | 问题 | 正确写法 |
|---------|------|---------|
| `class todo` | 类名应大驼峰 | `class Todo` |
| `mark_done()` 没写 `self` | 缺实例引用参数 | `def mark_done(self):` |
| `return self.done = True` | 方法体里直接赋值即可 | `self.done = True` |

---

## 三、storage.py（✅ 已完成）

### 知识点讲解

**1. `json` 库读写文件**（标准库，类似前端 `JSON.parse` / `JSON.stringify`，但读写文件）

```python
import json

# 读：文件对象 → Python 对象（list/dict）
with open("todos.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 写：Python 对象 → 文件
with open("todos.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

> `ensure_ascii=False` 让中文不变成 `\uXXXX`；`indent=2` 让文件缩进好看。

**2. Pydantic 模型 ↔ dict 转换**（串 0.6）

```python
t.model_dump()          # Todo → dict，如 {"title": "x", "done": False}
Todo.model_validate(d)  # dict → Todo
```

> 关键：`json` 库不认识 Pydantic 模型，只能处理 dict/list。所以**写之前** `model_dump()` 转 dict，**读之后** `model_validate()` 转回 Todo。

**3. 列表推导式批量转换**（串 0.2）

```python
[Todo.model_validate(d) for d in data]   # list[dict] → list[Todo]
[t.model_dump() for t in todos]          # list[Todo] → list[dict]
```

**4. 文件不存在处理**（两条路任选）

```python
# 方式 A：先判断
if not os.path.exists(DATA_FILE):
    return []

# 方式 B：try/except
try:
    open(DATA_FILE)
except FileNotFoundError:
    return []
```

### 纠错记录

**问题：`save_todos` 第一版有 3 个 bug**（用户独立写的，review 时发现）

第一版代码：
```python
def save_todos(todos: list[Todo]) -> None:
    arr = [t.model_dump() for t in todos]
    for x in arr:
        with open('todos.json', 'w', encoding='utf-8') as f:
            json.dump(json.load(f), x, ensure_ascii=False, indent=2)
```

**bug 1：`json.dump` 参数顺序反了**

- 现象：`json.dump(obj, fp)` 是「数据在前、文件对象在后」，却写成了 `json.dump(json.load(f), x)`——把读结果当数据、把 dict `x` 当文件对象。
- 知识点：`json.dump(obj, fp)` ≈ `fs.writeFileSync(path, JSON.stringify(obj))`，数据是「内容」，文件对象是「往哪写」，别混。

**bug 2：`'w'` 模式下又去 `json.load(f)` 读文件**

- 现象：`open(..., 'w')` 一打开就清空文件，紧接的 `json.load(f)` 读到空文件，报 `JSONDecodeError: Expecting value: line 1 column 1 (char 0)`——这是运行时**第一个**触发的错误。
- 知识点：写文件（dump）时根本不需要读（load），load/dump 别混在一句。

**bug 3：`for x in arr` 循环重复写互相覆盖**

- 现象：`'w'` 是覆盖不是追加，循环每次写都清掉上一次，最终文件只剩最后一条 todo。
- 知识点：想写整个列表就**一次性写**，不要循环；追加才用 `'a'`。

**正确写法**：
```python
def save_todos(todos: list[Todo]) -> None:
    arr = [t.model_dump() for t in todos]
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(arr, f, ensure_ascii=False, indent=2)
```

**小瑕疵**：`load_todos` 硬编码 `'todos.json'` 没用 `DATA_FILE` 常量，一并改成统一。

### 踩坑速查表

| 错误写法 | 问题 | 正确写法 |
|---------|------|---------|
| `json.dump(json.load(f), x)` | 参数顺序反了 + 不该读 | `json.dump(arr, f)` |
| `open(..., 'w')` 后又 `json.load(f)` | w 已清空，读到空文件报错 | 写就别读 |
| `for x in arr:` 循环里 `open(..., 'w')` | 覆盖互相清空，只剩一条 | 一次性 `json.dump(arr, f)` |
| `open('todos.json')` 硬编码 | 换文件名要改多处 | 用 `DATA_FILE` 常量 |

---

## 四、cli.py（✅ 已完成）

### 知识点讲解（argparse 是全新知识点）

**1. argparse 是什么**

Python 标准库，解析命令行参数。前端类比：Node 的 `commander.js` / `yargs`，把 `process.argv` 解析成结构化数据。

**2. 三个核心概念**

| 概念 | 说明 | 代码 |
|------|------|------|
| 子命令 | `git add` / `git commit` 这种「主命令 + 子命令」 | `parser.add_subparsers(dest="command", required=True)` |
| 位置参数 | `todo add "标题"` 里必需、按位置传的参数 | `p_add.add_argument("title", type=str)` |
| type 转换 | 自动把 `"1"` 转成 `int 1` | `p_done.add_argument("index", type=int)` |

**3. 数据流（关键认知：函数不用自己「读」命令行）**

```
命令行 todo add "学习 FastAPI"
   ↓ argparse 解析
args = { command: "add", title: "学习 FastAPI" }
   ↓ main() 里的 if 分发
cmd_add(args.title)  →  title 参数已经是 "学习 FastAPI"
```

> 前端类比：就像事件回调 `onClick = (e) => {...}`，浏览器已把事件对象 `e` 传进来，你不用自己「读」用户点了哪。`title` 就相当于已传进来的 `e`。

### 纠错记录

**问题 1（提问）：「cmd_add 怎么写，怎么读取 todo add xxx」**

- 现象：卡在 cmd_add，纠结「怎么读取命令行」。
- 原因：混淆「解析命令行」（argparse 的活）和「处理逻辑」（cmd_add 的活）。
- 知识点：**参数是 argparse 解析好、通过函数参数传进来的，函数里直接用参数，不用自己读命令行**（见数据流图）。

**问题 2：cmd_add 缺 print 确认**

- 现象：第一版漏了 `print`，敲 `add` 后屏幕没反馈。
- 知识点：命令行工具反馈很重要——数据存进去了用户看不到确认会以为失败。

**问题 3：cmd_list 的 f-string 硬编码「标题」**

- 现象：`print(f"{ind}. {status} 标题")` → 输出 `1. ⬜ 标题`，实际标题没出来。
- 原因：f-string 里 `{ind}`、`{status}` 用了花括号，「标题」却漏了花括号写成了死字符串。
- 知识点：应写变量 `{t.title}`。类比 JS 模板字符串漏写 `${t.title}`。

**问题 4：cmd_delete 漏了 save_todos（改内存 ≠ 持久化）**

- 现象：`delete 2` 打印「已删除」，再 `list` 那条还在。
- 原因：`arr.pop()` 只改内存里的列表，没 `save_todos(arr)` 写回文件，下次 load 又从文件读回。
- 知识点：**改内存 ≠ 持久化**。类比前端改了 state 但忘了调 API 存后端 / 忘了 `localStorage.setItem`。

### 踩坑速查表

| 错误写法 | 问题 | 正确写法 |
|---------|------|---------|
| `print(f"... 标题")` | 死字符串，不是变量 | `print(f"... {t.title}")` |
| `arr.pop(index-1)` 后没 save | 只改内存没持久化 | 补 `save_todos(arr)` |
| `Todo(title = title)` | 关键字参数 `=` 不该有空格 | `Todo(title=title)` |
| `arr[index -1]` | 二元运算符 `-` 两边要空格 | `arr[index - 1]` |
| 「代办」 | 错别字，Todo 是「待办」 | 「待办」 |

---

## 五、跑起来（✅ 已完成）

完整流程测试通过：空列表 → add ×3 → list → done → list → delete → list → 越界，4 个命令全部正常，持久化正确，删除后序号正确重排。

---

## 六、项目总结

### 这个项目串起了哪些知识点

| 知识点 | 落地位置 |
|--------|---------|
| 0.2 数据结构 | `list` 存 todo 列表、`dict` 存单条 |
| 0.3 类型提示 | 所有函数签名 `-> list[Todo]` 等 |
| 0.4 包管理 | venv + pyproject.toml + .gitignore |
| 0.6 Pydantic | `Todo` 模型、`Field` 约束、`model_dump`/`model_validate` |
| 🆕 argparse | 子命令 + 位置参数 + `type=int` |
| 🆕 json | `json.load`/`json.dump` 读写文件持久化 |

### 核心收获

1. **分层设计**：`models.py`（数据）→ `storage.py`（持久化）→ `cli.py`（交互）三层分离，各管一件事。这是后端项目的基本骨架，后面 FastAPI 也是这个思路。
2. **持久化的本质**：内存里的数据（list）和磁盘上的数据（json 文件）是两份，必须显式 `save`/`load` 同步。改了内存忘了 save，数据就丢了。
3. **命令行工具的结构**：argparse 解析参数 → main 分发 → 各命令函数处理，参数通过函数参数传递，不是全局变量。
