"""
第零阶段 · 0.3 类型提示 — 检验练习

每个函数的 TODO 需要你来实现。
写完后运行: python practice.py
全部通过 = 0.3 过关 ✅

提示：类型标注运行时不检查，所以测试只看函数的实际行为。
但你要确保给每个函数参数和返回值都加上正确的类型标注！
"""

from typing import Callable, TypedDict

# ===== 练习 1：基本类型标注 =====
def describe_person(name: str, age: int, height: float, is_student: bool) -> str:
    """
    返回对人的描述字符串。
    给所有参数和返回值加上正确的类型标注（已经写好了，参考这个格式）。

    例如: describe_person("小明", 18, 1.75, True)
         → "小明，18岁，身高1.75米，学生"
    例如: describe_person("小红", 25, 1.62, False)
         → "小红，25岁，身高1.62米，非学生"
    """
    # TODO: 实现函数体
    status = "学生" if is_student else "非学生"
    return f"{name}，{age}岁，身高{height}米，{status}"


# ===== 练习 2：Optional / Union — 处理"可能没有"的情况 =====
def get_user_email(users: dict[str, str], username: str) -> str | None:
    """
    从 users 字典中查找用户的邮箱。
    如果用户存在，返回邮箱；否则返回 None。

    例如: get_user_email({"zhio": "zhio@dev.com"}, "zhio") → "zhio@dev.com"
    例如: get_user_email({"zhio": "zhio@dev.com"}, "nobody") → None
    """
    # TODO: 实现函数体
    return users.get(username)


# ===== 练习 3：容器类型 — list、dict、tuple =====
def analyze_scores(scores: list[int]) -> dict[str, float]:
    """
    分析分数列表，返回统计字典：
    {"average": 平均分, "highest": 最高分, "lowest": 最低分}。
    如果列表为空，所有值返回 0.0。

    例如: analyze_scores([80, 90, 100])
         → {"average": 90.0, "highest": 100.0, "lowest": 80.0}
    例如: analyze_scores([])
         → {"average": 0.0, "highest": 0.0, "lowest": 0.0}
    """
    # TODO: 实现函数体
    if not scores:
        return {"average": 0.0, "highest": 0.0, "lowest": 0.0}
    length = len(scores)
    dd = {}
    dd['lowest'] = float(min(scores))
    dd['highest'] = float(max(scores))
    dd['average'] = sum(scores) / length
    return dd


# ===== 练习 4：类型别名 =====
# 定义类型别名
UserID = int
UserInfo = dict[str, str | int | None]

# 模拟数据库
FAKE_DB: dict[UserID, UserInfo] = {
    1: {"name": "zhio", "role": "admin", "email": "zhio@dev.com"},
    2: {"name": "小明", "role": "user", "email": None},
    3: {"name": "小红", "role": "user", "email": "xiaohong@dev.com"},
}

def find_user_by_id(uid: UserID) -> UserInfo | None:
    """
    根据用户 ID 查找用户。
    使用类型别名 UserID 和 UserInfo。

    例如: find_user_by_id(1) → {"name": "zhio", "role": "admin", "email": "zhio@dev.com"}
    例如: find_user_by_id(999) → None
    """
    # TODO: 实现函数体
    return FAKE_DB.get(uid)


# ===== 练习 5：TypedDict — 给字典结构加类型 =====
class TodoItem(TypedDict):
    title: str
    done: bool
    priority: int  # 1=高, 2=中, 3=低

def format_todo(item: TodoItem) -> str:
    """
    将 TodoItem 格式化为字符串。
    用 ✅ 表示 done=True，⬜ 表示 done=False。
    用星号数量表示优先级：1→★★★, 2→★★, 3→★

    例如: format_todo({"title": "学Python", "done": True, "priority": 1})
         → "✅ 学Python ★★★"
    例如: format_todo({"title": "学Docker", "done": False, "priority": 3})
         → "⬜ 学Docker ★"
    """
    # TODO: 实现函数体
    title = item.get('title')
    status = '✅' if item.get('done') else '⬜'
    star = item.get('priority')
    if star == 1:
        star = '★★★'
    elif star == 2:
        star = '★★'
    else:
        star =  '★'
    return f"{status} {title} {star}"



# ===== 练习 6：Callable — 函数作为参数 =====
def filter_by(
    items: list[int],
    condition: Callable[[int], bool]
) -> list[int]:
    """
    根据 condition 函数过滤列表。
    condition 是一个函数，接收一个 int，返回 bool。

    例如:
        is_even = lambda x: x % 2 == 0
        filter_by([1, 2, 3, 4, 5], is_even) → [2, 4]

    例如:
        is_positive = lambda x: x > 0
        filter_by([-1, 0, 3, -5, 6], is_positive) → [3, 6]
    """
    # TODO: 实现函数体
    return [x for x in items if condition(x)]


# ===== 练习 7：综合 — 把所有知识组合起来 =====
class Student(TypedDict):
    name: str
    scores: list[int]  # 各科成绩

GradeReport = dict[str, str | float | bool]  # 类型别名

