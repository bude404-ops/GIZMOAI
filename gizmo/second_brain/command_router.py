"""GitHub issue/PR comment command router for GIZMO second brain."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from gizmo.core.models import MemoryKind, now_iso
from gizmo.core.models import Task
from gizmo.memory.memory_system import MemorySystem
from gizmo.second_brain.context_indexer import RepoContextIndexer
from gizmo.tasks.task_engine import TaskEngine


@dataclass
class BrainCommandResult:
    id: str
    command: str
    status: str
    response_markdown: str
    artifacts: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SecondBrainCommandRouter:
    """Turns GitHub comments into auditable GIZMO responses."""

    def __init__(self, memory: MemorySystem, tasks: TaskEngine, indexer: RepoContextIndexer) -> None:
        self.memory = memory
        self.tasks = tasks
        self.indexer = indexer

    def route(self, body: str, actor: str = "github-user") -> BrainCommandResult:
        text = body.strip()
        if not text.startswith("/gizmo"):
            return self._result("ignore", "IGNORED", "No GIZMO command detected.")
        parts = text.split(maxsplit=2)
        command = parts[1].lower() if len(parts) >= 2 else "help"
        payload = parts[2] if len(parts) >= 3 else ""
        if command == "help":
            return self._help()
        if command == "status":
            return self._status()
        if command == "context":
            return self._context(payload)
        if command == "remember":
            return self._remember(payload, actor)
        if command == "recall":
            return self._recall(payload)
        if command == "plan":
            return self._plan(payload)
        return self._result(command, "UNKNOWN", f"Unknown GIZMO command: `{command}`. Try `/gizmo help`.")

    def _help(self) -> BrainCommandResult:
        body = """## GIZMO Second Brain Commands

- `/gizmo status` — show brain state.
- `/gizmo context <topic>` — build a repo context pack.
- `/gizmo remember <lesson>` — store a project lesson.
- `/gizmo recall <topic>` — retrieve matching memory.
- `/gizmo plan <objective>` — create a task plan.

Risky writes remain approval-gated."""
        return self._result("help", "OK", body)

    def _status(self) -> BrainCommandResult:
        index = self.indexer.build_index()
        body = f"""## GIZMO Second Brain Status

- Indexed files: **{index['file_count']}**
- Source files: **{index['by_kind'].get('source', 0)}**
- Tests: **{index['by_kind'].get('test', 0)}**
- Docs: **{index['by_kind'].get('documentation', 0)}**

The brain is watching context, memory, tasks, and gates."""
        return self._result("status", "OK", body, {"index": index})

    def _context(self, query: str) -> BrainCommandResult:
        pack = self.indexer.context_pack(query=query, limit=10)
        lines = ["## GIZMO Context Pack", "", f"Query: `{query or 'default'}`", ""]
        for file in pack["files"]:
            lines.append(f"- `{file['path']}` — {file['summary']}")
        return self._result("context", "OK", "\n".join(lines), {"context_pack": pack})

    def _remember(self, lesson: str, actor: str) -> BrainCommandResult:
        if not lesson.strip():
            return self._result("remember", "REJECTED", "Nothing to remember.")
        memory = self.memory.add(kind=MemoryKind.PROJECT, namespace="gizmo-second-brain", content=lesson.strip(), tags=["github", "second-brain", actor])
        return self._result("remember", "OK", f"Remembered. Memory id: `{memory['id']}`", {"memory": memory})

    def _recall(self, query: str) -> BrainCommandResult:
        memories = self.memory.search(query or "github second brain", limit=5)
        if not memories:
            return self._result("recall", "EMPTY", "No matching memory yet.")
        lines = ["## GIZMO Recall", ""]
        for item in memories:
            lines.append(f"- `{item['id']}` — {item['content']}")
        return self._result("recall", "OK", "\n".join(lines), {"memories": memories})

    def _plan(self, objective: str) -> BrainCommandResult:
        if not objective.strip():
            return self._result("plan", "REJECTED", "Give me an objective after `/gizmo plan`.")
        plan = [
            self.tasks.create_task(Task(project="github-second-brain", objective=f"Map repo context for: {objective.strip()}", assigned_agent="agent-05", priority=1)),
            self.tasks.create_task(Task(project="github-second-brain", objective=f"Plan implementation for: {objective.strip()}", assigned_agent="agent-01", priority=1)),
            self.tasks.create_task(Task(project="github-second-brain", objective=f"Verify and document: {objective.strip()}", assigned_agent="agent-27", priority=1)),
        ]
        lines = ["## GIZMO Plan", "", f"Objective: {objective.strip()}", ""]
        for task in plan:
            lines.append(f"- `{task.id}` — {task.objective} → {task.assigned_agent}")
        return self._result("plan", "OK", "\n".join(lines), {"tasks": [task.to_dict() for task in plan]})

    def _result(self, command: str, status: str, response: str, artifacts: dict[str, Any] | None = None) -> BrainCommandResult:
        return BrainCommandResult(id=f"brain-{uuid4().hex[:12]}", command=command, status=status, response_markdown=response, artifacts=artifacts or {})
