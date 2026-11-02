"""
第二阶段 · 阶段项目 · Task 4A — schemas.py
Pydantic 请求 / 响应模型

请求模型（In） : 客户端传进来的数据 → 校验
响应模型（Out）: 返回给客户端的数据   → 过滤 + 序列化

写完后运行: .venv/bin/python schemas.py
全部通过 = Task 4A 过关 ✅
"""

from pydantic import BaseModel, ConfigDict, Field


# ===== UserCreate（请求模型）=====
class UserCreate(BaseModel):
    """
    注册用户时客户端传的字段。

    username: str，必填，长度 1~50（用 Field(min_length=1, max_length=50)）
    email:    str | None，默认 None

    注意：不要有 id。
    """
    username: str = Field(min_length=1, max_length=50)
    email: str | None = None


# ===== UserRead（响应模型）=====
class UserRead(BaseModel):
    """
    返回给客户端的用户信息。

    id:       int
    username: str
    email:    str | None

    关键：要能从 SQLAlchemy 对象读取属性 → 加
        model_config = ConfigDict(from_attributes=True)
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str | None


# ===== TodoCreate（请求模型）=====
class TodoCreate(BaseModel):
    """
    创建 todo 时客户端传的字段。

    title:   str，必填，长度 1~200
    user_id: int，必填（这条 todo 属于谁）
    """
    title: str = Field(min_length=1, max_length=200)
    user_id: int


# ===== TodoRead（响应模型）=====
class TodoRead(BaseModel):
    """
    返回给客户端的 todo。

    id:      int
    title:   str
    done:    bool
    user_id: int

    同样要加 from_attributes=True。
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    done: bool
    user_id: int


# ===== TodoUpdate（请求模型，PATCH 用）=====
class TodoUpdate(BaseModel):
    """
    部分更新：所有字段都可选，默认 None。

    title: str | None = None
    done:  bool | None = None

    PATCH 的语义：只改客户端传了的字段，没传的保持原样。
    """

    title: str | None = None
    done:  bool | None = None


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    from types import SimpleNamespace

    from pydantic import ValidationError

    errors = []

    def check(name, fn):
        try:
            fn()
            print(f"✅ {name}")
        except AssertionError as e:
            errors.append(f"{name}: {e}")
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}: {e}")

    # ---------- UserCreate ----------
    def test_user_create_basic():
        u = UserCreate(username="alice", email="a@example.com")
        assert u.username == "alice", f"username 期望 alice，实际 {u.username!r}"
        assert u.email == "a@example.com"
        u2 = UserCreate(username="bob")
        assert u2.email is None, f"email 不传时默认应为 None，实际 {u2.email!r}"

    def test_user_create_requires_username():
        try:
            UserCreate(email="x@y.com")
        except ValidationError:
            return
        raise AssertionError("缺 username 应该抛 ValidationError")

    def test_user_create_username_length():
        try:
            UserCreate(username="a" * 51)
        except ValidationError:
            return
        raise AssertionError("username 超过 50 字符应该抛 ValidationError")

    # ---------- UserRead ----------
    def test_user_read_from_object():
        obj = SimpleNamespace(id=1, username="alice", email=None)
        u = UserRead.model_validate(obj)
        assert u.id == 1, f"id 期望 1，实际 {u.id!r}"
        assert u.username == "alice"
        assert u.email is None

    # ---------- TodoCreate ----------
    def test_todo_create():
        t = TodoCreate(title="买牛奶", user_id=1)
        assert t.title == "买牛奶"
        assert t.user_id == 1

    def test_todo_create_requires_user_id():
        try:
            TodoCreate(title="买牛奶")
        except ValidationError:
            return
        raise AssertionError("缺 user_id 应该抛 ValidationError")

    # ---------- TodoRead ----------
    def test_todo_read_from_object():
        obj = SimpleNamespace(id=3, title="买牛奶", done=False, user_id=1)
        t = TodoRead.model_validate(obj)
        assert (t.id, t.title, t.done, t.user_id) == (3, "买牛奶", False, 1), (
            f"实际 {t.id!r}, {t.title!r}, {t.done!r}, {t.user_id!r}"
        )

    # ---------- TodoUpdate ----------
    def test_todo_update_all_optional():
        a = TodoUpdate()
        assert a.title is None and a.done is None, "不传字段时都应为 None"
        b = TodoUpdate(done=True)
        assert b.done is True, f"done 期望 True，实际 {b.done!r}"
        assert b.title is None, "只传 done 时 title 应为 None"

    check("UserCreate 基本字段 + email 默认 None", test_user_create_basic)
    check("UserCreate 缺 username 报错", test_user_create_requires_username)
    check("UserCreate username 长度上限 50", test_user_create_username_length)
    check("UserRead 能从对象读取（from_attributes）", test_user_read_from_object)
    check("TodoCreate 基本字段", test_todo_create)
    check("TodoCreate 缺 user_id 报错", test_todo_create_requires_user_id)
    check("TodoRead 能从对象读取（from_attributes）", test_todo_read_from_object)
    check("TodoUpdate 全部可选", test_todo_update_all_optional)

    print()
    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！Task 4A schemas.py = ✅")