def generate_report(student: Student) -> GradeReport | None:
    """
    为学生生成成绩报告。
    如果 scores 为空，返回 None。
    否则返回:
    {
        "name": 名字,
        "average": 平均分,
        "passed": 均分>=60,
        "grade": "A"(>=90), "B"(>=80), "C"(>=70), "D"(>=60), "F"(<60)
    }

    例如: generate_report({"name": "zhio", "scores": [95, 88, 92]})
         → {"name": "zhio", "average": 91.67, "passed": True, "grade": "A"}
    例如: generate_report({"name": "小明", "scores": []})
         → None
    """
    # TODO: 实现函数体
    name = student.get('name')
    scores = student.get('scores')
    if not scores:
        return None
    average = round(sum(scores) / len(scores), 2)
    passed = True if average >= 60 else False
    grade = ''
    if average < 60:
        grade = 'F'
    elif average < 70:
        grade = 'D'
    elif average < 80:
        grade = 'C'
    elif average < 90:
        grade = 'B'
    else:
        grade = 'A'

    return {"name": name, "average": average, "passed": passed, "grade": grade}


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    errors = []

    # --- 练习 1 ---
    r1_1 = describe_person("小明", 18, 1.75, True)
    if r1_1 != "小明，18岁，身高1.75米，学生":
        errors.append(f"练习1-1: 期望 '小明，18岁，身高1.75米，学生'，实际 '{r1_1}'")

    r1_2 = describe_person("小红", 25, 1.62, False)
    if r1_2 != "小红，25岁，身高1.62米，非学生":
        errors.append(f"练习1-2: 期望 '小红，25岁，身高1.62米，非学生'，实际 '{r1_2}'")

    # --- 练习 2 ---
    test_users = {"zhio": "zhio@dev.com", "test": "test@dev.com"}
    r2_1 = get_user_email(test_users, "zhio")
    if r2_1 != "zhio@dev.com":
        errors.append(f"练习2-1: 期望 'zhio@dev.com'，实际 '{r2_1}'")

    r2_2 = get_user_email(test_users, "nobody")
    if r2_2 is not None:
        errors.append(f"练习2-2: 期望 None，实际 '{r2_2}'")

    # --- 练习 3 ---
    r3_1 = analyze_scores([80, 90, 100])
    expected_3_1 = {"average": 90.0, "highest": 100.0, "lowest": 80.0}
    if r3_1 != expected_3_1:
        errors.append(f"练习3-1: 期望 {expected_3_1}，实际 {r3_1}")

    r3_2 = analyze_scores([])
    expected_3_2 = {"average": 0.0, "highest": 0.0, "lowest": 0.0}
    if r3_2 != expected_3_2:
        errors.append(f"练习3-2: 期望 {expected_3_2}，实际 {r3_2}")

    # --- 练习 4 ---
    r4_1 = find_user_by_id(1)
    expected_4_1 = {"name": "zhio", "role": "admin", "email": "zhio@dev.com"}
    if r4_1 != expected_4_1:
        errors.append(f"练习4-1: 期望 {expected_4_1}，实际 {r4_1}")

    r4_2 = find_user_by_id(999)
    if r4_2 is not None:
        errors.append(f"练习4-2: 期望 None，实际 '{r4_2}'")

    r4_3 = find_user_by_id(2)
    if r4_3 is None or r4_3.get("email") is not None:
        errors.append(f"练习4-3: 期望 email 为 None，实际 '{r4_3}'")

    # --- 练习 5 ---
    r5_1 = format_todo({"title": "学Python", "done": True, "priority": 1})
    if r5_1 != "✅ 学Python ★★★":
        errors.append(f"练习5-1: 期望 '✅ 学Python ★★★'，实际 '{r5_1}'")

    r5_2 = format_todo({"title": "学Docker", "done": False, "priority": 3})
    if r5_2 != "⬜ 学Docker ★":
        errors.append(f"练习5-2: 期望 '⬜ 学Docker ★'，实际 '{r5_2}'")

    r5_3 = format_todo({"title": "写测试", "done": True, "priority": 2})
    if r5_3 != "✅ 写测试 ★★":
        errors.append(f"练习5-3: 期望 '✅ 写测试 ★★'，实际 '{r5_3}'")

    # --- 练习 6 ---
    is_even = lambda x: x % 2 == 0
    r6_1 = filter_by([1, 2, 3, 4, 5], is_even)
    if r6_1 != [2, 4]:
        errors.append(f"练习6-1: 期望 [2, 4]，实际 {r6_1}")

    is_positive = lambda x: x > 0
    r6_2 = filter_by([-1, 0, 3, -5, 6], is_positive)
    if r6_2 != [3, 6]:
        errors.append(f"练习6-2: 期望 [3, 6]，实际 {r6_2}")

    r6_3 = filter_by([], is_even)
    if r6_3 != []:
        errors.append(f"练习6-3: 期望 []，实际 {r6_3}")

    # --- 练习 7 ---
    r7_1 = generate_report({"name": "zhio", "scores": [95, 88, 92]})
    expected_7_1 = {"name": "zhio", "average": 91.67, "passed": True, "grade": "A"}
    if r7_1 != expected_7_1:
        errors.append(f"练习7-1: 期望 {expected_7_1}，实际 {r7_1}")

    r7_2 = generate_report({"name": "小明", "scores": [60, 62, 58]})
    if r7_2 is None:
        errors.append(f"练习7-2: 期望非 None 报告，实际 None")
    elif r7_2["grade"] != "D":
        errors.append(f"练习7-2: grade 期望 'D'，实际 '{r7_2['grade']}'")

    r7_3 = generate_report({"name": "小红", "scores": []})
    if r7_3 is not None:
        errors.append(f"练习7-3: 期望 None，实际 {r7_3}")

    r7_4 = generate_report({"name": "test", "scores": [40, 50]})
    if r7_4 is None:
        errors.append(f"练习7-4: 期望非 None 报告，实际 None")
    elif r7_4["grade"] != "F":
        errors.append(f"练习7-4: grade 期望 'F'，实际 '{r7_4['grade']}'")

    # --- 结果 ---
    if errors:
        print(f"❌ 有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！0.3 类型提示 = ✅")
