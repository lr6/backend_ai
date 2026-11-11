"""
第三阶段 · 阶段项目 · Task 3 — schemas.py
Pydantic 请求 / 响应模型

和第二阶段相比，三个变化：
  1. UserCreate 多一个 password（收明文，路由里立刻哈希）
  2. 新增 TokenPair / RefreshRequest（登录、刷新的响应和请求）
  3. TodoCreate 删掉 user_id（身份从 token 来，不信客户端）

写完后运行: ../../.venv/bin/python schemas.py
全部通过 = Task 3 过关 ✅
"""

from pydantic import BaseModel, ConfigDict, Field


# ===== UserCreate（注册请求）=====
class UserCreate(BaseModel):
    """
    注册时客户端传的字段。

    username: str，必填，长度 1~50
    email:    str | None，默认 None
    password: str，必填

    TODO 1：给 password 加约束 Field(min_length=8, max_length=72)
      为什么上限是 72 而不是 128？想想 bcrypt 的处理上限。
      为什么下限是 8？太短的密码在离线爆破面前等于没有。
    """
    username: str = Field(min_length=1, max_length=50)
    email: str | None = None
    password: str = Field(min_length=8, max_length=72)


# ===== UserRead（用户响应）=====
class UserRead(BaseModel):
    """
    返回给客户端的用户信息（已给好）。

    注意：这里【没有】password_hash —— 响应模型就是白名单。
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str | None


# ===== TokenPair（登录 / 刷新响应）=====
class TokenPair(BaseModel):
    """
    登录成功返回的双 token。

    access_token:  str
    refresh_token: str
    token_type:    str，默认 "bearer"（小写，OAuth2 约定）
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ===== RefreshRequest（刷新请求）=====
class RefreshRequest(BaseModel):
    """
    换新 access token 时，客户端用 JSON 传 refresh token。

    refresh_token: str
    """
    refresh_token: str


# ===== TodoCreate（创建请求）=====
class TodoCreate(BaseModel):
    """
    创建 todo 时客户端传的字段。

    TODO 2：只保留 title（必填，长度 1~200）。
      —— 不要 user_id！它由后端从 token 里取。
    """
    # TODO 2: title 写在下面
    title: str = Field(min_length=1, max_length=200)


# ===== TodoRead（Todo 响应，已给好）=====
class TodoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    done: bool
    user_id: int


# ===== TodoUpdate（PATCH，已给好）=====
class TodoUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None


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
    def t_user_create_ok():
        u = UserCreate(username="alice", password="12345678")
        assert u.username == "alice"
        assert u.password == "12345678", f"password 期望 '12345678'，实际 {u.password!r}"
        assert u.email is None

    def t_password_required():
        try:
            UserCreate(username="alice")
        except ValidationError:
            return
        raise AssertionError("缺 password 应该抛 ValidationError")

    def t_password_too_short():
        try:
            UserCreate(username="alice", password="1234567")
        except ValidationError:
            return
        raise AssertionError("7 位密码应该被拒绝（min_length=8）")

    def t_password_too_long():
        try:
            UserCreate(username="alice", password="a" * 73)
        except ValidationError:
            return
        raise AssertionError("73 字节密码应该被拒绝（max_length=72，bcrypt 上限）")

    # ---------- UserRead ----------
    def t_user_read_safe():
        fields = set(UserRead.model_fields)
        assert "password_hash" not in fields, f"UserRead 泄露了 password_hash！字段: {fields}"
        assert "password" not in fields, f"UserRead 不应包含 password！字段: {fields}"
        obj = SimpleNamespace(id=1, username="alice", email=None)
        u = UserRead.model_validate(obj)
        assert (u.id, u.username) == (1, "alice")

    # ---------- TokenPair ----------
    def t_token_pair():
        t = TokenPair(access_token="a", refresh_token="r")
        assert t.token_type == "bearer", f"token_type 默认应为 'bearer'，实际 {t.token_type!r}"
        assert t.access_token == "a" and t.refresh_token == "r"

    # ---------- RefreshRequest ----------
    def t_refresh_request_required():
        try:
            RefreshRequest()
        except ValidationError:
            return
        raise AssertionError("缺 refresh_token 应该抛 ValidationError")

    # ---------- TodoCreate ----------
    def t_todo_create_no_user_id():
        fields = set(TodoCreate.model_fields)
        assert "user_id" not in fields, f"TodoCreate 不应该有 user_id（由 token 推导）！字段: {fields}"
        t = TodoCreate(title="买牛奶")
        assert t.title == "买牛奶"

    def t_todo_create_title_required():
        try:
            TodoCreate()
        except ValidationError:
            return
        raise AssertionError("缺 title 应该抛 ValidationError")

    def t_todo_create_title_length():
        try:
            TodoCreate(title="")
        except ValidationError:
            return
        raise AssertionError("空 title 应该被拒绝（min_length=1）")

    # ---------- TodoRead / TodoUpdate ----------
    def t_todo_read():
        obj = SimpleNamespace(id=3, title="买牛奶", done=False, user_id=1)
        t = TodoRead.model_validate(obj)
        assert (t.id, t.title, t.done, t.user_id) == (3, "买牛奶", False, 1)

    def t_todo_update():
        a = TodoUpdate()
        assert a.title is None and a.done is None
        b = TodoUpdate(done=False)
        assert b.done is False and b.title is None

    check("UserCreate 基本字段（含 password）", t_user_create_ok)
    check("UserCreate 缺 password 报错", t_password_required)
    check("password 少于 8 位报错", t_password_too_short)
    check("password 超过 72 报错", t_password_too_long)
    check("UserRead 不泄露密码字段", t_user_read_safe)
    check("TokenPair 默认 token_type=bearer", t_token_pair)
    check("RefreshRequest 缺 refresh_token 报错", t_refresh_request_required)
    check("TodoCreate 没有 user_id", t_todo_create_no_user_id)
    check("TodoCreate 缺 title 报错", t_todo_create_title_required)
    check("TodoCreate 空 title 报错", t_todo_create_title_length)
    check("TodoRead from_attributes", t_todo_read)
    check("TodoUpdate 全部可选", t_todo_update)

    print()
    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！Task 3 schemas.py = ✅")
