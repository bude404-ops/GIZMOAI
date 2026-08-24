"""Task and planning engine for GIZMO bootstrap."""
from __future__ import annotations

from gizmo.core.models import Task, TaskStatus
from gizmo.core.store import JsonStore


class TaskEngine:
    def __init__(self, store: JsonStore) -> None:
        self.store = store

    def create_task(self, task: Task) -> Task:
        task.record("created", "Task created")
        self.save(task)
        return task

    def save(self, task: Task) -> None:
        self.store.write(task.to_dict(), "tasks", f"{task.id}.json")

    def load(self, task_id: str) -> Task:
        data = self.store.read("tasks", f"{task_id}.json")
        if not data:
            raise KeyError(task_id)
        return Task.from_dict(data)

    def list_tasks(self) -> list[Task]:
        tasks_dir = self.store.path("tasks")
        return [Task.from_dict(__import__('json').loads(path.read_text())) for path in sorted(tasks_dir.glob("*.json"))]

    def transition(self, task_id: str, status: TaskStatus, reason: str) -> Task:
        task = self.load(task_id)
        task.status = status
        task.record("status", reason, status=status.value)
        self.save(task)
        return task
