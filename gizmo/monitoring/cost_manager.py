"""Simple resource and retry limits."""
from __future__ import annotations

from gizmo.core.store import JsonStore


class CostManager:
    def __init__(self, store: JsonStore, max_operations: int = 1000) -> None:
        self.store = store
        self.max_operations = max_operations

    def record_operation(self, label: str, units: float = 1.0) -> None:
        data = self.store.read("monitoring", "costs.json", default={"operations": [], "total_units": 0})
        data["operations"].append({"label": label, "units": units})
        data["total_units"] += units
        self.store.write(data, "monitoring", "costs.json")
        if data["total_units"] > self.max_operations:
            raise RuntimeError("cost/resource limit exceeded")
