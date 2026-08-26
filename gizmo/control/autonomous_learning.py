"""Telegram-triggered autonomous knowledge enhancement loop for GIZMO."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from gizmo.brain.models import BrainMemoryType
from gizmo.core.models import Task, now_iso


SAFE_KNOWLEDGE_TOPICS = [
    "Telegram command center reliability",
    "agent memory recall quality",
    "autonomous task prioritization",
    "GitHub workflow dispatch safety",
    "Second Brain knowledge gaps",
    "approval gate ergonomics",
]


@dataclass
class LearningCycleResult:
    cycle_id: str
    status: str
    started_at: str
    ended_at: str | None = None
    topics: list[str] = field(default_factory=list)
    memories_created: list[str] = field(default_factory=list)
    tasks_created: list[str] = field(default_factory=list)
    gaps: list[dict[str, Any]] = field(default_factory=list)
    vault_report: dict[str, Any] = field(default_factory=dict)
    notification: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TelegramAutonomousKnowledgeRunner:
    """Runs safe autonomous learning cycles under Telegram/Reaper policy boundaries."""

    def __init__(self, orchestrator: Any, notifier: Any | None = None) -> None:
        self.orchestrator = orchestrator
        self.notifier = notifier
        self.store = orchestrator.store
        self.brain = orchestrator.brain_core

    def run_cycle(self, *, chat_id: str | None = None, topics: list[str] | None = None, execute_agents: bool = False) -> LearningCycleResult:
        state = self._state()
        cycle = LearningCycleResult(
            cycle_id=f"tg-learn-{now_iso().replace(':', '').replace('.', '').replace('-', '')}",
            status="SKIPPED",
            started_at=now_iso(),
            topics=topics or SAFE_KNOWLEDGE_TOPICS,
        )
        if not state.get("enabled") or state.get("paused") or state.get("emergency"):
            cycle.notification = self._format_skip(state)
            self._persist(cycle)
            if chat_id and self.notifier:
                self.notifier.queue(chat_id, cycle.notification, "LOW")
            return cycle

        cycle.status = "RUNNING"
        self.brain.record_goal(
            "Telegram autonomous learning cycle",
            "Telegram initiated a permission-bound autonomous knowledge enhancement cycle for GIZMO.",
            source="telegram-autonomous",
            source_agent="agent-26",
            project="Gizmo",
            importance=7,
            confidence=0.9,
            tags=["telegram", "autonomous", "learning"],
            metadata={"cycle_id": cycle.cycle_id},
        )

        for topic in cycle.topics:
            context = self.brain.build_context(topic, project="Gizmo", limit=6)
            gaps = self.brain.detect_knowledge_gaps(topic, project="Gizmo")
            cycle.gaps.extend(gaps[:2])
            research = self.brain.record_research(
                f"Autonomous scan: {topic}",
                self._research_summary(topic, context, gaps),
                source="telegram-autonomous",
                source_agent="agent-26",
                project="Gizmo",
                importance=6,
                confidence=0.82,
                tags=["telegram", "autonomous", "research", "knowledge-enhancement"],
                metadata={"cycle_id": cycle.cycle_id, "topic": topic},
            )
            lesson = self.brain.record_lesson(
                f"Learning action: {topic}",
                self._lesson_summary(topic, gaps),
                source="telegram-autonomous",
                source_agent="agent-26",
                project="Gizmo",
                importance=7,
                confidence=0.86,
                tags=["telegram", "autonomous", "lesson"],
                metadata={"cycle_id": cycle.cycle_id, "topic": topic, "research_id": research.id},
            )
            self.brain.link_memories(research.id, "produced_lesson", lesson.id, 0.85)
            cycle.memories_created.extend([research.id, lesson.id])
            task = self._create_learning_task(topic, execute_agents)
            cycle.tasks_created.append(task.id)

        evaluation = self.brain.record_evaluation(
            "Telegram autonomous learning evaluation",
            f"Cycle {cycle.cycle_id} created {len(cycle.memories_created)} memories and {len(cycle.tasks_created)} follow-up tasks while respecting approval boundaries.",
            source="telegram-autonomous",
            source_agent="agent-26",
            project="Gizmo",
            importance=7,
            confidence=0.9,
            tags=["telegram", "autonomous", "evaluation"],
            metadata={"cycle_id": cycle.cycle_id},
        )
        cycle.memories_created.append(evaluation.id)
        cycle.vault_report = self.brain.rebuild_vault_indexes()
        cycle.ended_at = now_iso()
        cycle.status = "COMPLETED"
        cycle.notification = self._format_complete(cycle)
        self._persist(cycle)
        self.store.append_list(cycle.to_dict(), "telegram", "autonomous_learning_history.json")
        if chat_id and self.notifier:
            self.notifier.queue(chat_id, cycle.notification, "IMPORTANT")
        return cycle

    def enable(self, *, chat_id: str = "", source: str = "telegram") -> dict[str, Any]:
        state = {"enabled": True, "paused": False, "emergency": False, "updated_at": now_iso(), "source": source, "chat_id": str(chat_id), "cycle": "telegram-autonomous-knowledge", "boundaries": ["approval_required", "policy_gated", "no_secret_memory", "safe_learning_topics"]}
        self.store.write(state, "control", "autonomous_mode.json")
        return state

    def latest_cycle(self) -> dict[str, Any] | None:
        latest = self.store.read("telegram", "autonomous_learning_latest.json", default=None)
        return latest

    def _create_learning_task(self, topic: str, execute_agents: bool) -> Task:
        task = Task(project="Gizmo", objective=f"Enhance GIZMO knowledge about {topic}", assigned_agent="agent-26", priority=4)
        task.record("telegram_autonomous_learning", "Created by Telegram autonomous knowledge cycle")
        self.orchestrator.tasks.create_task(task)
        if execute_agents:
            return self.orchestrator._execute_allowed_task(task)
        return task

    def _state(self) -> dict[str, Any]:
        return self.store.read("control", "autonomous_mode.json", default={"enabled": False, "paused": False, "emergency": False})

    def _persist(self, cycle: LearningCycleResult) -> None:
        self.store.write(cycle.to_dict(), "telegram", "autonomous_learning_latest.json")
        self.store.write(cycle.to_dict(), "telegram", "autonomous_cycles", f"{cycle.cycle_id}.json")

    def _research_summary(self, topic: str, context: Any, gaps: list[dict[str, Any]]) -> str:
        context_items = getattr(context, "memories", []) or []
        gap_titles = [gap.get("topic", "unknown gap") for gap in gaps[:3]]
        return (
            f"Autonomous Telegram learning inspected {topic}. "
            f"Relevant memories found: {len(context_items)}. "
            f"Top gaps: {', '.join(gap_titles) if gap_titles else 'none detected'}. "
            "Next action is to preserve concise lessons and create follow-up agent tasks without touching secrets or bypassing approvals."
        )

    def _lesson_summary(self, topic: str, gaps: list[dict[str, Any]]) -> str:
        if gaps:
            return f"For {topic}, prioritize closing the highest-confidence knowledge gaps before expanding autonomous scope. Keep Telegram summaries short and approval-aware."
        return f"For {topic}, existing memory is sufficient for now; keep monitoring for drift and preserve any new operator decisions."

    def _format_skip(self, state: dict[str, Any]) -> str:
        return (
            "🧠 AUTONOMOUS LEARNING SKIPPED\n"
            f"Enabled: {state.get('enabled', False)}\n"
            f"Paused: {state.get('paused', False)}\n"
            f"Emergency: {state.get('emergency', False)}"
        )

    def _format_complete(self, cycle: LearningCycleResult) -> str:
        return (
            "🧠 AUTONOMOUS LEARNING COMPLETE\n"
            f"Cycle: {cycle.cycle_id}\n"
            f"Memories: {len(cycle.memories_created)}\n"
            f"Tasks: {len(cycle.tasks_created)}\n"
            f"Gaps tracked: {len(cycle.gaps)}"
        )
