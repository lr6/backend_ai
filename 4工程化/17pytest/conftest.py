"""
练习 8 专用：定义在 conftest.py 里的 fixture，practice.py 不用 import 就能用。
"""

import pytest


@pytest.fixture
def todo_payload():
    """
    返回一个示例 Todo 字典：{"title": "buy milk", "done": False}
    """
    return {"title": "buy milk", "done": False}
