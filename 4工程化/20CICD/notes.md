# 20 CI/CD — GitHub Actions

> 日期：2026-11-15　｜　文件：`.github/workflows/ci.yml`（已通过 GitHub 真实运行）
> 运行记录：CI #1 ✅ test / ✅ deploy　https://github.com/lr6/backend_ai/actions/runs/43670978283

---

## 一、知识点讲解

### 1. CI = Continuous Integration（持续集成）

每次 push，自动做：

```
拉代码 → 装依赖 → lint → test → build
```

任何一步失败，这次提交在 GitHub 上就是红叉。价值：

- **早发现**：不用等合并才发现「在别人机器上跑不起来」
- **环境统一**：runner 每次从干净系统开始，杜绝「我电脑上能跑」
- **可重复**：每次提交的结果都可见

前端类比：把本地的 `npm run lint && npm run test && npm run build` 搬到云端，每次 push 自动跑。

### 2. CD 的两种 D

| | 流程 | 最后一步 |
|---|------|---------|
| **Continuous Delivery（持续交付）** | 自动测试 → 自动构建 → 产物随时可发布 | **人工点「上线」** |
| **Continuous Deployment（持续部署）** | 全自动，测试过了就上线 | 无人 |

Vercel / Netlify 默认「push 到生产分支 → 自动上线」= Continuous Deployment。

### 3. GitHub Actions 模型

```
workflow（.github/workflows/ci.yml）
  └─ 触发 on: push / pull_request / workflow_dispatch
  └─ job（跑在一台机器上）
       └─ runs-on: ubuntu-latest     ← GitHub 提供的临时 VM
       └─ steps（按顺序执行）
            ├─ uses: actions/checkout@v4      ← 拉代码
            ├─ uses: actions/setup-python@v5  ← 装 Python
            └─ run: pytest ...                ← 执行命令
```

**关键认知**：runner 是「执行动作的临时工」，不是「跑你服务的服务器」。job 结束机器即销毁，所以 CD 的部署动作通常是 SSH 到自己的服务器、推 Docker 镜像，或用 self-hosted runner。

### 4. steps 的短路语义

- 同一 job 内 step 顺序执行，**每步默认带隐式 `if: success()`**
- 某步失败 → 后面的 step 一律跳过，job 标记失败
- job 之间：`needs: test` 等的是「test **成功** 结束」，失败则下游 job skipped

反例开关：

| 写法 | 用途 |
|------|------|
| `if: always()` | 不管成败都跑（清理、发通知） |
| `if: failure()` | 只在失败时跑（上传日志、告警） |
| `continue-on-error: true` | 这步失败但不算 job 失败 |

### 5. YAML 结构要点

```yaml
jobs:                      # 字典：job 名 → 配置
  test:                    # job 名
    runs-on: ubuntu-latest
    steps:                 # 列表：有序
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:              # 属于当前列表项，和 uses 对齐
          python-version: "3.12"
```

缩进层级：`jobs`(0) → job 名(2) → `runs-on`/`steps`(4) → `-`(6) → `with`(8) → `with` 的子项(10)。

**列表项的缩进规则**：`- ` 占两个字符位置，同一列表项里的其它 key 要和 `- ` 之后的第一个字符对齐。

### 6. on / needs / if / secrets

```yaml
on:
  push:
    branches: [master]     # 行内列表 = 下面缩进写 - master
  pull_request:
  workflow_dispatch:       # 无参数也要写冒号，值为 null 合法

deploy:
  needs: test              # test 成功才跑
  if: github.event_name == 'push' && github.ref == 'refs/heads/master'
  steps:
    - run: echo "${{ secrets.DEPLOY_HOST }}"
```

- `${{ ... }}` 是 GitHub Actions 表达式语法
- `secrets.XXX` 从仓库 Settings → Secrets and variables → Actions 读取
- **没配置的 secret 是空字符串，不会报错**——所以别指望它报错提醒你忘了配

---

## 二、练习 ↔ 知识点映射

| 练习 | 内容 | 对应知识点 |
|------|------|-----------|
| 1 | push/pull_request/workflow_dispatch + branches | 第 6 节 `on` 写法、YAML mapping vs 字符串 |
| 2 | runs-on + checkout + setup-python | 第 3 节 workflow 模型、`uses` / `with` |
| 3 | pip install → ruff → pytest | `run: \|` 多行脚本、步骤顺序 |
| 4 | needs + if + secrets | 第 4 节短路语义、第 6 节条件与密钥 |

---

## 三、练习纠错全记录

### 探底 1：CI 的机器是谁的？

- 回答：「GitHub 的机器，Linux」——✅ 正确。

### 探底 2：CI 是什么？CD 的两种 D？

- 回答：「不知道，都不知道」——直接讲解（第 1、2 节）。
- 检查题「Vercel 自动上线属于哪种 CD」回答 **Continuous Deployment** ✅。

