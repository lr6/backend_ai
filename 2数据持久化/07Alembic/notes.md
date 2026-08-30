# 学习项 7 · Alembic — 数据库迁移

> 完成日期：2026-08-30
> 环境：alembic 1.19.1，PostgreSQL，练习库 `alembic_practice_db`（新建，不动 `todo_orm_db`）

---

## 一、知识点讲解

### 1. 为什么需要迁移（前端类比：数据库的 Git）

| 场景 | `create_all`（练习 6 学的） | Alembic 迁移 |
|------|---------------------------|--------------|
| 第一次建表 | ✅ 能建 | ✅ 能建 |
| 给表加一列 | ❌ 不会更新已有表 | ✅ 生成 add_column |
| 上线后改表结构 | ❌ 只能删库重建 | ✅ 有记录的演进 |
| 回滚 | ❌ 没有历史 | ✅ downgrade |

**核心认知**：`create_all` 是「一把梭建表」，只负责**从无到有**；它不知道表以后要怎么变。生产环境上线后绝不能删库重建，所以需要「有版本的建表」——这就是迁移。

**一句话**：迁移 = **数据库的 Git**
- `upgrade` = 前进（git merge / 应用 commit）
- `downgrade` = 回滚（撤销 commit）
- `revision --autogenerate` = `git diff`（自动算出模型和数据库的差异）

### 2. Alembic 的两处核心配置

| 配置 | 位置 | 作用 | 前端类比 |
|------|------|------|---------|
| `sqlalchemy.url` | `alembic.ini` | **连哪个数据库** | API 的 baseURL |
| `target_metadata` | `alembic/env.py` | **模型长什么样**（差异对比的基准） | TypeScript 的类型定义 |

`env.py` 关键两行：
```python
from models import Base          # 拿到模型的 Base
target_metadata = Base.metadata  # 告诉 Alembic：「模型结构在这」
```

### 3. autogenerate 是「差异驱动」的

```
autogenerate 做的事 = 模型结构 vs 数据库当前结构 → 差异 → 生成迁移
```

- 模型有、库里没有 → `op.create_table(...)`
- 模型加了列、库里没有 → `op.add_column(...)`
- 两边完全一致 → **空迁移**（只有 `pass`）

**空迁移不报错，但说明没差异可生成**。这次会话的核心问题「为什么 autogenerate 生成空迁移」就是因为 `todo_orm_db` 里已经有 create_all 建的表，和模型无差异。解决：用全新空库 `alembic_practice_db`，差异立刻出现。

### 4. 迁移脚本文件解剖（Git 类比贯穿始终）

```python
revision = '2c7e80fe71c8'                    # 这条迁移的 ID（= commit hash）
down_revision = 'd873bca84447'               # 上一条迁移（= parent commit）
# 第一条迁移的 down_revision = None          # 链条起点（= 第一个 commit）

def upgrade():                               # 前进方向
    op.add_column('todos', sa.Column('due_date', sa.Date(), nullable=True))

def downgrade():                             # 回滚方向
    op.drop_column('todos', 'due_date')
```

**顺序的铁律**：
- 建表：先建**被外键引用**的表（users 先于 todos）
- 删表：先删**引用方**（todos 先于 users）—— 倒着拆

### 5. 模型写法 → 数据库结构的对应（2.0 类型推断）

```python
due_date: Mapped[date | None] = mapped_column()
#                        ^^^        ^^ 不写类型也能推断
#                    可空=数据库 nullable=True
```

- `Mapped[date]` → 自动推断出数据库 `DATE` 类型（`sa.Date()`）—— 2.0 特色，**不需要**手写 `mapped_column(Date)`
- `date | None`（可空）→ 翻译成 `nullable=True`
- `date`（非空）→ 翻译成 `nullable=False`

### 6. 可空 vs 非空：为什么新加列尽量用可空

**Postgres 规则**：给已有行加 `NOT NULL` 列且无默认值 → **直接报错**（已有行没有值）。

```
ALTER TABLE todos ADD COLUMN due_date date NOT NULL;  -- 表里有数据就炸
```

所以给已有表加**可选**的新列，模型里写 `Mapped[date | None]`。若确实要非空，得先想好给旧数据的默认值。

### 7. 版本跟踪

- `alembic_version` 表：Alembic 自动建，记录数据库当前在哪个 revision（像 Git 的 HEAD）
- `alembic upgrade head`：一路升到最新
- `alembic history`：列出全部迁移链（= git log）
- `alembic current`：数据库当前停在哪个版本（= git HEAD）

