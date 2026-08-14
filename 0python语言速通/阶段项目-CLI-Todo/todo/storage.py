
import json
from todo.models import Todo

DATA_FILE = 'todos.json'

def load_todos() -> list[Todo]:
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [Todo.model_validate(d) for d in data]
    except FileNotFoundError:
        return []

def save_todos(todos: list[Todo]) -> None:
    arr = [t.model_dump() for t in todos]
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(arr, f, ensure_ascii=False, indent=2)


