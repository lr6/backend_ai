"""
第二阶段 · 9 Normalization — 范式化与反范式化 检验练习

每个函数的 TODO 需要你来实现。
写完后运行: python practice.py
全部通过 = 9 Normalization 过关 ✅

背景速记（讲课时推导出来的结论）：
- 范式化 = 拆表消除冗余，让每份数据只有一个「家」；代价是读要 JOIN
- 1NF  一格只装一个值（原子）
- 2NF  非主键列不能只依赖复合主键的「一部分」（部分依赖）
- 3NF  非主键列不能隔着一个外键拐弯依赖（传递依赖）
- 口诀: 每个非主键列，都要「直接、完整」地依赖主键
       （直接 = 3NF，完整 = 2NF）
- 反范式化 = 故意存回冗余，用「写的一致性」换「读的快」，本质是缓存
"""

# ===== 练习 1：1NF 违规检测 =====
def find_1nf_violations(rows):
    """
    检测哪些列违反 1NF（一格里塞了多个值）。

    判断规则：某列只要出现一个值满足以下任一情况，就视为违规：
      - 值是 list / tuple（本身就是一堆东西塞一个格）
      - 值是字符串且包含逗号 ","（多个值拼在了一个字符串里）

    输入: rows 是 list[dict]，每个 dict 代表一行（列名 -> 值）
    输出: list[str]，违规列名列表（无违规返回 []）

    例如:
      rows = [{"order_id": 1, "product": "键盘,鼠标"},
              {"order_id": 2, "product": "耳机"}]
      调用  ->  ["product"]
    """
    # TODO: 遍历每一列，检查该列的值是否违反 1NF
    # 提示：先拿到所有列名（所有行的 key 的并集），再逐列判断
    bad_cols = set()
    for row in rows:
        for col, v in row.items():
            if isinstance(v, (list, tuple)) or (isinstance(v, str) and ',' in v):
                bad_cols.add(col)

    return list(bad_cols)

# ===== 练习 2：2NF 部分依赖检测 =====
def find_partial_dependency(pk, deps):
    """
    检测哪些非主键列存在「部分依赖」（只依赖复合主键的一部分）。

    输入:
      pk   : list[str]，主键包含哪些列（复合主键时 > 1 个元素）
      deps : dict[str, list[str]]，非主键列名 -> 决定它的列名列表
             （即「这一列的值，由哪些列决定」）

    判断规则：一个非主键列，如果它的决定列集合，是主键集合的
              「真子集」（⊂），就说明它只依赖主键的一部分 -> 部分依赖。

    输出: list[str]，有部分依赖的列名列表（无则返回 []）

    例如:
      pk   = ["order_id", "product_name"]
      deps = {"product_price": ["product_name"],          # 只依赖一半 -> 违规
              "qty": ["order_id", "product_name"]}         # 依赖整个主键 -> 没问题
      调用  ->  ["product_price"]
    """
    # TODO: 遍历 deps，用 set 判断决定列是否为 pk 的真子集
    # 提示: set(dep) < set(pk)  是真子集判断
    violations = set()
    pk_set = set(pk)
    for col, dep in deps.items():
        if pk_set > set(dep):
            violations.add(col)
    return list(violations)

# ===== 练习 3：3NF 传递依赖检测 =====
def find_transitive_dependency(pk, deps):
    """
    检测哪些非主键列存在「传递依赖」（隔着一个外键拐弯决定）。

    输入:
      pk   : list[str]，主键包含哪些列
      deps : dict[str, list[str]]，非主键列名 -> 决定它的列名列表

    判断规则：一个非主键列的决定列里，只要包含「不属于主键」的列
              （比如外键 user_id 或别的普通列），说明它不是直接由
              主键决定，而是传递过来的 -> 传递依赖。

    输出: list[str]，有传递依赖的列名列表（无则返回 []）

    例如:
      pk   = ["order_id"]
      deps = {"user_city": ["user_id"],      # user_id 不是主键 -> 违规
              "created_at": ["order_id"]}     # 直接依赖主键 -> 没问题
      调用  ->  ["user_city"]
    """
    # TODO: 遍历 deps，检查决定列里是否有不属于 pk 的列
    # 提示: for d in dep:  if d not in pk: ...
    violations = []
    for col, dep in deps.items():
        for d in dep:
            if d not in pk:
                violations.append(col)
    return violations


# ===== 练习 4：综合 —— 最高满足第几范式 =====
def highest_normal_form(pk, deps):
    """
    判断一张表最高满足到第几范式。

    输入同上（pk + deps）。
    输出: 字符串，只能是 "1NF" / "2NF" / "3NF" 之一。

    判断顺序（从低到高排除）：
      - 存在部分依赖  -> 连 2NF 都不满足，返回 "1NF"
      - 否则存在传递依赖 -> 连 3NF 都不满足，返回 "2NF"
      - 都没有          -> "3NF"

    例如:
      pk=["order_id"]  deps={"user_city": ["user_id"]}      -> "2NF"  (传递依赖)
      pk=["order_id","product_name"]
                       deps={"qty": ["order_id","product_name"]} -> "3NF"  (都满足)
      pk=["order_id","product_name"]
                       deps={"product_price": ["product_name"]} -> "1NF"  (部分依赖)
    """
    # TODO: 复用练习 2、3 的判断逻辑（也可独立实现）
    # 提示: 先判部分依赖，再判传递依赖
    if find_partial_dependency(pk, deps):
        return '1NF'
    if find_transitive_dependency(pk, deps):
        return '2NF'
    return '3NF'


