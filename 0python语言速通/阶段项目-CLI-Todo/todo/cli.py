"""cli.py — argparse 入口 + 4 个命令。"""
import argparse
from todo.models import Todo
from todo.storage import load_todos, save_todos


# ===== 下面 4 个函数，你来实现 =====

def cmd_add(title: str) -> None:
    """
    add "标题" → 新建一条 Todo 追加到列表，保存，打印确认。
    提示：load_todos() 拿到列表 → append(Todo(title=title)) → save_todos()
    """

    arr = load_todos()
    arr.append(Todo(title=title))
    save_todos(arr)
    print(f"已添加: {title}")



def cmd_list() -> None:
    """
    list → 列出所有 todo，带序号和状态。
    空列表时打印「暂无 todo」。
    每条格式：`1. ✅ 标题`（done=True 用 ✅，否则 ⬜）
    提示：enumerate(todos, start=1) 能同时拿到序号和元素
    """

    arr = load_todos()
    if len(arr) == 0:
        print(f"「暂无 todo」")
    else:
        for ind, t in enumerate(arr, start = 1):
            status = '✅' if t.done else '⬜'
            print(f"{ind}. {status} {t.title}")

def cmd_done(index: int) -> None:
    """
    done 1 → 把第 index 条标记为完成。
    注意序号越界：index 不在 1..len(todos) 范围内时打印错误并 return。
    提示：todos[index - 1].mark_done()（列表是 0 开始，序号是 1 开始）
    """
    arr = load_todos()
    if index < 1 or index > len(arr):
        print(f"不存在序号为 {index} 的待办事项")
    else:
        arr[index - 1].mark_done()
        save_todos(arr)
        print(f"序号{index} 的待办事项，已经标记完成")


def cmd_delete(index: int) -> None:
    """
    delete 1 → 删除第 index 条。
    同样要处理越界。提示：todos.pop(index - 1)
    """

    arr = load_todos()
    if index < 1 or index > len(arr):
        print(f"不存在序号为 {index} 的待办事项")
    else:
        t = arr.pop(index - 1)
        save_todos(arr)
        print(f"序号{index} 的待办事项: {t.title}，已经被删除了")


# ===== argparse 部分，不用改，照着理解 =====
def main() -> None:
    parser = argparse.ArgumentParser(prog="todo", description="命令行 Todo 工具")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="添加一条 todo")
    p_add.add_argument("title", type=str, help="todo 标题")

    sub.add_parser("list", help="列出所有 todo")

    p_done = sub.add_parser("done", help="把某条标记为完成")
    p_done.add_argument("index", type=int, help="todo 序号（从 1 开始）")

    p_delete = sub.add_parser("delete", help="删除某条 todo")
    p_delete.add_argument("index", type=int, help="todo 序号（从 1 开始）")

    args = parser.parse_args()

    if args.command == "add":
        cmd_add(args.title)
    elif args.command == "list":
        cmd_list()
    elif args.command == "done":
        cmd_done(args.index)
    elif args.command == "delete":
        cmd_delete(args.index)


if __name__ == "__main__":
    main()
