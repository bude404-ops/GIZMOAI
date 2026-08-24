"""Structured audit log."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from gizmo.core.models import now_iso
from gizmo.core.store import JsonStore


class AuditLogger:
    def __init__(self, store: JsonStore) -> None:
        self.store = store

    def log(self, agent: str, task: str | None, action: str, result: str, **extra: Any) -> dict[str, Any]:
        entry = {
            "id": f"log-{uuid4().hex[:12]}",
            "timestamp": now_iso(),
            "agent": agent,
            "task": task,
            "action": action,
            "result": result,
            **extra,
        }
        self.store.append_list(entry, "monitoring", "audit_log.json")
        return entry
