"""
第四阶段 · 阶段项目 · Task 3 — tests/conftest.py

测试和开发环境必须互不打扰：
  数据库：eng_todo_test_db（不是 eng_todo_db）
  Redis ：db 14（不是 db 0）

⚠️ 为什么环境变量写在所有 import 之前？
   config.py 在「被 import 的那一刻」就执行 os.getenv，之后不会再读。
   所以必须在 import database / cache / main 之前把值设好 ——
   顺序反了，engine 和 redis client 就都指向开发环境了。
"""

import os
from uuid import uuid4

# setdefault：外部（比如 CI）已经设置就用外部的，本地没设才用默认值。
# 写成 os.environ[...] = ... 会把 CI 的 DATABASE_URL 强行盖成本机 socket，CI 必挂。
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg:///eng_todo_test_db")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/14")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import cache  # noqa: E402
import models  # noqa: E402,F401 —— import 一次让表注册到 Base.metadata
from database import Base, get_db  # noqa: E402
from main import app  # noqa: E402

TEST_DATABASE_URL = os.environ["DATABASE_URL"]

# ===== 测试库 engine（模块级只建一次）=====
test_engine = create_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(bind=test_engine)


def override_get_db():
    """database.get_db 的测试版：同一个结构，Session 绑到测试库。"""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    """整个测试会话开始前重建表，结束后拆掉（drop_all 顺带清数据）。"""
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture(autouse=True)
def clean_data():
    """
    每个测试开始前清空 todos 和 Redis，让测试之间互不依赖。

    为什么不清 users？
      session 级的 auth fixture 只注册一次用户、把 id 写进了 token。
      每个测试都清 users 的话，第二个测试开始时 token 里的用户已经不存在，
      所有需要登录的测试都会 401。user 行留着无害，会话结束 drop_all 一并清掉。
    """
    with test_engine.begin() as conn:
        conn.execute(text("TRUNCATE todos RESTART IDENTITY CASCADE"))
    cache.redis_client.flushdb()
    yield


@pytest.fixture
def client():
    """
    TestClient + 把 get_db 换成测试库版本。

    clear() 放 yield 之后：app 是全进程单例，不清理会污染后面的测试文件。
    """
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def db_session():
    """
    测试自己的数据库 Session：用来直接查库/改库，
    不经过 API —— 验证「命中缓存」时，就是靠绕过 API 改库、再看 API 还返回旧值。
    """
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ===== 认证 fixtures =====

def _register_and_login(username: str) -> dict:
    """
    注册 + 登录一个用户，返回测试要用的三样东西：
      headers  —— 直接塞进请求的 {"Authorization": "Bearer ..."}
      user_id  —— 断言 todo 归属用
      username

    为什么自己建 TestClient 而不用 client fixture？
      client 是 function scope，session scope 的 fixture 不能依赖它（ScopeMismatch）。
      这里用完就 pop 掉 override，不和 client fixture 抢。
    """
    app.dependency_overrides[get_db] = override_get_db
    try:
        c = TestClient(app)
        password = "pass12345"
        r = c.post("/auth/register", json={"username": username, "password": password})
        assert r.status_code == 201, f"注册失败: {r.status_code} {r.text}"
        user_id = r.json()["id"]

        r = c.post("/auth/login", data={"username": username, "password": password})
        assert r.status_code == 200, f"登录失败: {r.status_code} {r.text}"
        token = r.json()["access_token"]
    finally:
        app.dependency_overrides.pop(get_db, None)

    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "user_id": user_id,
        "username": username,
    }


@pytest.fixture(scope="session")
def auth(prepare_database):
    """主用户：整个测试会话只注册一次。"""
    return _register_and_login(f"alice_{uuid4().hex[:8]}")


@pytest.fixture(scope="session")
def other_auth(prepare_database):
    """第二个用户：专门用来测越权（IDOR）。"""
    return _register_and_login(f"bob_{uuid4().hex[:8]}")
