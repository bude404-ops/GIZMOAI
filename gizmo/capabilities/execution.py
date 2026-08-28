"""Execution ledger for universal GIZMO task plans.

The router decides what should happen. The execution ledger records how that plan is
handed to GIZMO's task engine, which gates apply, and what evidence must exist
before a route can be called complete.
"""
from __future__ import annotations

from copy import deepcopy
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
        pause = data.get("evidence", {}).get("pause", {})
        if data.get("evidence", {}).get("cancellation", {}).get("cancelled") is True:
            status = "CANCELLED"
        elif pause.get("paused") is True:
            status = "PAUSED"
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
        counts = {status: 0 for status in ["PLANNED", "QUEUED", "PAUSED", "RUNNING", "WAITING_APPROVAL", "FAILED", "ESCALATED", "COMPLETED", "CANCELLED"]}
        step_counts = {"total": 0, "queued": 0, "paused": 0, "running": 0, "waiting": 0, "failed": 0, "escalated": 0, "completed": 0, "cancelled": 0, "blocked": 0}
        waiting_approval: list[dict[str, Any]] = []
        paused: list[dict[str, Any]] = []
        checkpointed: list[dict[str, Any]] = []
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
            checkpoint = self.latest_checkpoint(record.execution_id)
            if checkpoint:
                checkpointed.append({"execution_id": record.execution_id, "checkpoint_id": checkpoint.get("checkpoint_id"), "label": checkpoint.get("label"), "created_at": checkpoint.get("created_at")})
            if record.status == "PAUSED":
                pause = record.evidence.get("pause", {})
                paused.append({"execution_id": record.execution_id, "objective": record.objective, "reason": pause.get("reason"), "age_minutes": age_minutes})
            if record.status in {"QUEUED", "RUNNING"} and age_minutes >= stale_after_minutes:
                stale.append({"execution_id": record.execution_id, "status": record.status, "objective": record.objective, "age_minutes": age_minutes})
            for step in record.steps:
                status = step.get("status", "PLANNED")
                step_counts["total"] += 1
                if status == TaskStatus.QUEUED.value:
                    step_counts["queued"] += 1
                elif status == TaskStatus.PAUSED.value:
                    step_counts["paused"] += 1
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
        if paused:
            actions.append("Resume or cancel paused universal executions")
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
        risk = "HIGH" if escalated or failed else ("MEDIUM" if waiting_approval or stale or paused else "LOW")
        report = {
            "ready": True,
            "risk": risk,
            "total_executions": len(records),
            "counts": counts,
            "step_counts": step_counts,
            "waiting_approval": waiting_approval,
            "paused": paused,
            "checkpointed": checkpointed,
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
        if record.status == "PAUSED" or record.evidence.get("pause", {}).get("paused") is True:
            record.evidence["runner"] = {"ran": 0, "blocked": "execution paused", "updated_at": now_iso()}
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


    def list_checkpoints(self, execution_id: str) -> list[dict[str, Any]]:
        """Return checkpoints for an execution, newest first."""
        folder = self.store.path("universal", "checkpoints", execution_id)
        if not folder.exists():
            return []
        checkpoints: list[dict[str, Any]] = []
        for path in folder.glob("*.json"):
            data = self.store.read("universal", "checkpoints", execution_id, path.name)
            if data:
                checkpoints.append(data)
        return sorted(checkpoints, key=lambda item: item.get("created_at", ""), reverse=True)

    def latest_checkpoint(self, execution_id: str) -> dict[str, Any] | None:
        checkpoints = self.list_checkpoints(execution_id)
        return checkpoints[0] if checkpoints else None

    def create_checkpoint(self, execution_id: str, *, label: str = "manual checkpoint", reason: str = "operator checkpoint") -> dict[str, Any]:
        """Snapshot an execution record and linked task state for rollback."""
        record = self.refresh(execution_id)
        checkpoint_id = f"chk-{now_iso().replace(':', '').replace('.', '').replace('-', '')}"
        tasks: dict[str, Any] = {}
        for task_id in record.task_ids:
            tasks[task_id] = self.tasks.load(task_id).to_dict()
        checkpoint = {
            "checkpoint_id": checkpoint_id,
            "execution_id": record.execution_id,
            "label": label,
            "reason": reason,
            "execution": deepcopy(record.to_dict()),
            "tasks": tasks,
            "created_at": now_iso(),
        }
        self.store.write(checkpoint, "universal", "checkpoints", execution_id, f"{checkpoint_id}.json")
        record.evidence["checkpoint"] = {"available": True, "checkpoint_id": checkpoint_id, "label": label, "reason": reason, "task_count": len(tasks), "updated_at": now_iso()}
        self._persist(record)
        return checkpoint

    def rollback_execution(self, execution_id: str, *, checkpoint_id: str | None = None, reason: str = "operator rollback", force: bool = False) -> UniversalExecutionRecord:
        """Restore an execution and linked tasks from a checkpoint."""
        current = self.refresh(execution_id)
        terminal = {"COMPLETED", "CANCELLED", "ESCALATED"}
        if current.status in terminal and not force:
            current.evidence["rollback"] = {"rolled_back": False, "reason": f"execution is terminal ({current.status}); use force to rollback", "updated_at": now_iso()}
            self._persist(current)
            return current
        checkpoint = None
        if checkpoint_id:
            checkpoint = self.store.read("universal", "checkpoints", execution_id, f"{checkpoint_id}.json")
        else:
            checkpoint = self.latest_checkpoint(execution_id)
        if not checkpoint:
            current.evidence["rollback"] = {"rolled_back": False, "reason": "no checkpoint available", "updated_at": now_iso()}
            self._persist(current)
            return current
        restored_data = deepcopy(checkpoint["execution"])
        restored_tasks = checkpoint.get("tasks", {})
        before = {step.get("task_id"): step.get("status") for step in current.steps if step.get("task_id")}
        for task_data in restored_tasks.values():
            task = self.tasks.load(task_data["id"])
            restored = type(task).from_dict(task_data)
            restored.record("rollback", "Task restored from universal execution checkpoint", checkpoint_id=checkpoint["checkpoint_id"], reason=reason, previous_status=before.get(restored.id))
            self.tasks.save(restored)
        restored_data.setdefault("evidence", {})["rollback"] = {
            "rolled_back": True,
            "checkpoint_id": checkpoint["checkpoint_id"],
            "label": checkpoint.get("label"),
            "reason": reason,
            "force": force,
            "restored_task_ids": sorted(restored_tasks.keys()),
            "previous_status": current.status,
            "updated_at": now_iso(),
        }
        restored_data["updated_at"] = now_iso()
        record = UniversalExecutionRecord(**restored_data)
        self._persist(record)
        return self.refresh(record.execution_id)

    def evaluate_outcome(self, execution_id: str) -> dict[str, Any]:
        """Judge whether execution evidence actually satisfies the plan's acceptance intent."""
        record = self.refresh(execution_id)
        statuses = [step.get("status") for step in record.steps]
        terminal_success = record.status == "COMPLETED" and statuses and all(status == TaskStatus.COMPLETED.value for status in statuses)
        blockers = []
        if record.status in {"FAILED", "ESCALATED", "CANCELLED", "PAUSED", "WAITING_APPROVAL"}:
            blockers.append(f"execution status is {record.status}")
        incomplete = [step.get("name") for step in record.steps if step.get("status") != TaskStatus.COMPLETED.value]
        if incomplete:
            blockers.append(f"incomplete steps: {', '.join(incomplete[:4])}")
        has_runner = bool(record.evidence.get("runner"))
        has_verification = bool(record.evidence.get("verification_plan") or record.acceptance_checks)
        confidence = 0.92 if terminal_success and has_runner and has_verification else (0.55 if not blockers else 0.25)
        verdict = "SOLVED" if confidence >= 0.85 else ("NEEDS_REVIEW" if confidence >= 0.5 else "NOT_SOLVED")
        next_actions: list[str] = []
        if verdict != "SOLVED":
            if record.status == "FAILED":
                next_actions.append("Run universal-recover or rollback to a checkpoint")
            elif record.status == "PAUSED":
                next_actions.append("Resume or cancel paused execution")
            elif record.status == "WAITING_APPROVAL":
                next_actions.append("Approve or reject waiting execution")
            elif record.status == "CANCELLED":
                next_actions.append("Rollback from checkpoint if work should continue")
            else:
                next_actions.append("Run remaining ready steps or inspect blockers")
        evaluation = {
            "ready": True,
            "execution_id": record.execution_id,
            "verdict": verdict,
            "confidence": confidence,
            "objective": record.objective,
            "status": record.status,
            "blockers": blockers,
            "evidence_present": {"runner": has_runner, "verification": has_verification, "checkpoint": bool(self.latest_checkpoint(execution_id))},
            "next_actions": next_actions or ["No intervention needed"],
            "updated_at": now_iso(),
        }
        record.evidence["outcome_evaluation"] = evaluation
        self._persist(record)
        self.store.write(evaluation, "universal", "latest_outcome_evaluation.json")
        return evaluation

    def pause_execution(self, execution_id: str, *, reason: str = "operator paused") -> UniversalExecutionRecord:
        """Pause unfinished universal execution work without making it terminal."""
        record = self.refresh(execution_id)
        if record.status in {"COMPLETED", "CANCELLED", "ESCALATED"}:
            record.evidence["pause"] = {"paused": False, "reason": f"execution already {record.status.lower()}", "updated_at": now_iso()}
            self._persist(record)
            return record
        paused: list[dict[str, Any]] = []
        preserved: list[dict[str, Any]] = []
        prior_step_statuses: dict[str, str] = {}
        terminal = {TaskStatus.COMPLETED, TaskStatus.ESCALATED, TaskStatus.CANCELLED}
        for step in record.steps:
            task_id = step.get("task_id")
            if task_id:
                task = self.tasks.load(task_id)
                if task.status in terminal:
                    preserved.append({"task_id": task_id, "status": task.status.value})
                    continue
                previous_status = task.status.value
                task.status = TaskStatus.PAUSED
                task.record("pause", "Universal execution paused", reason=reason, previous_status=previous_status)
                self.tasks.save(task)
                step["status"] = TaskStatus.PAUSED.value
                paused.append({"task_id": task_id, "previous_status": previous_status})
            elif step.get("status") != TaskStatus.COMPLETED.value:
                previous_status = step.get("status", "PLANNED")
                prior_step_statuses[step.get("name", f"step-{step.get('order')}")] = previous_status
                step["status"] = TaskStatus.PAUSED.value
                step["blocked_reason"] = reason
                paused.append({"step": step.get("name"), "previous_status": previous_status})
        record.status = "PAUSED"
        record.evidence["pause"] = {"paused": True, "reason": reason, "paused_items": paused, "preserved_terminal_items": preserved, "prior_step_statuses": prior_step_statuses, "updated_at": now_iso()}
        self._persist(record)
        return record

    def resume_execution(self, execution_id: str, *, reason: str = "operator resumed") -> UniversalExecutionRecord:
        """Resume paused universal execution work back to queue/waiting approval."""
        record = self.refresh(execution_id)
        if record.evidence.get("pause", {}).get("paused") is not True:
            record.evidence["resume"] = {"resumed": False, "reason": "execution is not paused", "updated_at": now_iso()}
            self._persist(record)
            return record
        resumed: list[dict[str, Any]] = []
        prior_step_statuses = record.evidence.get("pause", {}).get("prior_step_statuses", {})
        for step in record.steps:
            task_id = step.get("task_id")
            if task_id:
                task = self.tasks.load(task_id)
                if task.status == TaskStatus.PAUSED:
                    task.status = TaskStatus.QUEUED
                    task.record("resume", "Universal execution resumed", reason=reason, next_status=TaskStatus.QUEUED.value)
                    self.tasks.save(task)
                    step["status"] = TaskStatus.QUEUED.value
                    resumed.append({"task_id": task_id, "status": TaskStatus.QUEUED.value})
            elif step.get("status") == TaskStatus.PAUSED.value:
                restored = prior_step_statuses.get(step.get("name"), "PLANNED")
                step["status"] = restored
                step["blocked_reason"] = "approval required" if record.approval_required and not record.task_ids else None
                resumed.append({"step": step.get("name"), "status": restored})
        record.evidence["pause"]["paused"] = False
        record.evidence["resume"] = {"resumed": True, "reason": reason, "resumed_items": resumed, "updated_at": now_iso()}
        if record.approval_required and not record.task_ids:
            record.status = "WAITING_APPROVAL"
        elif record.task_ids:
            record.status = "QUEUED"
        else:
            record.status = "PLANNED"
        self._persist(record)
        return self.refresh(record.execution_id)

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
