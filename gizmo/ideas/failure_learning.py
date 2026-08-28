"""Autonomous failure-pattern learning for GIZMO.

Recovery requeues a failed task. This learner studies failure evidence across
executions, distills patterns, records lessons, and emits recovery rules the
goal loop can use on the next cycle.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from gizmo.brain.models import BrainMemoryType
from gizmo.core.models import TaskStatus, now_iso


@dataclass
class FailurePattern:
    id: str
    signature: str
    capability: str
    step: str
    occurrences: int
    task_ids: list[str]
    execution_ids: list[str]
    lesson: str
    recommended_rule: str
    confidence: float
    severity: str
    evidence: list[str] = field(default_factory=list)
    memory_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FailureLearningReport:
    ready: bool
    learned_at: str
    patterns_found: int
    lessons_created: int
    patterns: list[dict[str, Any]]
    recovery_rules: list[dict[str, Any]]
    next_actions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FailureLearningLoop:
    """Turn repeated execution failures into persistent lessons and rules."""

    def __init__(self, orchestrator: Any) -> None:
        self.orchestrator = orchestrator
        self.store = orchestrator.store
        self.brain = orchestrator.brain_core
        self.tasks = orchestrator.tasks
        self.execution = orchestrator.universal_execution

    def learn(self, *, min_occurrences: int = 1) -> FailureLearningReport:
        failures = self._collect_failures()
        patterns = self._group_failures(failures, min_occurrences=max(1, min_occurrences))
        existing = self._existing_rule_signatures()
        lessons_created = 0
        rules: list[dict[str, Any]] = []
        for pattern in patterns:
            if pattern.signature not in existing:
                pattern.memory_id = self._record_lesson(pattern)
                if pattern.memory_id:
                    lessons_created += 1
            rule = self._rule_from_pattern(pattern)
            rules.append(rule)
            self.store.append_list(rule, "learning", "failure_recovery_rules.json")
        report = FailureLearningReport(
            ready=True,
            learned_at=now_iso(),
            patterns_found=len(patterns),
            lessons_created=lessons_created,
            patterns=[pattern.to_dict() for pattern in patterns],
            recovery_rules=rules,
            next_actions=self._next_actions(patterns),
        )
        data = report.to_dict()
        self.store.write(data, "learning", "latest_failure_learning.json")
        self.store.append_list(data, "learning", "failure_learning_history.json")
        return report

    def _collect_failures(self) -> list[dict[str, Any]]:
        failures: list[dict[str, Any]] = []
        for record in self.execution.list_records(refresh=True):
            for step in record.steps:
                status = step.get("status")
                if status not in {TaskStatus.FAILED.value, TaskStatus.ESCALATED.value}:
                    continue
                task_id = step.get("task_id")
                task_result = ""
                history: list[dict[str, Any]] = []
                retry_count = 0
                if task_id:
                    task = self.tasks.load(task_id)
                    task_result = task.result or ""
                    history = task.execution_history[-5:]
                    retry_count = task.retry_count
                failures.append({
                    "execution_id": record.execution_id,
                    "objective": record.objective,
                    "task_id": task_id,
                    "step": step.get("name") or "unknown step",
                    "capability": step.get("capability") or "unknown capability",
                    "assigned_agent": step.get("assigned_agent"),
                    "status": status,
                    "result": task_result or step.get("result") or step.get("blocked_reason") or status,
                    "retry_count": retry_count,
                    "history": history,
                })
        return failures

    def _group_failures(self, failures: list[dict[str, Any]], *, min_occurrences: int) -> list[FailurePattern]:
        buckets: dict[str, list[dict[str, Any]]] = {}
        for failure in failures:
            signature = self._signature(failure)
            buckets.setdefault(signature, []).append(failure)
        patterns: list[FailurePattern] = []
        for signature, items in buckets.items():
            if len(items) < min_occurrences:
                continue
            first = items[0]
            severity = "HIGH" if any(item.get("status") == TaskStatus.ESCALATED.value for item in items) or len(items) >= 3 else "MEDIUM"
            confidence = min(0.95, 0.58 + len(items) * 0.12)
            lesson = self._lesson(first, items)
            rule = self._recommended_rule(first, items)
            patterns.append(FailurePattern(
                id="failure-pattern-" + uuid4().hex[:10],
                signature=signature,
                capability=first["capability"],
                step=first["step"],
                occurrences=len(items),
                task_ids=sorted({item["task_id"] for item in items if item.get("task_id")}),
                execution_ids=sorted({item["execution_id"] for item in items}),
                lesson=lesson,
                recommended_rule=rule,
                confidence=round(confidence, 3),
                severity=severity,
                evidence=[self._evidence_line(item) for item in items[:5]],
            ))
        return sorted(patterns, key=lambda pattern: (pattern.severity == "HIGH", pattern.occurrences, pattern.confidence), reverse=True)

    @staticmethod
    def _signature(failure: dict[str, Any]) -> str:
        result = str(failure.get("result") or "").lower().strip()
        if "timeout" in result:
            family = "timeout"
        elif "permission" in result or "approval" in result:
            family = "permission"
        elif "dependency" in result or "missing" in result or "not found" in result:
            family = "dependency"
        elif "test" in result or "assert" in result:
            family = "verification"
        else:
            family = result[:48] or str(failure.get("status", "unknown")).lower()
        return f"{failure.get('capability')}::{failure.get('step')}::{family}"

    @staticmethod
    def _lesson(first: dict[str, Any], items: list[dict[str, Any]]) -> str:
        return f"When capability '{first['capability']}' step '{first['step']}' fails with this signature, do not only retry. Capture the blocker, check prerequisites, and choose recovery or rollback before continuing. Seen {len(items)} time(s)."

    @staticmethod
    def _recommended_rule(first: dict[str, Any], items: list[dict[str, Any]]) -> str:
        result = " ".join(str(item.get("result", "")).lower() for item in items)
        if "timeout" in result:
            return "Before retrying, reduce work scope or increase timeout and checkpoint first."
        if "permission" in result or "approval" in result:
            return "Request approval or downgrade to a safe planning step before execution."
        if "dependency" in result or "missing" in result or "not found" in result:
            return "Verify dependencies and environment state before requeueing."
        if "test" in result or "assert" in result:
            return "Run the narrow failing verification first, then retry the dependent task."
        return "Checkpoint, inspect task history, then recover only the failed dependency-ready steps."

    @staticmethod
    def _evidence_line(item: dict[str, Any]) -> str:
        return f"{item.get('execution_id')}::{item.get('task_id')}::{item.get('status')}::{str(item.get('result'))[:120]}"

    def _record_lesson(self, pattern: FailurePattern) -> str | None:
        try:
            memory = self.brain.remember(
                BrainMemoryType.LESSON,
                f"Failure lesson: {pattern.capability} / {pattern.step}"[:120],
                f"Pattern: {pattern.signature}\nLesson: {pattern.lesson}\nRule: {pattern.recommended_rule}\nEvidence: {'; '.join(pattern.evidence)}",
                source="failure-learning-loop",
                source_agent="agent-26",
                project="Gizmo",
                importance=9 if pattern.severity == "HIGH" else 7,
                confidence=pattern.confidence,
                tags=["failure-learning", pattern.capability, pattern.severity.lower()],
                entities=[pattern.capability, pattern.step],
                metadata={"pattern": pattern.to_dict()},
            )
            return memory.id
        except Exception:
            return None

    def _existing_rule_signatures(self) -> set[str]:
        rules = self.store.read("learning", "failure_recovery_rules.json", default=[])
        return {str(rule.get("signature")) for rule in rules if isinstance(rule, dict)}

    @staticmethod
    def _rule_from_pattern(pattern: FailurePattern) -> dict[str, Any]:
        return {
            "id": "recovery-rule-" + uuid4().hex[:10],
            "signature": pattern.signature,
            "capability": pattern.capability,
            "step": pattern.step,
            "severity": pattern.severity,
            "confidence": pattern.confidence,
            "rule": pattern.recommended_rule,
            "lesson": pattern.lesson,
            "memory_id": pattern.memory_id,
            "created_at": now_iso(),
        }

    @staticmethod
    def _next_actions(patterns: list[FailurePattern]) -> list[str]:
        if not patterns:
            return ["No failed execution patterns found", "Keep monitoring outcome evaluations and health reports"]
        actions = ["Review learned recovery rules before running universal-recover"]
        if any(pattern.severity == "HIGH" for pattern in patterns):
            actions.append("Create a checkpoint before retrying high-severity failure patterns")
        actions.append("Run autonomous-goal --route so learned failures can influence the next objective")
        return actions[:4]
