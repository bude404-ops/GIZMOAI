"""Important Telegram event reporting for GIZMO.

This module converts autonomous-cycle evidence into concise owner-facing
Telegram alerts. It is intentionally conservative: only high-signal events are
queued, every event is deduped, and live delivery only happens when explicitly
executed by the caller.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from gizmo.core.models import now_iso
from gizmo.telegram.alert_preferences import TelegramAlertPreferenceStore


@dataclass
class ImportantEvent:
    event_id: str
    key: str
    title: str
    body: str
    priority: str
    source: str
    created_at: str = field(default_factory=now_iso)
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ImportantEventReport:
    report_id: str
    created_at: str
    chat_id: str
    events: list[dict[str, Any]]
    queued: list[dict[str, Any]]
    skipped: list[dict[str, Any]]
    preferences: dict[str, Any] = field(default_factory=dict)
    execute: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ImportantTelegramEventReporter:
    """Find and notify important autonomous events."""

    IMPORTANT_PRIORITIES = {"IMPORTANT", "URGENT", "APPROVAL_REQUIRED", "FAILURE", "SECURITY"}

    def __init__(self, store: Any, notifier: Any) -> None:
        self.store = store
        self.notifier = notifier
        self.preferences = TelegramAlertPreferenceStore(store)

    def report(self, *, chat_id: str, cycle: dict[str, Any] | None = None, execute: bool = False, force: bool = False) -> ImportantEventReport:
        cycle_data = cycle or self.store.read("cloud", "brain_latest.json", default={}) or {}
        events = self.detect(cycle_data)
        queued = []
        skipped = []
        seen = set(self.store.read("telegram", "important_event_keys.json", default=[]))
        prefs = self.preferences.load()
        for event in events:
            allowed, reason = self.preferences.allows(event)
            if not allowed and not force:
                skipped.append({"event": event.to_dict(), "reason": reason})
                continue
            if event.key in seen and not force:
                skipped.append({"event": event.to_dict(), "reason": "duplicate"})
                continue
            note = self.notifier.send(chat_id, self._format_event(event), event.priority, execute=execute)
            queued.append({"event": event.to_dict(), "notification": note.to_dict()})
            seen.add(event.key)
        self.store.write(sorted(seen)[-300:], "telegram", "important_event_keys.json")
        report = ImportantEventReport(
            report_id="important-events-" + uuid4().hex[:10],
            created_at=now_iso(),
            chat_id=str(chat_id),
            events=[event.to_dict() for event in events],
            queued=queued,
            skipped=skipped,
            preferences=prefs.to_dict(),
            execute=execute,
        )
        self.store.write(report.to_dict(), "telegram", "important_events_latest.json")
        self.store.append_list(report.to_dict(), "telegram", "important_events_history.json")
        return report

    def detect(self, cycle: dict[str, Any]) -> list[ImportantEvent]:
        events: list[ImportantEvent] = []
        if not cycle:
            return events
        cycle_id = str(cycle.get("cycle_id") or cycle.get("snapshot", {}).get("cycle_id") or "latest")
        status = cycle.get("status")
        if status and status not in {"COMPLETED", "SKIPPED"}:
            events.append(self._event(
                key=f"cycle:{cycle_id}:status:{status}",
                title="Cloud cycle needs attention",
                body=f"Cycle {cycle_id} ended with status {status}.",
                priority="FAILURE",
                source="cloud-brain",
                data={"status": status},
            ))
        progress = cycle.get("progress_evaluation") or {}
        verdict = progress.get("verdict")
        if verdict in {"STALLED", "MIXED_PROGRESS"}:
            events.append(self._event(
                key=f"progress:{progress.get('evaluation_id', cycle_id)}:{verdict}",
                title=f"Autonomous progress is {verdict}",
                body=f"Score {progress.get('score')}; trend {progress.get('trend')}. Next: {self._first(progress.get('next_actions'))}",
                priority="URGENT" if verdict == "STALLED" else "IMPORTANT",
                source="autonomous-progress",
                data=progress,
            ))
        tracking = cycle.get("campaign_tracking") or {}
        tracking_verdict = tracking.get("verdict")
        if tracking_verdict in {"BLOCKED", "NEEDS_EVIDENCE"}:
            events.append(self._event(
                key=f"tracking:{tracking.get('tracking_id', cycle_id)}:{tracking_verdict}",
                title=f"Campaign tracking: {tracking_verdict}",
                body=f"Campaign {tracking.get('campaign_id', 'unknown')} score {tracking.get('score')}. Active: {tracking.get('next_objective', 'none')}",
                priority="URGENT" if tracking_verdict == "BLOCKED" else "IMPORTANT",
                source="campaign-tracker",
                data=tracking,
            ))
        goal = cycle.get("autonomous_goal") or {}
        selected = goal.get("selected_goal") or {}
        if selected.get("approval_required"):
            events.append(self._event(
                key=f"goal:{goal.get('decision_id', cycle_id)}:approval",
                title="Goal needs approval",
                body=f"Approval-gated objective selected: {selected.get('objective')}",
                priority="APPROVAL_REQUIRED",
                source="autonomous-goal",
                data=selected,
            ))
        learning = cycle.get("failure_learning") or self.store.read("learning", "latest_failure_learning.json", default={}) or {}
        if learning.get("patterns_found", 0) or learning.get("lessons_created", 0):
            severe = [rule for rule in learning.get("recovery_rules", []) if rule.get("severity") == "HIGH"]
            if severe:
                events.append(self._event(
                    key=f"learning:{learning.get('learning_id', cycle_id)}:high-severity",
                    title="High-severity failure pattern learned",
                    body=f"{len(severe)} high-severity recovery rule(s) created. First: {severe[0].get('rule', 'inspect rule')}",
                    priority="IMPORTANT",
                    source="failure-learning",
                    data=learning,
                ))
        health = cycle.get("universal_health") or self.store.read("universal", "latest_health_report.json", default={}) or {}
        if health.get("risk") == "HIGH":
            events.append(self._event(
                key=f"health:{cycle_id}:HIGH:{len(health.get('next_actions', []))}",
                title="Universal worker health is HIGH risk",
                body=f"Next action: {self._first(health.get('next_actions'))}",
                priority="URGENT",
                source="universal-health",
                data=health,
            ))
        approvals = self._pending_approvals_count(cycle)
        if approvals:
            events.append(self._event(
                key=f"approvals:{cycle_id}:{approvals}",
                title="Approval waiting",
                body=f"{approvals} approval request(s) are pending your decision.",
                priority="APPROVAL_REQUIRED",
                source="policy",
                data={"pending_approvals": approvals},
            ))
        return self._dedupe(events)

    def _event(self, *, key: str, title: str, body: str, priority: str, source: str, data: dict[str, Any]) -> ImportantEvent:
        return ImportantEvent(
            event_id="event-" + uuid4().hex[:10],
            key=key,
            title=title[:120],
            body=str(body)[:900],
            priority=priority if priority in self.IMPORTANT_PRIORITIES else "IMPORTANT",
            source=source,
            data=data,
        )

    @staticmethod
    def _first(items: Any) -> str:
        if isinstance(items, list) and items:
            return str(items[0])[:220]
        return "No next action recorded."

    @staticmethod
    def _pending_approvals_count(cycle: dict[str, Any]) -> int:
        policy = cycle.get("policy") or cycle.get("snapshot", {}).get("policy") or {}
        try:
            return int(policy.get("pending_approvals", 0))
        except Exception:
            return 0

    @staticmethod
    def _dedupe(events: list[ImportantEvent]) -> list[ImportantEvent]:
        seen: set[str] = set()
        unique: list[ImportantEvent] = []
        for event in events:
            if event.key in seen:
                continue
            seen.add(event.key)
            unique.append(event)
        return unique

    @staticmethod
    def _format_event(event: ImportantEvent) -> str:
        return (
            f"⚠️ GIZMO IMPORTANT\n"
            f"{event.title}\n"
            f"Source: {event.source}\n"
            f"Priority: {event.priority}\n"
            f"{event.body}"
        )
