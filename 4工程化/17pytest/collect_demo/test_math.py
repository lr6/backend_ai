"""pytest 收集规则演示：pytest 到底会运行哪些函数？"""


def add(a, b):
    return a + b


def test_add_positive():
    assert add(1, 2) == 3


def test_add_negative():
    assert add(-1, -2) == -3


def helper_check():  # 不是 test_ 开头
    assert add(0, 0) == 1
