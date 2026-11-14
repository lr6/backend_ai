# 17 pytest — 学习笔记

> 状态：✅ 已完成（练习 1–8 全部通过，13 个测试 + 2 个收集规则 demo，2026-11-14 归档）
> 环境：pytest 9.2.0（装在项目 `.venv`）、Python 3.12.9
> 运行：`.venv/bin/python -m pytest 4工程化/17pytest/ -v`

---

## 一、知识点讲解

### 1. 为什么要写测试

此前验证 API 的方式：uvicorn 起服务 → curl → 肉眼判断。三个问题：

- **不可重复**：每次靠人记得跑哪些命令
- **无回归保护**：改了代码，不知道之前验证过的场景还对不对
- **人眼判断**：200 看着像对，字段拼错也发现不了

测试 = 把「验证步骤」写成代码，机器每次秒跑。

### 2. pytest 的发现规则（最重要的一条）

pytest 不是被 import 调用的库，而是**收集器**：

```
文件名：test_*.py 或 *_test.py
函数名：def test_*(...) 开头
```

**两条都要满足**：文件名决定「pytest 是否打开这个文件」，函数名决定「文件里的函数跑不跑」。

- 不符合 `test_` 的普通函数（如 `helper_check`）**永远不会被调用**，里面的错误 assert 也不会被执行
- 名字写错 **不会报错，只会静默跳过**——「测试全绿」可能是根本没跑
- **显式指定文件路径会绕过命名规则**：`pytest practice.py` 能跑，`pytest 4工程化/17pytest/` 不会收集 `practice.py`。本章因此把练习文件改名为 `test_practice.py`
- 用 `-v` 看 `collected N items`，数量不对先查命名

### 3. assert 与 pytest.raises

pytest 对 assert 做了改写：失败时自动展开表达式、显示实际值。

```python
assert calculate_discount(100, 20) == 80.0
```

失败输出：

```
E       assert 3 == 4
E        +  where 3 = add(1, 2)
```

**异常断言**：普通 assert 测不了「会抛错」——异常会在 assert 执行前抛出。用上下文管理器：

```python
with pytest.raises(ValueError, match="between"):
    calculate_discount(100, 150)
```

| 情况 | 结果 |
|---|---|
| 块内抛出匹配的类型 + 消息 | PASSED |
| 块内没抛 | FAILED（DID NOT RAISE） |
| 块内抛了别的类型 | FAILED |
| 只放会抛错的那一句调用，不要塞别的代码 | — |

`match` 是**正则**，写普通单词即子串匹配。

### 4. fixture：准备与清理的复用

```python
@pytest.fixture
def db():
    db = FakeDB()     # setup
    yield db          # 交给测试函数
    db.close()        # teardown

def test_db_insert_and_get(db):   # 参数名 = fixture 名
    ...
```

关键点：

1. **参数名即接线方式**：pytest 按测试函数参数名查找同名 fixture，注入 `yield` 出来的值
2. **`yield` 是分界线**：前 = 准备，后 = 清理；pytest 按 `try/finally` 语义执行，**测试失败也照样清理**
3. **默认 `scope="function"`**：每个测试各准备/清理一次
4. fixture 必须定义在**模块级或类级**；写在测试函数内部不会被注册，测试参数报 `fixture 'db' not found`
5. **fixture 可以依赖 fixture**：`def client(db): return make_client(db)`。依赖链按拓扑顺序创建、逆序销毁；同一次测试里拿到的 `db` 是**同一个实例**（可用 `is` 验证）

### 5. scope 选择

| scope | 执行次数 | 适合 |
|---|---|---|
| `"function"`（默认） | 每个测试各一次 | 会改数据的：DB Session、临时文件、mock 对象 |
| `"module"` | 每个文件各一次 | 文件内共享但不跨文件 |
| `"session"` | 整个进程一次 | 进程级无状态：engine / 连接池、测试服务器 |

**口诀：会改数据的往下放（function），不会改的往上放（session）。**

- `engine`（连接池）→ session scope ✅
- `session`（SQLAlchemy Session）→ function ✅，用 module ❌：Session 有状态（identity map、未提交改动），共享会互相污染
- **重要误区**：scope 隔离的是 Session 对象，不是数据库。`commit()` 过的数据，换新 Session 依然在；`rollback()` 只能撤销未提交的改动
- 真正隔离数据：① fixture teardown 里 `DELETE`/`TRUNCATE`；② 测试只 `flush` 不 `commit`，fixture 里 rollback；③ 每个测试独立库/事务沙箱

