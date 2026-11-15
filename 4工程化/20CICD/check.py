"""
第 20 项 CI/CD · 自动检查（不要修改这个文件）

用法：
    python check.py             # 本地检查：YAML 语法 + workflow 结构 + 实际跑一遍测试
    python check.py --remote    # 额外拉取 GitHub 上最近一次真实运行结果
    python check.py --remote --wait   # 运行中时每 10 秒轮询，最多 5 分钟

说明：
- 本地检查不需要 push，可以先改到全绿
- 但 CI 的最终验收是 GitHub 上真的跑绿：check.py --remote
- 只依赖 pyyaml / httpx，仓库是 public，不需要 gh 或 token
"""

import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
REPO = "lr6/backend_ai"
API = f"https://api.github.com/repos/{REPO}/actions"
TEST_DIRS = ["4工程化/17pytest", "4工程化/18httpx-pytest"]

errors = []


def expect(ok, label, detail=""):
    if ok:
        print(f"  ✅ {label}")
    else:
        print(f"  ❌ {label}")
        if detail:
            print(f"     {detail}")
        errors.append(label)


# ============================================================
# 本地检查
# ============================================================
def check_local():
    global errors
    errors = []

    if not WORKFLOW.exists():
        print(f"❌ 找不到 {WORKFLOW.relative_to(ROOT)}")
        return False

    text = WORKFLOW.read_text(encoding="utf-8")
    print("===== YAML 基础 =====")
    expect("\t" not in text, "没有 Tab（YAML 只能用空格缩进）", "文件里出现了 Tab 字符")

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        print(f"  ❌ YAML 解析失败：\n     {e}")
        return False
    expect(isinstance(data, dict), "顶层是 mapping（key: value 结构）")

    # PyYAML 1.1 会把裸 on 解析成布尔 True，两种都认
    triggers = data.get("on", data.get(True)) if isinstance(data, dict) else None

    print("\n===== 练习 1：触发条件 =====")
    if isinstance(triggers, str):
        print(f"  ℹ️  on 的值被解析成普通字符串 {triggers!r}：YAML 不会按逗号拆成多个触发器")
        triggers = {triggers: None}
    if not isinstance(triggers, dict):
        triggers = {}
    expect("push" in triggers, "有 push 触发")
    expect("pull_request" in triggers, "有 pull_request 触发")
    expect("workflow_dispatch" in triggers, "有 workflow_dispatch（可手动触发）")
    push_cfg = triggers.get("push")
    branches = push_cfg.get("branches") if isinstance(push_cfg, dict) else None
    if branches is None:
        print("  ℹ️  push 没限制分支：每次 push 都会跑（练习要求 master，也可以）")
    else:
        expect(
            "master" in branches,
            "push 只监听 master",
            f"实际 branches = {branches}",
        )

    jobs = data.get("jobs") if isinstance(data, dict) else None
    jobs = jobs if isinstance(jobs, dict) else {}
    test_job = jobs.get("test")
    test_job = test_job if isinstance(test_job, dict) else {}
    steps = test_job.get("steps")
    steps = steps if isinstance(steps, list) else []

    print("\n===== 练习 2：job 骨架 =====")
    expect(bool(test_job), "jobs 里有 test")
    runs_on = str(test_job.get("runs-on", ""))
    expect("ubuntu" in runs_on.lower(), "test.runs-on 是 ubuntu", f"实际 {runs_on!r}")

    uses = [str(s.get("uses", "")) for s in steps if isinstance(s, dict)]
    expect(any(u.startswith("actions/checkout@") for u in uses), "用了 actions/checkout")
    setup = next((s for s in steps if str(s.get("uses", "")).startswith("actions/setup-python@")), None)
    expect(setup is not None, "用了 actions/setup-python")
    if setup:
        with_cfg = setup.get("with") or {}
        pyver = str(with_cfg.get("python-version", ""))
        expect(pyver.startswith("3.12"), "setup-python 指定 3.12", f"实际 {pyver!r}")

    print("\n===== 练习 3：依赖 + lint + 测试 =====")
    runs = [str(s.get("run", "")) for s in steps if isinstance(s, dict)]
    all_runs = "\n".join(runs)
    expect("pip install" in all_runs, "有 pip install 步骤")
    expect("ruff" in all_runs and "check" in all_runs, "有 ruff lint 步骤")
    expect("pytest" in all_runs, "有 pytest 步骤")
    expect(
        all(d in all_runs for d in TEST_DIRS),
        "pytest 覆盖了 17pytest 和 18httpx-pytest 两个目录",
        "命令里要出现两个路径",
    )

    print("\n===== 练习 4：部署 job =====")
    deploy = jobs.get("deploy")
    deploy = deploy if isinstance(deploy, dict) else {}
    expect(bool(deploy), "jobs 里有 deploy")
    needs = deploy.get("needs")
    needs_ok = needs == "test" or (isinstance(needs, list) and "test" in needs)
    expect(needs_ok, "deploy 依赖 test（needs: test）", f"实际 needs = {needs!r}")
    if_cfg = str(deploy.get("if", ""))
    expect("refs/heads/master" in if_cfg, "if 判断了 master 分支", f"实际 {if_cfg!r}")
    expect("github.event_name" in if_cfg, "if 判断了事件类型 push", f"实际 {if_cfg!r}")

    deploy_runs = "\n".join(
        str(s.get("run", "")) for s in (deploy.get("steps") or []) if isinstance(s, dict)
    )
    expect("secrets.DEPLOY_HOST" in deploy_runs, "部署步骤引用了 secrets.DEPLOY_HOST")
    expect("secrets.DEPLOY_USER" in deploy_runs, "部署步骤引用了 secrets.DEPLOY_USER")

    # 测试命令本身在本机能不能跑通（CI 会跑同样的路径）
    print("\n===== 本地实跑：CI 要跑的 27 个测试 =====")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *TEST_DIRS, "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    tail = (result.stdout or "").strip().splitlines()[-3:]
    expect(
        result.returncode == 0,
        "pytest 命令在本地通过",
        "\n     ".join(tail) if tail else result.stderr[-300:],
    )

    return not errors


