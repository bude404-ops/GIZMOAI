"""Persistent searchable memory for GIZMO."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from gizmo.core.models import MemoryKind, now_iso
from gizmo.core.store import JsonStore


class MemorySystem:
    def __init__(self, store: JsonStore) -> None:
        self.store = store

    def add(self, kind: MemoryKind, namespace: str, content: str, tags: list[str] | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        record = {
            "id": f"mem-{uuid4().hex[:12]}",
            "kind": kind.value,
            "namespace": namespace,
            "content": content,
            "tags": tags or [],
            "metadata": metadata or {},
            "created_at": now_iso(),
        }
        self.store.append_list(record, "memory", f"{namespace}.json")
        self.store.append_list(record, "memory", "all.json")
        return record

    def search(self, query: str, namespace: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        terms = [term.lower() for term in query.split() if term.strip()]
        records = self.store.read("memory", "all.json", default=[])
        matches: list[tuple[int, dict[str, Any]]] = []
        for record in records:
            if namespace and record["namespace"] != namespace:
                continue
            haystack = " ".join([record.get("content", ""), " ".join(record.get("tags", []))]).lower()
            score = sum(1 for term in terms if term in haystack)
            if score:
                matches.append((score, record))
        matches.sort(key=lambda item: (item[0], item[1]["created_at"]), reverse=True)
        return [record for _, record in matches[:limit]]
