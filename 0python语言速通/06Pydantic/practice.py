"""
第零阶段 · 0.6 Pydantic — 检验练习

每个 TODO 需要你来实现。
写完后运行: python practice.py
全部通过 = 0.6 Pydantic ✅

提示（前端对照）：
  - class X(BaseModel)  ~  TypeScript interface + Zod（运行时校验）
  - Field(gt=0)         ~  Zod 的 .positive() 之类
  - model_dump()        ~  转 dict（序列化）
  - model_validate()    ~  从 dict 构建模型
  - ValidationError     ~  校验失败抛的异常
"""

from pydantic import BaseModel, Field, ValidationError


# ===== 练习 1：定义 User 模型 =====
class User(BaseModel):
    """
    用户模型。定义两个字段：
      - name: str
      - age: int
    """
    # TODO: 写两个字段
    name: str
    age: int


# ===== 练习 2：运行时校验 =====
def validate_age(age) -> bool:
    """
    尝试 User(name="x", age=age)：
      - 如果抛 ValidationError，返回 False
      - 否则返回 True

    例如: validate_age(30) -> True
          validate_age("abc") -> False
    """
    # TODO
    try:
        User(name="x", age=age)
        return True
    except ValidationError:
        return False


# ===== 练习 3：自动类型转换（coercion）=====
def coerced_age_type() -> type:
    """
    User(name="x", age="25") 里，age 传了字符串 "25"。
    Pydantic 会自动转成 int。返回 user.age 的类型（应该是 int）。

    例如: coerced_age_type() -> int
    """
    # TODO
    user = User(name="x", age="25")
    return type(user.age)


# ===== 练习 4：默认值 =====
class Article(BaseModel):
    """
    文章模型。定义两个字段：
      - title: str
      - views: int = 0   （默认值 0）
    """
    # TODO
    title: str
    views: int = 0


def default_views() -> int:
    """
    创建 Article(title="hello")（不传 views），返回 article.views。
    例如: default_views() -> 0
    """
    # TODO
    article = Article(title="hello")
    return article.views


# ===== 练习 5：Field 约束 =====
class Product(BaseModel):
    """
    商品模型。定义两个字段：
      - name: str
      - price: float = Field(gt=0)   （必须大于 0）
    """
    # TODO
    name: str
    price: float = Field(gt=0)


def negative_price_raises() -> bool:
    """
    尝试 Product(name="x", price=-5)，应抛 ValidationError。
    如果确实抛了，返回 True；否则 False。

    例如: negative_price_raises() -> True
    """
    # TODO
    try:
        Product(name='x', price=-5)
        return False
    except ValidationError:
        return True


# ===== 练习 6：序列化 model_dump =====
def dump_user() -> dict:
    """
    创建 User(name="Dave", age=28)，用 .model_dump() 转成 dict 并返回。
    例如: dump_user() -> {"name": "Dave", "age": 28}
    """
    # TODO
    user = User(name="Dave", age=28)
    return user.model_dump()


# ===== 练习 7：嵌套模型 =====
class Order(BaseModel):
    """
    订单模型。定义两个字段：
      - id: int
      - user: User   （嵌套另一个模型）
    """
    # TODO
    id: int
    user: User


def order_user_name() -> str:
    """
    创建 Order(id=1, user={"name": "Eve", "age": 22})（user 直接传 dict，
    Pydantic 会自动转成 User），返回 order.user.name。

    例如: order_user_name() -> "Eve"
    """
    # TODO
    order = Order(id=1, user={"name": 'Eve', "age": 29})
    return order.user.name


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    errors = []

    def check(name, actual, expected):
        if actual != expected:
            errors.append(f"{name}: 期望 {expected}，实际 {actual}")
        else:
            print(f"✅ {name}")

    # 练习 1
    try:
        u = User(name="Alice", age=30)
        check("练习1 User.name", u.name, "Alice")
        check("练习1 User.age", u.age, 30)
    except Exception as e:
        errors.append(f"练习1: User 模型定义有误 - {type(e).__name__}: {e}")

    # 练习 2
    check("练习2 校验合法", validate_age(30), True)
    check("练习2 校验非法", validate_age("abc"), False)

    # 练习 3
    check("练习3 类型转换", coerced_age_type(), int)

    # 练习 4
    check("练习4 默认值", default_views(), 0)

    # 练习 5
    check("练习5 Field约束", negative_price_raises(), True)

    # 练习 6
    check("练习6 序列化", dump_user(), {"name": "Dave", "age": 28})

    # 练习 7
    check("练习7 嵌套模型", order_user_name(), "Eve")

    if errors:
        print(f"\n有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("\n🎉 全部通过！0.6 Pydantic = ✅")