### 6. parametrize：一份逻辑，多组输入

前端 `test.each` 的对应物：

```python
@pytest.mark.parametrize("price, percent, expected", [
    (100, 0, 100.0),
    (100, 50, 50.0),
])
def test_calculate_discount_cases(price, percent, expected):
    assert calculate_discount(price, percent) == expected
```

- 每组数据收集成一个独立测试，ID 自动拼成 `test_...[100-50-50.0]`
- 失败时会列出**所有**失败组；for 循环写法则第一组失败就中断，后面根本没跑
- `ids=[...]` 可自定义名字；多个 parametrize 叠加 = 笛卡尔积

### 7. mock：只替换系统边缘

不能真碰的东西：第三方 API（要钱/不稳定）、时间、随机数、Redis/数据库（慢、有状态）。

`monkeypatch`（pytest 自带，测试结束自动还原）：

```python
def test_fetch_price(monkeypatch):
    calls = []

    def fake_get(url):
        calls.append(url)
        return FakeResponse({"price": 19.9})

    monkeypatch.setattr(httpx, "get", fake_get)
    assert fetch_price("A1") == 19.9
    assert calls == ["https://api.example.com/price/A1"]
```

注意 `monkeypatch` 是**对象**，要调它的方法 `setattr`，不能 `monkeypatch(...)`。

`MagicMock`（标准库）三件事：

```python
fake_cache = MagicMock()
fake_cache.get.return_value = None                      # 假返回
get_todo(fake_cache, 1)
fake_cache.set.assert_called_once_with("todo:1", {...}) # 交互断言
fake_cache.zzz.yyy.return_value = 1                      # 任意属性自动存在
```

交互断言测的是「怎么跟外部世界打交道」——能抓住 key 前缀写错、读写用了不同 key 这类 bug（学习项 16 踩过的坑）。

**mock 边界**（判断原则）：

| 对象 | mock？ | 理由 |
|---|---|---|
| Redis 客户端 | ✅ | 外部服务 |
| 数据库查询（单元测试） | ✅ | 外部服务 |
| 被测函数自己 | ❌ | mock 掉就什么都没测 |
| 自己写的纯函数（如 `build_cache_key`） | ❌ | 正是要测的逻辑，mock 会掩盖 bug |

单元测试 vs 集成测试（学习项 18）：单元测试里 DB 可以假；集成测试用真实测试库，只 mock 第三方外部服务。

### 8. ERROR vs FAILED

- **FAILED**：测试函数跑起来了，assert 失败或内部抛异常
- **ERROR**：测试函数根本没跑起来，通常是 fixture 找不到或 fixture 内部报错（如 `fixture 'client' not found`）

### 9. 属性 vs 方法（本次暴露的基础薄弱点）

```python
db.closed     # 属性：读状态，布尔值
db.close()    # 方法：执行动作，返回 None
```

- Python 里方法本身也是属性，所以 `db.close` 不报错，拿到的是 `<bound method ...>`，`is False` 自然不成立
- 命名规律：**动词方法 + 形容词属性**（标准库 `f.closed` / `f.close()` 同款）
- 前端同理：`arr.length` vs `arr.push()`；`btn.disabled` vs `btn.click()`
- 少写括号 = 拿函数当值用（静默错）；多写括号 = 把值当函数调（`TypeError: 'bool' object is not callable`）

---

## 二、练习 ↔ 知识点映射

| 练习 | 内容 | 对应知识点 |
|---|---|---|
| 1 | 两个基础测试 | 命名规则、裸 assert |
| 2 | `pytest.raises` + `match` | 异常断言 |
| 3 | 定义 `db` fixture | setup / yield / teardown |
| 4 | `client(db)` fixture | 依赖链、同一实例（`is`） |
| 5 | 填 assert | parametrize |
| 6 | 替换 `httpx.get` | monkeypatch、记录调用参数 |
| 7 | 两个 MagicMock 测试 | return_value、交互断言 |
| 8 | 补 conftest fixture | `conftest.py` 免 import 共享 |

---

## 三、练习纠错全记录

### 练习 1 — 一次通过

两条普通 assert，理解正确。

### 练习 2 — 「我完全不会」

用户明说不会，直接给答案。原因：`with pytest.raises` 是 pytest 独有语法，没写过推不出来。

写出 `match = "between"`，功能正确，仅提醒关键字参数习惯不写空格。

