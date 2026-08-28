"""Execution ledger for universal GIZMO task plans.

The router decides what should happen. The execution ledger records how that plan is
handed to GIZMO's task engine, which gates apply, and what evidence must exist
before a route can be called complete.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
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

    def attach_approval(self, execution_id: str, approval: Any) -> UniversalExecutionRecord:
        record = self.refresh(execution_id)
        record.approval_required = True
        record.status = "WAITING_APPROVAL"
        record.evidence["approval_request"] = approval.to_dict() if hasattr(approval, "to_dict") else dict(approval)
        record.evidence["approval_decision"] = "PENDING"
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
        if data.get("evidence", {}).get("cancellation", {}).get("cancelled") is True:
            status = "CANCELLED"
        elif data.get("approval_required") and not task_ids:
            status = "WAITING_APPROVAL"
        elif statuses and all(status == TaskStatus.COMPLETED.value for status in statuses):
            status = "COMPLETED"
        elif any(status == TaskStatus.FAILED.value for status in statuses):
            status = "FAILED"
        elif any(status == TaskStatus.ESCALATED.value for status in statuses):
            status = "ESCALATED"
        elif statuses and all(status in {TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value} for status in statuses):
            status = "CANCELLED" if any(status == TaskStatus.CANCELLED.value for status in statuses) else "COMPLETED"
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

    def latest(self) -> UniversalExecutionRecord | None:
        data = self.store.read("universal", "latest_execution.json")
        return UniversalExecutionRecord(**data) if data else None

    def list_records(self, *, refresh: bool = True) -> list[UniversalExecutionRecord]:
        """Return known universal executions ordered newest first."""
        folder = self.store.path("universal", "executions")
        if not folder.exists():
            return []
        records: list[UniversalExecutionRecord] = []
        for path in folder.glob("*.json"):
            data = self.store.read("universal", "executions", path.name)
            if not data:
                continue
            record = UniversalExecutionRecord(**data)
            if refresh:
                record = self.refresh(record.execution_id)
            records.append(record)
        return sorted(records, key=lambda record: record.updated_at, reverse=True)

    def health_report(self, *, stale_after_minutes: int = 60) -> dict[str, Any]:
        """Summarize universal execution health for operator triage."""
        records = self.list_records(refresh=True)
        counts = {status: 0 for status in ["PLANNED", "QUEUED", "RUNNING", "WAITING_APPROVAL", "FAILED", "ESCALATED", "COMPLETED", "CANCELLED"]}
        step_counts = {"total": 0, "queued": 0, "running": 0, "waiting": 0, "failed": 0, "escalated": 0, "completed": 0, "cancelled": 0, "blocked": 0}
        waiting_approval: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []
        escalated: list[dict[str, Any]] = []
        stale: list[dict[str, Any]] = []
        dependency_blocked: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        for record in records:
            counts[record.status] = counts.get(record.status, 0) + 1
            age_minutes = self._age_minutes(record.updated_at, now)
            if record.status == "WAITING_APPROVAL":
                approval = record.evidence.get("approval_request", {})
                waiting_approval.append({"execution_id": record.execution_id, "approval_id": approval.get("id"), "objective": record.objective, "age_minutes": age_minutes})
            if record.status in {"QUEUED", "RUNNING"} and age_minutes >= stale_after_minutes:
                stale.append({"execution_id": record.execution_id, "status": record.status, "objective": record.objective, "age_minutes": age_minutes})
            for step in record.steps:
                status = step.get("status", "PLANNED")
                step_counts["total"] += 1
                if status == TaskStatus.QUEUED.value:
                    step_counts["queued"] += 1
                elif status == TaskStatus.COMPLETED.value:
                    step_counts["completed"] += 1
                elif status == TaskStatus.CANCELLED.value:
                    step_counts["cancelled"] += 1
                elif status == TaskStatus.FAILED.value:
                    step_counts["failed"] += 1
                    failed.append({"execution_id": record.execution_id, "task_id": step.get("task_id"), "step": step.get("name"), "objective": record.objective})
                elif status == TaskStatus.ESCALATED.value:
                    step_counts["escalated"] += 1
                    escalated.append({"execution_id": record.execution_id, "task_id": step.get("task_id"), "step": step.get("name"), "objective": record.objective})
                elif status in {TaskStatus.RUNNING.value, TaskStatus.TESTING.value, TaskStatus.REVIEW.value}:
                    step_counts["running"] += 1
                elif status == TaskStatus.WAITING.value:
                    step_counts["waiting"] += 1
                if step.get("blocked_reason"):
                    step_counts["blocked"] += 1
                task_id = step.get("task_id")
                if task_id and status == TaskStatus.QUEUED.value:
                    task = self.tasks.load(task_id)
                    unmet = [dep for dep in task.dependencies if self.tasks.load(dep).status != TaskStatus.COMPLETED]
                    if unmet:
                        dependency_blocked.append({"execution_id": record.execution_id, "task_id": task_id, "step": step.get("name"), "dependencies": unmet})
        actions: list[str] = []
        if waiting_approval:
            actions.append("Approve or reject waiting universal executions")
        if failed:
            actions.append("Run universal-recover on failed executions")
        if escalated:
            actions.append("Review escalated tasks manually before retrying")
        if stale:
            actions.append("Run universal-run or inspect stale queued executions")
        if dependency_blocked and not failed and not escalated:
            actions.append("Advance dependency-ready queued tasks")
        if not actions:
            actions.append("No intervention needed")
        risk = "HIGH" if escalated or failed else ("MEDIUM" if waiting_approval or stale else "LOW")
        report = {
            "ready": True,
            "risk": risk,
            "total_executions": len(records),
            "counts": counts,
            "step_counts": step_counts,
            "waiting_approval": waiting_approval,
            "failed": failed,
            "escalated": escalated,
            "stale": stale,
            "dependency_blocked": dependency_blocked,
            "next_actions": actions,
            "updated_at": now_iso(),
        }
        self.store.write(report, "universal", "health_report.json")
        return report

    def run_ready_steps(self, execution_id: str, *, executor: Any, max_steps: int | None = None) -> UniversalExecutionRecord:
        """Run dependency-ready internal tasks and refresh the execution ledger.

        The runner only touches tasks already created by the universal router. Approval-gated
        executions remain blocked, and dependency order is enforced from task records.
        """
        record = self.refresh(execution_id)
        if record.status == "CANCELLED":
            record.evidence["runner"] = {"ran": 0, "blocked": "execution cancelled", "updated_at": now_iso()}
            self._persist(record)
            return record
        approved = record.evidence.get("approval_decision") == "APPROVED"
        if (record.approval_required and not approved) or record.status == "WAITING_APPROVAL":
            record.evidence["runner"] = {"ran": 0, "blocked": "approval required", "updated_at": now_iso()}
            self._persist(record)
            return record
        ran = 0
        skipped: list[dict[str, Any]] = []
        for task_id in record.task_ids:
            if max_steps is not None and ran >= max_steps:
                break
            task = self.tasks.load(task_id)
            if task.status != TaskStatus.QUEUED:
                skipped.append({"task_id": task_id, "reason": f"status={task.status.value}"})
                continue
            unmet = [dep for dep in task.dependencies if self.tasks.load(dep).status != TaskStatus.COMPLETED]
            if unmet:
                skipped.append({"task_id": task_id, "reason": "waiting_dependencies", "dependencies": unmet})
                continue
            executor(task)
            ran += 1
        refreshed = self.refresh(execution_id)
        refreshed.evidence["runner"] = {"ran": ran, "skipped": skipped, "updated_at": now_iso()}
        self._persist(refreshed)
        return refreshed

    def cancel_execution(self, execution_id: str, *, reason: str = "operator cancelled") -> UniversalExecutionRecord:
        """Cancel unfinished universal execution work and record the operator reason."""
        record = self.refresh(execution_id)
        if record.status == "COMPLETED":
            record.evidence["cancellation"] = {"cancelled": False, "reason": "execution already completed", "updated_at": now_iso()}
            self._persist(record)
            return record
        cancelled: list[dict[str, Any]] = []
        preserved: list[dict[str, Any]] = []
        terminal = {TaskStatus.COMPLETED, TaskStatus.ESCALATED, TaskStatus.CANCELLED}
        for step in record.steps:
            task_id = step.get("task_id")
            if task_id:
                task = self.tasks.load(task_id)
                if task.status in terminal:
                    preserved.append({"task_id": task_id, "status": task.status.value})
                    step["status"] = task.status.value
                    continue
                previous_status = task.status.value
                task.status = TaskStatus.CANCELLED
                task.result = reason
                task.record("cancel", "Universal execution cancelled", reason=reason, previous_status=previous_status)
                self.tasks.save(task)
                step["status"] = TaskStatus.CANCELLED.value
                step["result"] = reason
                cancelled.append({"task_id": task_id, "previous_status": previous_status})
            elif step.get("status") != TaskStatus.COMPLETED.value:
                previous_status = step.get("status", "PLANNED")
                step["status"] = TaskStatus.CANCELLED.value
                step["blocked_reason"] = reason
                cancelled.append({"step": step.get("name"), "previous_status": previous_status})
        record.status = "CANCELLED"
        record.evidence["cancellation"] = {"cancelled": True, "reason": reason, "cancelled_items": cancelled, "preserved_terminal_items": preserved, "updated_at": now_iso()}
        self._persist(record)
        return record

    def recover_failed_steps(self, execution_id: str, *, max_tasks: int | None = None) -> UniversalExecutionRecord:
        """Requeue failed universal tasks when retry budget remains; escalate exhausted tasks."""
        record = self.refresh(execution_id)
        recovered: list[dict[str, Any]] = []
        escalated: list[dict[str, Any]] = []
        inspected = 0
        for task_id in record.task_ids:
            if max_tasks is not None and inspected >= max_tasks:
                break
            task = self.tasks.load(task_id)
            if task.status != TaskStatus.FAILED:
                continue
            inspected += 1
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.QUEUED
                prior_result = task.result
                task.result = ""
                task.record("retry", "Universal recovery requeued failed task", retry_count=task.retry_count, previous_result=prior_result)
                self.tasks.save(task)
                recovered.append({"task_id": task_id, "retry_count": task.retry_count, "max_retries": task.max_retries})
            else:
                task.status = TaskStatus.ESCALATED
                task.record("escalate", "Retry budget exhausted; operator review required", retry_count=task.retry_count, max_retries=task.max_retries)
                self.tasks.save(task)
                escalated.append({"task_id": task_id, "retry_count": task.retry_count, "max_retries": task.max_retries})
        refreshed = self.refresh(execution_id)
        refreshed.evidence["recovery"] = {"requeued": recovered, "escalated": escalated, "updated_at": now_iso()}
        if escalated:
            refreshed.status = "ESCALATED"
        self._persist(refreshed)
        return refreshed

    def find_by_approval(self, approval_id: str) -> UniversalExecutionRecord | None:
        folder = self.store.path("universal", "executions")
        if not folder.exists():
            return None
        for path in folder.glob("*.json"):
            data = self.store.read("universal", "executions", path.name)
            approval = data.get("evidence", {}).get("approval_request", {})
            if approval.get("id") == approval_id:
                return UniversalExecutionRecord(**data)
        return None

    def release_after_approval(self, execution_id: str, *, approval: Any, task_creator: Any) -> UniversalExecutionRecord:
        record = self.refresh(execution_id)
        approval_status = getattr(approval, "status", None) or approval.get("status")
        if approval_status != "APPROVED":
            record.evidence["approval_decision"] = approval_status or "UNKNOWN"
            record.evidence["release"] = {"released": False, "reason": "approval not granted", "updated_at": now_iso()}
            self._persist(record)
            return record
        task_ids: list[str] = []
        previous: list[str] = []
        for step in record.steps:
            if step.get("task_id"):
                task_ids.append(step["task_id"])
                previous = [step["task_id"]]
                continue
            task_id = task_creator(step, previous)
            step["task_id"] = task_id
            step["status"] = TaskStatus.QUEUED.value
            step["blocked_reason"] = None
            task_ids.append(task_id)
            previous = [task_id]
        record.task_ids = task_ids
        record.status = "QUEUED" if task_ids else "PLANNED"
        record.evidence["approval_request"] = approval.to_dict() if hasattr(approval, "to_dict") else dict(approval)
        record.evidence["approval_decision"] = "APPROVED"
        record.evidence["release"] = {"released": bool(task_ids), "task_count": len(task_ids), "updated_at": now_iso()}
        self._persist(record)
        return record

    def _persist(self, record: UniversalExecutionRecord) -> None:
        data = record.to_dict()
        self.store.write(data, "universal", "executions", f"{record.execution_id}.json")
        self.store.write(data, "universal", "latest_execution.json")
        self.store.append_list(data, "universal", "execution_history.json")

    @staticmethod
    def _age_minutes(timestamp: str, now: datetime) -> int:
        try:
            parsed = datetime.fromisoformat(timestamp)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return max(0, int((now - parsed).total_seconds() // 60))
        except Exception:
            return 0