### 检查题：第 3 步失败，第 4 步和 deploy 会执行吗？

- 回答：「不会，不知道为什么，直觉」——直觉正确，补讲了隐式 `if: success()` 和 `needs` 的语义。

### 找不到练习 1/2 的位置

- 现象：用户说「31 行没 on 啊」，实际磁盘文件第 31 行就是 `on:`。
- 原因：**打开了 `4工程化/20CICD/check.py`（测试脚手架），不是 `.github/workflows/ci.yml`（练习文件）**。
- 教训：先确认标签页完整路径；隐藏目录 `.github` 容易点错。

### 练习 1：`on: push, pull_request, workflow_dispatch`

- 现象：检查器提示 `on 的值被解析成普通字符串 'push, pull_request, workflow_dispatch'`。
- 原因：YAML 的 `key: value` 中，冒号后**整行就是一个值**；逗号不会自动拆成列表。
- 正确写法：`on:` 换行，每个触发名作为独立 key 缩进；有参数的再缩进一层。
- 附带修正：`branch` 拼写 → `branches`？本次未犯；`branches: [master]` 是行内列表。

### 练习 2：`with:` 缩进错 + 同一行嵌套 key

- 现象：
  ```yaml
  - uses: actions/setup-python@v5
  with: python-version: "3.12"
  ```
  报错 `while parsing a block collection ... expected <block end>, but found '?'`。
- 原因 1：`with:` 在第 6 格，和 `-` 对齐；列表项在 `-` 处就结束了，YAML 解析冲突。
- 原因 2：`with: python-version: ...` 一行里出现两个冒号，不允许；必须拆成两层。
- 正确：
  ```yaml
  - uses: actions/setup-python@v5
    with:
      python-version: "3.12"
  ```
- 后续：用户明确要求「直接把正确答案写上」，于是 Claude 写完整份并逐段讲解（按教学细则的逃生门）。

### Claude 自己的 bug：`check.py --wait` 不等待首次出现

- 现象：push 后立刻跑 `--wait`，脚本报「还没有 ci.yml 的运行记录」并退出；几秒后 API 里运行才出现。
- 原因：轮询逻辑只在「已找到 run 且未完成」时循环；没找到 run 时直接返回。
- 修复：没找到 run 且 `--wait` 时也 sleep 10 重试，直到 5 分钟上限。

---

## 四、踩坑速查表

| 错误写法 | 报错 / 现象 | 正确写法 |
|---------|-----------|---------|
| `on: push, pull_request` | 被当成一个字符串，触发器不生效 | `on:` 换行 + 每个触发名一个 key |
| `on: [push, pull_request]` | 合法，但没法给 push 加 branches | 需要参数时用 mapping 形式 |
| `with:` 和 `-` 对齐 | `expected <block end>, but found '?'` | `with:` 和 `uses:` 对齐（多缩进 2） |
| `with: python-version: "3.12"` | YAML 解析错误 | 拆成 `with:` 换行 + 子项缩进 |
| `uses: actions/checkout`（无 @版本） | GitHub 拒绝 workflow | `actions/checkout@v4` |
| `steps:` 写成字典 | `steps` must be an array | 每步用 `- ` 列表项 |
| 省略 checkout | 后续步骤找不到仓库文件 | 第一步永远 checkout |
| `needs: test` 写进 steps | 层级错误 | `needs` 是 job 的配置项 |
| `secrets.DEPLOY_HOST` 没配 | **不报错**，得到空字符串 | 先到仓库 Settings 配好 |
| deploy 没有 `if` | PR 也会触发部署 | `if: event_name == 'push' && ref == 'refs/heads/master'` |

---

## 五、真实运行结果

```
CI #1 · push · completed
✅ test: success
✅ deploy: success
https://github.com/lr6/backend_ai/actions/runs/43670978283
```

验证方式：公开 API 轮询（无需 `gh` / token）

```bash
python 4工程化/20CICD/check.py --remote --wait
```

---

## 六、生产延伸

- **依赖缓存**：`actions/setup-python` 加 `cache: pip`，或 `actions/cache`，省掉每次装依赖的时间
- **矩阵测试**：`strategy: matrix: python-version: ["3.11", "3.12"]`，一次跑多版本
- **环境与审批**：`environment: production` + 保护规则，实现「自动到可发布，人工点上线」（Delivery 形态）
- **真实部署**：SSH 到服务器 `git pull && systemctl restart`，或构建 Docker 镜像推送后拉取
- **密钥管理**：生产用 Environments secrets，按环境影响隔离；权限最小化
- **分支保护**：要求 PR + CI 通过才能合并 master，CI 才真正有约束力
- **本地验证**：`actionlint` 查语法、`act` 本地跑 workflow（Docker）
- **成本**：public 仓库 Actions 免费；private 仓库按分钟计费
