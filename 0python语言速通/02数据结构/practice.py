"""
第零阶段 · 0.2 数据结构 — 检验练习

每个函数的 TODO 需要你来实现。
写完后运行: python practice.py
全部通过 = 0.2 过关 ✅
"""


# ===== 练习 1：列表推导式 =====
def square_even_greater_than(nums, threshold):
    """
    从 nums 中筛选出 > threshold 的偶数，返回它们的平方列表
    例如: ([3, 7, 12, 5, 8, 10, 4], 6) → [144, 64, 100]
    提示: 一行列表推导式搞定
    """
    # TODO
    return [i**2 for i in nums if i > threshold and i % 2 == 0]


# ===== 练习 2：切片操作 =====
def extract_middle(items):
    """
    返回列表去掉头尾各一个元素后的中间部分
    例如: [1, 2, 3, 4, 5] → [2, 3, 4]
          ["a", "b", "c"] → ["b"]
    要求: 用切片语法，一行代码
    """
    # TODO
    return items[1:-1]
    


# ===== 练习 3：tuple 解包 =====
def min_max(nums):
    """
    返回列表中最小值和最大值的 tuple
    例如: [5, 2, 9, 1, 7] → (1, 9)
    提示: 用 min() 和 max() 内置函数
    """
    # TODO
    return (min(nums), max(nums))


# ===== 练习 4：字典推导式 =====
def build_cube_map(n):
    """
    返回 {1: 1的立方, 2: 2的立方, ..., n: n的立方}
    例如: n=3 → {1: 1, 2: 8, 3: 27}
    要求: 用字典推导式，一行代码
    """
    # TODO
    return {x: x**3 for x in range(1, n+1)}


# ===== 练习 5：统计字符频率 =====
def char_count(text):
    """
    统计字符串中每个字符出现的次数，返回字典
    例如: "hello" → {'h': 1, 'e': 1, 'l': 2, 'o': 1}
    提示: 遍历每个字符，用 dict.get(key, default) 累加
    """
    # TODO
    dd = {}
    for x in text:
        dd[x] = dd.get(x, 0) + 1
    return dd


# ===== 练习 6：set 集合运算 =====
def find_intersection(set_a, set_b):
    """
    返回两个集合的交集
    例如: ({1, 2, 3}, {2, 3, 4}) → {2, 3}
    要求: 用 & 运算符，一行代码
    """
    # TODO
    return set_a & set_b


# ===== 练习 7：购物车综合题 =====
def cart_total(cart):
    """
    cart 是一个列表，每个元素是 {"price": int, "quantity": int}
    返回总价（price * quantity 的累加）
    例如: [{"price": 99, "quantity": 2}, {"price": 299, "quantity": 1}] → 497
    提示: 用 sum() + 生成器表达式，或 for 循环累加
    """
    # TODO
    return sum(item['price'] * item['quantity'] for item in cart)

# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    errors = []

    # 测试 1
    nums = [3, 7, 12, 5, 8, 10, 4]
    result = square_even_greater_than(nums, 6)
    expected = [144, 64, 100]
    if result != expected:
        errors.append(f"❌ square_even_greater_than: 期望 {expected}, 得到 {result}")
    else:
        print("✅ 练习1 (列表推导式) 通过")

    # 测试 2
    for items, expected in [
        ([1, 2, 3, 4, 5], [2, 3, 4]),
        (["a", "b", "c"], ["b"]),
    ]:
        result = extract_middle(items)
        if result != expected:
            errors.append(f"❌ extract_middle({items}): 期望 {expected}, 得到 {result}")
    if not any("extract_middle" in e for e in errors):
        print("✅ 练习2 (切片) 通过")

    # 测试 3
    result = min_max([5, 2, 9, 1, 7])
    expected = (1, 9)
    if result != expected:
        errors.append(f"❌ min_max: 期望 {expected}, 得到 {result}")
    else:
        print("✅ 练习3 (tuple解包) 通过")

    # 测试 4
    result = build_cube_map(3)
    expected = {1: 1, 2: 8, 3: 27}
    if result != expected:
        errors.append(f"❌ build_cube_map: 期望 {expected}, 得到 {result}")
    else:
        print("✅ 练习4 (字典推导式) 通过")

    # 测试 5
    result = char_count("hello")
    expected = {'h': 1, 'e': 1, 'l': 2, 'o': 1}
    if result != expected:
        errors.append(f"❌ char_count: 期望 {expected}, 得到 {result}")
    else:
        print("✅ 练习5 (字符统计) 通过")

    # 测试 6
    result = find_intersection({1, 2, 3}, {2, 3, 4})
    expected = {2, 3}
    if result != expected:
        errors.append(f"❌ find_intersection: 期望 {expected}, 得到 {result}")
    else:
        print("✅ 练习6 (set交集) 通过")

    # 测试 7
    cart = [
        {"price": 99, "quantity": 2},
        {"price": 299, "quantity": 1},
        {"price": 1299, "quantity": 1},
        {"price": 29, "quantity": 3},
    ]
    result = cart_total(cart)
    expected = 1883
    if result != expected:
        errors.append(f"❌ cart_total: 期望 {expected}, 得到 {result}")
    else:
        print("✅ 练习7 (购物车统计) 通过")

    # 总结
    print()
    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！0.2 数据结构 = ✅")