# ============================================================
# 远程检查：拉 GitHub 上最近一次真实运行
# ============================================================
def api_get(url):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "backend_ai-check"}
    # 直连优先
    try:
        with httpx.Client(trust_env=False, timeout=20) as c:
            r = c.get(url, headers=headers)
            if r.status_code == 200:
                return r.json()
    except httpx.HTTPError:
        pass
    # 直连失败再走本机代理
    proxies = urllib.request.getproxies()
    proxy = proxies.get("https") or proxies.get("http")
    if proxy:
        for kwargs in ({"proxy": proxy}, {"proxies": proxy}):
            try:
                with httpx.Client(trust_env=False, timeout=20, **kwargs) as c:
                    r = c.get(url, headers=headers)
                    if r.status_code == 200:
                        return r.json()
            except (httpx.HTTPError, TypeError):
                continue
    return None


def git_head():
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        return ""


def check_remote(wait=False):
    print("\n===== GitHub Actions 真实运行 =====")
    head = git_head()
    deadline = time.time() + 300

    while True:
        data = api_get(f"{API}/runs?per_page=10")
        if data is None:
            print("  ❌ 拉取 GitHub API 失败（网络或仓库不可达）")
            return False

        runs = [r for r in data.get("workflow_runs", []) if str(r.get("path", "")).endswith("ci.yml")]
        if not runs:
            print("  ℹ️  还没有 ci.yml 的运行记录——先把 workflow push 上去")
            print(f"     https://github.com/{REPO}/actions")
            return True

        run = runs[0]
        status, conclusion = run.get("status"), run.get("conclusion")
        label = f"CI #{run.get('run_number')} · {run.get('event')} · {status}"
        print(f"  {'✅' if conclusion == 'success' else '⏳' if status != 'completed' else '❌'} {label}")
        print(f"     {run.get('html_url')}")

        if run.get("head_sha") != head:
            print("  ℹ️  这次运行不是当前 HEAD 触发的（本地还有没 push 的提交？）")

        if status != "completed" and wait and time.time() < deadline:
            print("     等待 10 秒后重试...")
            time.sleep(10)
            continue

        if status == "completed":
            jobs = api_get(f"{API}/runs/{run.get('id')}/jobs") or {}
            for job in jobs.get("jobs", []):
                icon = {"success": "✅", "failure": "❌", "skipped": "⏭️", "cancelled": "⏹️"}.get(
                    job.get("conclusion"), "⏳"
                )
                print(f"     {icon} {job.get('name')}: {job.get('conclusion')}")
            if conclusion == "success":
                print("\n🎉 GitHub 上跑绿了，CD 链路验证通过！")
                return True
            print("\n❌ 这次运行没通过，点上面的链接看日志（或把报错贴给我）")
            return False

        print("  ℹ️  运行还没结束，加 --wait 可以自动轮询")
        return True


if __name__ == "__main__":
    ok = check_local()
    if "--remote" in sys.argv:
        ok = check_remote(wait="--wait" in sys.argv) and ok
    print()
    if errors:
        print(f"本地还有 {len(errors)} 项没通过。")
        sys.exit(1)
    print("🎉 本地检查全绿！push 后用 --remote 看真实运行。")
