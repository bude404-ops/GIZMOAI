"""Execution ledger for universal GIZMO task plans.

The router decides what should happen. The execution ledger records how that plan is
handed to GIZMO's task engine, which gates apply, and what evidence must exist
before a route can be called complete.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from gizmo.core.models import TaskStatus, now_iso
from gizmo.core.store import JsonStore


@dataclass
class ExecutionStepRecord:
    order: int
    name: str
    capability: str
    assigned_agent: str
    task_id: str | None
    status: str
    verification: str
    blocked_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class UniversalExecutionRecord:
    execution_id: str
    request_id: str
    objective: str
    project: str
    status: str
    approval_required: bool
    permission_mode: str
    task_ids: list[str] = field(default_factory=list)
    steps: list[dict[str, Any]] = field(default_factory=list)
    acceptance_checks: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class UniversalExecutionLedger:
    """Persists route-to-task execution handoffs with verification evidence."""

    def __init__(self, store: JsonStore, task_engine: Any) -> None:
        self.store = store
        self.tasks = task_engine

    def create_from_plan(self, plan: Any, *, project: str) -> UniversalExecutionRecord:
        task_ids = [step.get("task_id") for step in plan.decomposition if step.get("task_id")]
        status = "WAITING_APPROVAL" if plan.approval_required else ("QUEUED" if task_ids else "PLANNED")
        record = UniversalExecutionRecord(
            execution_id=f"exec-{now_iso().replace(':', '').replace('.', '').replace('-', '')}",
            request_id=plan.request_id,
            objective=plan.objective,
            project=project,
            status=status,
            approval_required=plan.approval_required,
            permission_mode=plan.permission_mode,
            task_ids=task_ids,
            steps=[
                ExecutionStepRecord(
                    order=step["order"],
                    name=step["name"],
                    capability=step["capability"],
                    assigned_agent=step["assigned_agent"],
                    task_id=step.get("task_id"),
                    status=step.get("status", "PLANNED"),
                    verification=step["verification"],
                    blocked_reason="approval required" if plan.approval_required and not step.get("task_id") else None,
                ).to_dict()
                for step in plan.decomposition
            ],
            acceptance_checks=self.acceptance_checks(plan),
            evidence={
                "plan_status": plan.status,
                "task_count": len(task_ids),
                "selected_agents": plan.selected_agents,
                "selected_tools": plan.selected_tools,
                "verification_plan": plan.verification_plan,
            },
        )
        self._persist(record)
        return record

    def acceptance_checks(self, plan: Any) -> list[str]:
        checks = [
            "Every executable step has a task id or an explicit blocked reason",
            "Approval-required plans do not silently execute",
            "Verification plan is copied into execution evidence",
            "Task dependencies preserve decomposition order",
        ]
        if plan.classification.get("needs_research"):
            checks.append("Research evidence must include citations/source quality before completion")
        if plan.classification.get("needs_code"):
            checks.append("Code work must include changed artifacts and test/build output before completion")
        if plan.classification.get("category") == "ai_generation":
            checks.append("Generation work must include provider/model/license manifest")
        if plan.classification.get("category") == "unreal_engine":
            checks.append("Unreal work must include project/bridge evidence or blocker")
        return checks

    def refresh(self, execution_id: str) -> UniversalExecutionRecord:
        data = self.store.read("universal", "executions", f"{execution_id}.json")
        if not data:
            raise KeyError(execution_id)
        task_ids = data.get("task_ids", [])
        statuses: list[str] = []
        for step in data.get("steps", []):
            task_id = step.get("task_id")
            if not task_id:
                statuses.append(step.get("status", "PLANNED"))
                continue
            task = self.tasks.load(task_id)
            step["status"] = task.status.value
            step["artifacts"] = task.artifacts
            step["tests"] = task.tests
            step["result"] = task.result
            statuses.append(task.status.value)
        if data.get("approval_required") and not task_ids:
            status = "WAITING_APPROVAL"
        elif statuses and all(status == TaskStatus.COMPLETED.value for status in statuses):
            status = "COMPLETED"
        elif any(status == TaskStatus.FAILED.value for status in statuses):
            status = "FAILED"
        elif any(status in {TaskStatus.RUNNING.value, TaskStatus.TESTING.value, TaskStatus.REVIEW.value} for status in statuses):
            status = "RUNNING"
        elif task_ids:
            status = "QUEUED"
        else:
            status = "PLANNED"
        data["status"] = status
        data["updated_at"] = now_iso()
        record = UniversalExecutionRecord(**data)
        self._persist(record)
        return record

    def _persist(self, record: UniversalExecutionRecord) -> None:
        data = record.to_dict()
        self.store.write(data, "universal", "executions", f"{record.execution_id}.json")
        self.store.write(data, "universal", "latest_execution.json")
        self.store.append_list(data, "universal", "execution_history.json")
