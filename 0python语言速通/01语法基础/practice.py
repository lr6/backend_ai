"""
第零阶段 · 0.1 语法基础 — 检验练习

每个函数的 TODO 需要你来实现。
写完后运行: python practice_0.1.py
全部通过 = 0.1 过关 ✅
"""


# ===== 练习 1：变量 + 字符串 =====
def greet(name, age):
    """返回 "Hello, 我叫{name}, 今年{age}岁" """
    # TODO: 用 f-string 实现
    return f"Hello, 我叫{name}, 今年{age}岁"


# ===== 练习 2：条件判断 =====
def check_age(age):
    """
    age < 13  → 返回 "child"
    13 <= age < 18 → 返回 "teen"
    age >= 18 → 返回 "adult"
    """
    # TODO: 用 if / elif / else 实现
    if  age < 13:
        return "child"
    elif age < 18:
        return "teen"
    else:
        return "adult"


# ===== 练习 3：循环 + 列表 =====
def filter_even(numbers):
    """
    过滤出列表中的所有偶数，返回新列表
    例如: [1, 2, 3, 4] → [2, 4]
    """
    # TODO: 用 for 循环实现（不要用列表推导式，先练基本功）
    arr = []
    for i in numbers:
        if i % 2 == 0:
            arr.append(i)
    return arr


# ===== 练习 4：字符串操作 =====
def count_word(text, word):
    """
    统计 word 在 text 中出现了多少次（用 in 判断即可）
    例如: ("hello world hello", "hello") → 2
    提示: 用 text.split() 把句子拆成单词列表
    """
    # TODO
    count = 0
    arr = text.split()
    for i in arr:
        if i == word:
            count += 1

    return count


# ===== 练习 5：列表切片 =====
def first_n(items, n):
    """
    返回列表的前 n 个元素
    例如: ([1,2,3,4,5], 3) → [1,2,3]
    要求: 用切片语法，一行代码
    """
    # TODO
    return items[0: n]


# ===== 练习 6：组合技 =====
def summarize(names):
    """
    输入一个名字列表，返回一个字符串：
    - 如果没有名字 → "no one"
    - 如果只有 1 个 → 直接返回那个名字
    - 如果有 2 个 → "A and B"
    - 如果有 3 个或更多 → "A, B, and N others"（N = 剩余人数）
    例如: ["zhio"] → "zhio"
          ["zhio", "bob"] → "zhio and bob"
          ["zhio", "bob", "alice"] → "zhio, bob, and 1 other"
          ["a", "b", "c", "d"] → "a, b, and 2 others"
    """
    # TODO: 用 if / elif / else + len() + f-string
    length = len(names)

    if length == 0:
        return "no one"
    elif length == 1:
        return f"{names[0]}"
    elif length == 2:
        return f"{names[0]} and {names[1]}"
    else:
        reset = length - 2
        if reset == 1:
            return f"{names[0]}, {names[1]}, and 1 other"
        else:
            return f"{names[0]}, {names[1]}, and {reset} others"



# ============================================
# 测试代码，不要修改下面内容
if __name__ == "__main__":
    errors = []

    # 测试 1
    result = greet("zhio", 25)
    expected = "Hello, 我叫zhio, 今年25岁"
    if result != expected:
        errors.append(f"❌ greet: 期望 '{expected}', 得到 '{result}'")
    else:
        print("✅ 练习1 (greet) 通过")

    # 测试 2
    for age, expected in [(10, "child"), (15, "teen"), (20, "adult"), (13, "teen"), (17, "teen"), (18, "adult")]:
        result = check_age(age)
        if result != expected:
            errors.append(f"❌ check_age({age}): 期望 '{expected}', 得到 '{result}'")
    if not any("check_age" in e for e in errors):
        print("✅ 练习2 (check_age) 通过")

    # 测试 3
    result = filter_even([1, 2, 3, 4, 5, 6])
    expected = [2, 4, 6]
    if result != expected:
        errors.append(f"❌ filter_even: 期望 {expected}, 得到 {result}")
    else:
        print("✅ 练习3 (filter_even) 通过")

    # 测试 4
    result = count_word("hello world hello", "hello")
    expected = 2
    if result != expected:
        errors.append(f"❌ count_word: 期望 {expected}, 得到 {result}")
    else:
        print("✅ 练习4 (count_word) 通过")

    # 测试 5
    result = first_n([1, 2, 3, 4, 5], 3)
    expected = [1, 2, 3]
    if result != expected:
        errors.append(f"❌ first_n: 期望 {expected}, 得到 {result}")
    else:
        print("✅ 练习5 (first_n) 通过")

    # 测试 6
    for names, expected in [
        ([], "no one"),
        (["zhio"], "zhio"),
        (["zhio", "bob"], "zhio and bob"),
        (["zhio", "bob", "alice"], "zhio, bob, and 1 other"),
        (["a", "b", "c", "d"], "a, b, and 2 others"),
    ]:
        result = summarize(names)
        if result != expected:
            errors.append(f"❌ summarize({names}): 期望 '{expected}', 得到 '{result}'")
    if not any("summarize" in e for e in errors):
        print("✅ 练习6 (summarize) 通过")

    # 总结
    print()
    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！0.1 语法基础 = ✅")
