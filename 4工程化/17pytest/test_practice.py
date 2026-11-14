"""
第四阶段 · 17 pytest — 检验练习

这个文件不直接用 python 运行，而是交给 pytest 收集运行：

    .venv/bin/python -m pytest 4工程化/17pytest/practice.py -v

每个 TODO 需要你补一段测试代码。
全部 PASSED = 17 pytest 过关 ✅
"""

from unittest.mock import MagicMock

import httpx
import pytest

# ============================================
# 被测代码，不要修改下面内容
# ============================================


def calculate_discount(price: float, percent: float) -> float:
    """按百分比打折，返回保留两位小数的价格；percent 超出 0-100 抛 ValueError。"""
    if not (0 <= percent <= 100):
        raise ValueError("percent must be between 0 and 100")
    return round(price * (100 - percent) / 100, 2)


class FakeDB:
    """内存版数据库，用于练习 fixture。"""

    def __init__(self):
        self.rows: dict[int, dict] = {}
        self.closed = False

    def insert(self, item_id: int, data: dict) -> None:
        self.rows[item_id] = data

    def get(self, item_id: int) -> dict | None:
        return self.rows.get(item_id)

    def close(self) -> None:
        self.closed = True
        self.rows.clear()


def make_client(db: FakeDB) -> dict:
    """模拟一个依赖数据库的 API 客户端。"""
    return {"db": db, "name": "todo-client"}


class FakeResponse:
    """替代 httpx.Response 的假响应。"""

    def __init__(self, payload: dict):
        self._payload = payload

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        return None


def fetch_price(sku: str) -> float:
    """调用第三方接口拿价格（测试时不要真发请求）。"""
    resp = httpx.get(f"https://api.example.com/price/{sku}")
    resp.raise_for_status()
    return resp.json()["price"]


def get_todo(cache, todo_id: int) -> dict:
    """Cache-Aside：先查缓存，未命中再查库并回填。"""
    key = f"todo:{todo_id}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    data = {"id": todo_id, "title": "from db"}
    cache.set(key, data)
    return data


# ============================================
# 练习 1：写你的第一个测试
# ============================================


def test_calculate_discount_normal():
    """
    验证 calculate_discount(100, 20) == 80.0。
    """
    assert calculate_discount(100, 20) == 80.0


def test_calculate_discount_no_discount():
    """
    验证 calculate_discount(99.99, 0) == 99.99。
    """
    assert calculate_discount(99.99, 0) == 99.99


# ============================================
# 练习 2：pytest.raises
# ============================================


def test_calculate_discount_invalid_percent():
    """
    percent=150 时应抛出 ValueError。

    要求：
    1. 用 pytest.raises 捕获 ValueError
    2. 用 match="between" 验证报错信息里包含 between
    """
    with pytest.raises(ValueError, match="between"):
        calculate_discount(100, 150)


# ============================================
# 练习 3：fixture 的准备与清理
# ============================================


@pytest.fixture
def db():
    db = FakeDB()
    yield db
    db.close()


def test_db_insert_and_get(db):
    """
    插入一条数据再取回，验证内容一致。
    同时断言 db.closed is False（说明测试进行中还没清理）。
    """
    mock_data = {"id": 1, "title": "buy milk"}
    db.insert(1, mock_data)

    row = db.get(1)
    assert row == mock_data
    assert db.closed is False


# ============================================
# 练习 4：fixture 依赖 fixture
# ============================================


@pytest.fixture
def client(db):
    return make_client(db)


def test_client_shares_db(client, db):
    """
    断言 client["db"] is db。
    验证依赖链里拿到的是同一个对象，不是各建各的。
    """
    assert client["db"] is db


# ============================================
# 练习 5：parametrize
# ============================================


@pytest.mark.parametrize(
    "price, percent, expected",
    [
        (100, 0, 100.0),
        (100, 50, 50.0),
        (200, 25, 150.0),
        (99.99, 100, 0.0),
    ],
)
def test_calculate_discount_cases(price, percent, expected):
    """
    用一行 assert 验证 calculate_discount(price, percent) == expected。
    """
    assert calculate_discount(price, percent) == expected


# ============================================
# 练习 6：monkeypatch 替换外部依赖
# ============================================


def test_fetch_price(monkeypatch):
    """
    不要真的发 HTTP 请求。

    要求：
    1. 用 monkeypatch.setattr 把 httpx.get 换成假函数
       假函数返回 FakeResponse({"price": 19.9})
    2. 断言 fetch_price("A1") == 19.9
    3. 进阶：记录假函数收到的 url，断言
       它是 "https://api.example.com/price/A1"
    """
    calls = []

    def fake_get(url):
        calls.append(url)
        return FakeResponse({"price": 19.9})

    monkeypatch.setattr(httpx, "get", fake_get)
    assert fetch_price("A1") == 19.9
    assert calls == ["https://api.example.com/price/A1"]


# ============================================
# 练习 7：MagicMock 验证交互
# ============================================


def test_cache_miss_backfills():
    """
    用 unittest.mock.MagicMock() 造一个 fake cache，get 返回 None。

    调用 get_todo(fake_cache, 1) 后断言：
    1. 返回值是 {"id": 1, "title": "from db"}
    2. fake_cache.set 被调用了一次，参数是
       ("todo:1", {"id": 1, "title": "from db"})
    """
    fake_cache = MagicMock()
    fake_cache.get.return_value = None

    result = get_todo(fake_cache, 1)

    assert result == {"id": 1, "title": "from db"}
    fake_cache.set.assert_called_once_with("todo:1", {"id": 1, "title": "from db"})


def test_cache_hit_does_not_write():
    """
    fake cache 的 get 返回 {"id": 1, "title": "cached"}。

    调用后断言：
    1. 返回值是缓存的 dict
    2. fake_cache.set 一次都没被调用
    """
    fake_cache = MagicMock()
    fake_cache.get.return_value = {"id": 1, "title": "cached"}

    result = get_todo(fake_cache, 1)

    assert result == {"id": 1, "title": "cached"}
    fake_cache.set.assert_not_called()


# ============================================
# 练习 8：conftest.py 共享 fixture
# ============================================


def test_todo_payload_fixture(todo_payload):
    """
    先打开同目录的 conftest.py，把 todo_payload 的 TODO 实现掉。

    然后断言：
    - todo_payload["title"] == "buy milk"
    - todo_payload["done"] is False
    """
    assert todo_payload["title"] == "buy milk"
    assert todo_payload["done"] is False
