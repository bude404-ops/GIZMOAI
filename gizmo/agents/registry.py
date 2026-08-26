"""Runtime agent registry built from existing core agents and Brain profiles."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from gizmo.agents.core_agents import CORE_AGENTS
from gizmo.core.models import now_iso
from gizmo.core.store import JsonStore


@dataclass
class AgentRuntimeRecord:
    agent_id: str
    name: str
    role: str
    capabilities: list[str]
    status: str
    current_task: str | None
    permissions: list[str]
    memory_location: str
    last_run: str | None
    last_result: str | None
    health: str
    version: str = "1.0"
    profile: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AgentRegistry:
    def __init__(self, store: JsonStore, agent_brain: Any | None = None) -> None:
        self.store = store
        self.agent_brain = agent_brain

    def list_agents(self) -> list[AgentRuntimeRecord]:
        tasks = self._tasks_by_agent()
        records: list[AgentRuntimeRecord] = []
        for agent in CORE_AGENTS:
            current = tasks.get(agent.id)
            profile = self.agent_brain.agent_profile(agent.id) if self.agent_brain else {}
            health = "healthy" if profile.get("tasks_failed", 0) == 0 else "watch"
            records.append(AgentRuntimeRecord(
                agent_id=agent.id,
                name=agent.name,
                role=agent.role,
                capabilities=agent.task_types,
                status="running" if current else "idle",
                current_task=current.get("id") if current else None,
                permissions=agent.allowed_tools,
                memory_location=agent.memory_namespace,
                last_run=profile.get("last_used"),
                last_result=self._last_result(agent.id),
                health=health,
                profile=profile,
            ))
        return records

    def get_agent(self, agent_id: str) -> AgentRuntimeRecord:
        for record in self.list_agents():
            if record.agent_id == agent_id:
                return record
        raise KeyError(agent_id)

    def export_status(self) -> dict[str, Any]:
        records = [record.to_dict() for record in self.list_agents()]
        return {
            "generated_at": now_iso(),
            "agents": records,
            "counts": {
                "total": len(records),
                "running": sum(1 for r in records if r["status"] == "running"),
                "idle": sum(1 for r in records if r["status"] == "idle"),
                "watch": sum(1 for r in records if r["health"] != "healthy"),
            },
        }

    def _tasks_by_agent(self) -> dict[str, dict[str, Any]]:
        folder = self.store.path("tasks")
        if not folder.exists():
            return {}
        import json
        active: dict[str, dict[str, Any]] = {}
        for path in sorted(folder.glob("*.json")):
            data = json.loads(path.read_text())
            if data.get("status") in {"PLANNING", "RUNNING", "TESTING", "REVIEW", "QUEUED"}:
                active[data.get("assigned_agent", "")] = data
        return active

    def _last_result(self, agent_id: str) -> str | None:
        folder = self.store.path("tasks")
        if not folder.exists():
            return None
        import json
        latest = None
        for path in sorted(folder.glob("*.json")):
            data = json.loads(path.read_text())
            if data.get("assigned_agent") == agent_id and data.get("result"):
                latest = data.get("result")
        return latest
