"""
第四阶段 · 18 httpx + pytest — 共享 fixture（需要你补全）

这两个 fixture 是所有 API 测试的基础。
"""

import pytest
from fastapi.testclient import TestClient

from app import Store, app, get_store


# ===== 练习 1：每个测试一套干净数据 =====
@pytest.fixture
def store():
    """
    返回一个新的 Store 实例。
    """
    return Store()

# ===== 练习 2：client + 依赖覆盖 =====
@pytest.fixture
def client(store):
    """
    1. 用 app.dependency_overrides 把 get_store 覆盖成「返回 store」的函数
    2. 创建 TestClient(app)
    3. yield 给测试使用
    4. 测试结束后清理 app.dependency_overrides
    """
    app.dependency_overrides[get_store] = lambda: store
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