### 8. 补充：id 的自增是数据库的活

`\d users` 显示 `id` 默认值是 `nextval('users_id_seq')` —— 自增主键由**数据库序列**负责，模型不用给 default。这和练习 6 里 `done` 必须写 `default=False` 原因相反：`done` 数据库不会自动给值，模型必须兜底。

---

## 二、练习 ↔ 知识点映射

| 练习 | 内容 | 对应知识点 |
|------|------|-----------|
| 1 | models.py 定义 User/Todo | 模型的 `Base` 是迁移的「对照物」 |
| 2 | alembic.ini 配 `sqlalchemy.url` | 「连哪个库」的配置 |
| 3 | env.py 挂 `target_metadata` | 「模型长什么样」的配置 |
| 4 | 从零生成第一个迁移 | autogenerate 差异驱动；upgrade head 应用；psql + alembic current 验证 |
| 5 | 给 Todo 加 `due_date` | 改模型 → 第二个迁移；down_revision 链；2.0 类型推断；nullable |
| 6 | `downgrade -1` 回滚 | 回滚 = 撤销；downgrade() 函数被执行 |
| 7 | `history` / `current` | 迁移链 = git log；current = HEAD |

---

## 三、练习纠错全记录

### 问题 1（上次会话遗留）：autogenerate 生成空迁移

- **现象**：`alembic revision --autogenerate -m "create users and todos"` 成功，但生成的文件里 `upgrade()` 只有 `pass`
- **原因**：autogenerate 是差异驱动的。`todo_orm_db` 里已经有学习项 6 用 `create_all` 建好的 users/todos 表，和模型**完全一致** → 无差异 → 空迁移
- **对应知识点**：迁移的差异驱动原理（知识点 3）
- **解决**：换全新空库 `alembic_practice_db`（不动 `todo_orm_db`），删掉空迁移文件，重新 autogenerate → 这次日志出现 `Detected added table 'users'` / `Detected added table 'todos'`，生成真正的 `op.create_table(...)`
- **教训**：空迁移 = 没有差异可生成，**先确认库里到底有没有表**，别盲目跑命令

### 问题 2（上次会话遗留）：`__tablename__` 漏写 → InvalidRequestError

- **现象**：Todo 类没写 `__tablename__`，运行报 `InvalidRequestError`
- **原因**：Alembic 不知道这个类映射到哪张表
- **解决**：类里加 `__tablename__ = 'todos'`
- **对应知识点**：模型是迁移的基准，表名是第一步

### 问题 3（本次会话，用户无踩坑）：`due_date` 列写法

- 用户一次写对：`from datetime import date` + `due_date: Mapped[date | None] = mapped_column()`
- autogenerate 准确生成 `op.add_column('todos', sa.Column('due_date', sa.Date(), nullable=True))`
- 验证 `down_revision` 指向第一条迁移 —— **链**建立成功

---

## 四、踩坑速查表

| 错误写法 / 场景 | 报错 / 现象 | 正确写法 |
|----------------|------------|---------|
| 模型类漏 `__tablename__` | `InvalidRequestError` | `__tablename__ = '表名'` |
| 对着已有同结构表的库跑 autogenerate | 生成空迁移（只有 pass） | 用空库，或先确认差异在哪 |
| 给已有数据表加 NOT NULL 新列 | Postgres 报错（已有行无值） | 新可选列写 `Mapped[T \| None]` |
| 建表顺序颠倒（先建引用方） | 外键引用的表不存在报错 | 先建被引用表（users → todos） |
| 删表顺序颠倒（先删被引用方） | 外键约束阻止删除 | 先删引用方（todos → users） |
| macOS 下找不到 alembic | command not found | venv 路径是 `bin/` 不是 Windows 的 `Scripts/`：`.venv/bin/alembic` |
| 升级后不知道到哪了 | — | `alembic current`（HEAD） / `alembic history`（git log） |

---

## 五、常用命令速查

```bash
alembic init alembic                          # 初始化骨架
alembic revision --autogenerate -m "说明"      # 自动生成迁移（git diff）
alembic upgrade head                          # 升到最新
alembic upgrade <revision>                    # 升到指定版本
alembic downgrade -1                          # 回退一步
alembic downgrade base                        # 回退到空
alembic history                               # 迁移历史（git log）
alembic current                               # 当前版本（HEAD）
```

> 本项目演示环境：`2数据持久化/07Alembic/`，练习库 `alembic_practice_db`，迁移历史含 2 条记录。