### 练习 3 — 三轮才通过

**第一轮：**

```python
def test_db_insert_and_get(db):
    @pytest.fixture
    def db():
        FakeDB = {}
        yield FakeDB
        FakeDB.close()
```

三个问题：

1. fixture 写在测试函数**内部** → 不会被注册，参数 `db` 报 `fixture 'db' not found`
2. `FakeDB = {}`：大写变量名覆盖了类名，且 `{}` 是空字典，应该 `FakeDB()`
3. 测试本体没写（insert / get / assert 全缺）

**第二轮：**

```python
assert db.close is False
```

失败输出：`assert <bound method FakeDB.close ...> is False`。没写括号，拿到的是方法对象。

**第三轮：**

```python
assert db.close() is False
```

更糟：真的执行了关闭动作（测试中途把资源释放了），且 `close()` 返回 `None`，`None is False` 永远失败。

**最终正确：**

```python
assert db.closed is False
```

**用户主动提问**：「close / closed 这第二个我真不知道」→ 说明从未建立「动作 + 状态自动联动」的类模型，单独讲了属性 vs 方法、同类标准库例子、前端类比。

### 练习 4 — 一次通过

`def client(db): return make_client(db)` + `assert client["db"] is db`，理解依赖链和同一实例。

### 练习 5 — 一次通过

把 `raise NotImplementedError` 换成一行 assert。

### 练习 6 — 直接要答案 + 一个手误

用户要求直接写，给完整代码。贴入时写成：

```python
monkeypatch(httpx, "get", fake_get)     # ❌ 少了 .setattr
```

报错 `TypeError: 'MonkeyPatch' object is not callable`。与 `close` / `closed` 同类：**对象本身 vs 对象上的方法**。

### 练习 7 — 「我不会」

直接给完整答案。`MagicMock` 的 `return_value`、`assert_called_once_with`、`assert_not_called` 均为新语法。

### 练习 8 — conftest 部分一次通过

`conftest.py` 的 `return {"title": "buy milk", "done": False}` 写对；测试本体一开始漏写，补上两条断言后通过。

### Review 收尾

1. 残留的注释模板（练习 3/4 上方 `# @pytest.fixture ...`）删除
2. PEP8 空行：顶层函数间 2 空行、`calls = []` 后空一行、import 分组（标准库 / 第三方）
3. **目录收集坑**：文件叫 `practice.py`，跑目录时不被收集（只跑了 demo 的 2 个）。显式传文件路径能跑，是因为绕过了命名规则。最终改名为 `test_practice.py`

---

## 四、踩坑速查表

| 错误写法 / 现象 | 报错或后果 | 正确写法 |
|---|---|---|
| 测试函数不叫 `test_*` | 静默跳过，`collected` 数量不对 | 函数名以 `test_` 开头 |
| 文件不叫 `test_*.py` | 跑目录时不收集；显式传路径才跑 | 改名 `test_*.py` / `*_test.py` |
| 没写 assert 的测试 | 永远 PASSED，什么都没测 | 测试必须有断言 |
| 直接写 `func(bad_input) == x` 测异常 | 测试因异常中断 | `with pytest.raises(E, match="..."):` |
| fixture 定义在测试函数内部 | `fixture 'db' not found`（ERROR） | fixture 放模块顶层 |
| `FakeDB = {}` | 覆盖类名；拿到 dict 不是实例 | `db = FakeDB()` |
| `db.close` | 拿到 bound method，`is False` 不成立 | `db.closed` |
| `db.close()` 写在断言里 | 提前关闭 + 返回 None | `db.closed is False` |
| `monkeypatch(...)` | `TypeError: 'MonkeyPatch' object is not callable` | `monkeypatch.setattr(...)` |
| mock 被测函数本身 / 自写纯函数 | 测试失去意义、掩盖 bug | 只 mock 外部系统边界 |
| 共享 Session 用 module scope | 测试互相污染、顺序相关 | 会改数据的用 function |
| 以为新 Session 就是干净库 | commit 过的数据仍在 | teardown 清数据 / 只 flush 不 commit |
| `pytest.raises` 块里塞多行代码 | 异常可能来自意外位置 | 块里只放会抛错的那一句 |

---

## 五、本章一句话总结

**pytest 靠命名收集测试，靠 fixture 管理准备/清理，靠 parametrize 覆盖多组输入，靠 mock 隔离外部世界；测试要测的是「你此刻关心的那一层」，不是 mock 越多越好。**
