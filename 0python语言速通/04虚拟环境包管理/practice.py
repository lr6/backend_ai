"""
第零阶段 · 0.4 虚拟环境 & 包管理 — 检验练习

⚠️ 运行前确保：
1. 已创建虚拟环境：python -m venv .venv
2. 已激活虚拟环境：.venv\Scripts\activate （Windows）或 source .venv/bin/activate （Mac/Linux）
3. 已安装 requests：pip install requests

然后运行：python practice.py
全部通过 = 0.4 过关 ✅
"""

import sys
import os
import requests

# ===== 练习 1：检测虚拟环境 =====
def check_venv() -> dict[str, bool | str]:
    """
    检查当前是否在虚拟环境中运行。
    提示：在 venv 中，sys.prefix 不等于 sys.base_prefix。

    返回 {
        "in_venv": 是否在虚拟环境中,
        "python_path": 当前 Python 解释器路径,
        "venv_name": 虚拟环境目录名（不在 venv 中返回 "无"）
    }
    """
    # TODO: 实现函数体
    in_venv = sys.prefix != sys.base_prefix
    python_path = sys.executable
    venv_name = os.path.basename(sys.prefix) if in_venv else '无'
    return {
        "in_venv": in_venv,
        "python_path": python_path,
        "venv_name": venv_name
    }


# ===== 练习 2：验证包安装 =====
def verify_package(package_name: str) -> bool:
    """
    尝试导入指定的包，判断是否已安装。
    用 try/except ImportError 来检测。

    例如: verify_package("requests") → True（如果已安装）
    例如: verify_package("不存在的包") → False
    """
    # TODO: 实现函数体
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False


# ===== 练习 3：用 requests 发请求 =====
def fetch_url_title(url: str) -> str | None:
    """
    用 requests 库获取指定 URL 的 <title> 标签内容。
    如果请求失败，返回 None。
    提示：用 requests.get() 发 GET 请求，用字符串查找提取 <title>...</title>。

    例如: fetch_url_title("https://example.com")
         → "Example Domain"
    """
    # TODO: 实现函数体
    try:
        resp = requests.get(url)
        html = resp.text
        start_tag = "<title>"
        end_tag = "</title>"
        start_idx = html.find(start_tag)
        end_idx = html.find(end_tag)
        if start_idx == -1 or end_idx == -1:
            return None
        return html[start_idx + len(start_tag): end_idx]
    except Exception:
        return None



# ===== 练习 4：解析 requirements.txt =====
def parse_requirements(content: str) -> dict[str, str | None]:
    """
    解析 requirements.txt 内容，提取包名和版本。
    每行格式："包名==版本" 或 "包名"（无版本则版本为 None）。
    忽略空行和以 # 开头的注释行。

    例如: parse_requirements("requests==2.28.0\nflask\n# 这是注释")
         → {"requests": "2.28.0", "flask": None}
    """
    # TODO: 实现函数体
    d = {}
    arr = content.split('\n')
    for x in arr:
        x = x.strip()
        if x == "" or x.startswith('#'):
            continue
        else:
            if "==" in x:
                a1 = x.split('==')
                d[a1[0]] = a1[1]
            else:
                d[x] = None
    return d


# ===== 练习 5：pyproject.toml 结构理解 =====
def describe_pyproject() -> dict[str, str]:
    """
    返回 pyproject.toml 中各个 section 的作用描述。
    填写字典中每个键对应的描述（一句话即可）。

    返回字段：
    - "project": 描述 [project] 段的用途
    - "dependencies": 描述 dependencies 字段的用途
    - "optional-dependencies": 描述 [project.optional-dependencies] 的用途
    """
    # TODO: 实现函数体
    return {
        "project": "定义项目元数据，如名称、版本、Python版本要求", 
        "dependencies": "声明项目运行时依赖的第三方包", 
        "optional-dependencies": "声明开发时可选的依赖分组，如测试工具"
    }


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    errors = []

    # --- 练习 1 ---
    r1 = check_venv()
    if not isinstance(r1, dict):
        errors.append(f"练习1: 期望返回 dict，实际返回 {type(r1)}")
    else:
        if not r1.get("in_venv"):
            errors.append(f"练习1: in_venv 应为 True，你确定激活了虚拟环境吗？")
        if "python" not in str(r1.get("python_path", "")).lower().replace("\\", "/"):
            errors.append(f"练习1: python_path 看起来不是 Python 路径")

    # --- 练习 2 ---
    if not verify_package("sys"):
        errors.append(f"练习2: sys 是标准库，应该能导入")

    if verify_package("th1s_p4ck4g3_n3v3r_ex1sts"):
        errors.append(f"练习2: 不存在的包应该返回 False")

    if not verify_package("requests"):
        errors.append(f"练习2: requests 应该已安装，请运行 pip install requests")

    # --- 练习 3 ---
    r3 = fetch_url_title("https://example.com")
    if r3 is None:
        errors.append(f"练习3: 请求 https://example.com 失败，检查网络或 requests 安装")
    elif "Example" not in r3:
        errors.append(f"练习3: 期望标题包含 'Example'，实际返回 '{r3}'")

    r3_2 = fetch_url_title("https://httpstat.us/404")
    if r3_2 is not None:
        errors.append(f"练习3: 404 页面应返回 None，实际返回 '{r3_2}'")

    # --- 练习 4 ---
    test_content = "requests==2.28.0\nflask\n# 这是注释\npytest==7.3.1\n"
    r4 = parse_requirements(test_content)
    expected_4 = {"requests": "2.28.0", "flask": None, "pytest": "7.3.1"}
    if r4 != expected_4:
        errors.append(f"练习4: 期望 {expected_4}，实际 {r4}")

    r4_2 = parse_requirements("")
    if r4_2 != {}:
        errors.append(f"练习4-2: 空内容应返回空字典，实际 {r4_2}")

    # --- 练习 5 ---
    r5 = describe_pyproject()
    required_keys = ["project", "dependencies", "optional-dependencies"]
    for key in required_keys:
        if key not in r5:
            errors.append(f"练习5: 缺少键 '{key}'")
        elif not r5[key] or len(r5[key]) < 5:
            errors.append(f"练习5: '{key}' 的描述太短，写一句话")

    # --- 结果 ---
    if errors:
        print(f"❌ 有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！0.4 虚拟环境 & 包管理 = ✅")