# ===== 练习 5：反范式化决策 =====
def denormalize_advice(scenario):
    """
    根据读写特征，判断应该「规范化」还是「反范式化」。

    输入: scenario dict，含三个键:
      - "read_per_sec" : 每秒读取次数（读热点有多热）
      - "write_per_day": 每天写入次数
      - "consistency"  : 一致性要求, "high" 或 "low"
    输出: 字符串 "normalize" 或 "denormalize"

    决策规则（读多写少 + 一致性要求不高 -> 反范式化缓存热点）:
      同时满足下面三条 -> 返回 "denormalize"
        1. read_per_sec > 100      (读极热)
        2. write_per_day < 10      (写极少)
        3. consistency == "low"    (能容忍短暂不一致)
      否则 -> "normalize"

    例如:
      {"read_per_sec": 1000, "write_per_day": 1, "consistency": "low"} -> "denormalize"
      {"read_per_sec": 5,    "write_per_day": 500, "consistency": "high"} -> "normalize"
    """
    # TODO: 按上面的规则写 if 判断
    if (scenario['read_per_sec'] > 100 and scenario['write_per_day'] < 10 and scenario['consistency'] == 'low'):
        return 'denormalize'
    return 'normalize'


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    errors = []

    # --- 练习 1 ---
    e1_1 = find_1nf_violations([{"order_id": 1, "product": "键盘,鼠标"},
                                {"order_id": 2, "product": "耳机"}])
    if e1_1 != ["product"]:
        errors.append(f"练习1-例1 ❌ 期望 ['product'] 实际 {e1_1}")

    e1_2 = find_1nf_violations([{"order_id": 1, "tags": ["a", "b"], "price": 299},
                                {"order_id": 2, "tags": ["c"], "price": 99}])
    if e1_2 != ["tags"]:
        errors.append(f"练习1-例2 ❌ 期望 ['tags'] 实际 {e1_2}")

    e1_3 = find_1nf_violations([{"order_id": 1, "price": 299},
                                {"order_id": 2, "price": 99}])
    if e1_3 != []:
        errors.append(f"练习1-例3 ❌ 期望 [] 实际 {e1_3}")

    # --- 练习 2 ---
    e2_1 = find_partial_dependency(["order_id", "product_name"],
                                   {"product_price": ["product_name"],
                                    "qty": ["order_id", "product_name"]})
    if e2_1 != ["product_price"]:
        errors.append(f"练习2-例1 ❌ 期望 ['product_price'] 实际 {e2_1}")

    e2_2 = find_partial_dependency(["order_id", "product_name"],
                                   {"qty": ["order_id", "product_name"]})
    if e2_2 != []:
        errors.append(f"练习2-例2 ❌ 期望 [] 实际 {e2_2}")

    e2_3 = find_partial_dependency(["order_id"],   # 单列主键没有"一半"
                                   {"created_at": ["order_id"]})
    if e2_3 != []:
        errors.append(f"练习2-例3 ❌ 期望 [] 实际 {e2_3}")

    # --- 练习 3 ---
    e3_1 = find_transitive_dependency(["order_id"],
                                      {"user_city": ["user_id"],
                                       "created_at": ["order_id"]})
    if e3_1 != ["user_city"]:
        errors.append(f"练习3-例1 ❌ 期望 ['user_city'] 实际 {e3_1}")

    e3_2 = find_transitive_dependency(["order_id"],
                                      {"created_at": ["order_id"]})
    if e3_2 != []:
        errors.append(f"练习3-例2 ❌ 期望 [] 实际 {e3_2}")

    # --- 练习 4 ---
    e4_1 = highest_normal_form(["order_id"], {"user_city": ["user_id"]})
    if e4_1 != "2NF":
        errors.append(f"练习4-例1 ❌ 期望 '2NF' 实际 {e4_1}")

    e4_2 = highest_normal_form(["order_id", "product_name"],
                               {"qty": ["order_id", "product_name"]})
    if e4_2 != "3NF":
        errors.append(f"练习4-例2 ❌ 期望 '3NF' 实际 {e4_2}")

    e4_3 = highest_normal_form(["order_id", "product_name"],
                               {"product_price": ["product_name"]})
    if e4_3 != "1NF":
        errors.append(f"练习4-例3 ❌ 期望 '1NF' 实际 {e4_3}")

    # --- 练习 5 ---
    e5_1 = denormalize_advice({"read_per_sec": 1000, "write_per_day": 1, "consistency": "low"})
    if e5_1 != "denormalize":
        errors.append(f"练习5-例1 ❌ 期望 'denormalize' 实际 {e5_1}")

    e5_2 = denormalize_advice({"read_per_sec": 5, "write_per_day": 500, "consistency": "high"})
    if e5_2 != "normalize":
        errors.append(f"练习5-例2 ❌ 期望 'normalize' 实际 {e5_2}")

    e5_3 = denormalize_advice({"read_per_sec": 1000, "write_per_day": 1, "consistency": "high"})
    if e5_3 != "normalize":
        errors.append(f"练习5-例3 ❌ 期望 'normalize' 实际 {e5_3}")

    # --- 结果 ---
    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！9 Normalization = ✅")
