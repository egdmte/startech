import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "tasks.json")

STATUSES = ["todo", "in_progress", "blocked", "done"]


@dataclass
class Task:
    id: int
    title: str
    owner: str
    status: str = "todo"
    depends_on: list = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    notes: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_tasks() -> list[Task]:
    if not os.path.exists(DATA_PATH):
        return []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Task(**item) for item in raw]


def save_tasks(tasks: list[Task]) -> None:
    tmp_path = DATA_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump([asdict(t) for t in tasks], f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, DATA_PATH)


def next_id(tasks: list[Task]) -> int:
    return max((t.id for t in tasks), default=0) + 1


def find_task(tasks: list[Task], task_id: int) -> Optional[Task]:
    return next((t for t in tasks if t.id == task_id), None)


def can_advance(task: Task, all_tasks: list[Task]) -> tuple[bool, list[str]]:
    """Returns (allowed, blocking_titles). A task can only move to
    in_progress/done once everything it depends on is done."""
    blocking = []
    for dep_id in task.depends_on:
        dep = find_task(all_tasks, dep_id)
        if dep and dep.status != "done":
            blocking.append(dep.title)
    return (len(blocking) == 0, blocking)


def create_task(tasks: list[Task], title: str, owner: str, depends_on: list[int], notes: str) -> Task:
    task = Task(
        id=next_id(tasks),
        title=title,
        owner=owner,
        status="todo",
        depends_on=depends_on,
        created_at=_now(),
        updated_at=_now(),
        notes=notes,
    )
    tasks.append(task)
    save_tasks(tasks)
    return task


def update_status(tasks: list[Task], task_id: int, new_status: str) -> tuple[bool, list[str]]:
    task = find_task(tasks, task_id)
    if task is None:
        return False, ["task not found"]
    if new_status in ("in_progress", "done"):
        allowed, blocking = can_advance(task, tasks)
        if not allowed:
            return False, blocking
    task.status = new_status
    task.updated_at = _now()
    save_tasks(tasks)
    return True, []


def update_task(tasks: list[Task], task_id: int, title: str, owner: str, depends_on: list[int], notes: str) -> Optional[Task]:
    task = find_task(tasks, task_id)
    if task is None:
        return None
    task.title = title
    task.owner = owner
    task.depends_on = depends_on
    task.notes = notes
    task.updated_at = _now()
    save_tasks(tasks)
    return task
