"""Always-on agent body for GIZMO.

The body gives the brain controlled hands: a supervisor chooses safe work, agents
execute small tasks, results are scored, and the next queue is persisted.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from gizmo.ai.reasoning import ModelReasoner
from gizmo.core.models import Task, TaskStatus, now_iso


@dataclass
class AgentBodyAction:
    agent_id: str
    lane: str
    objective: str
    task_id: str
    status: str
    score: float
    reasoning_provider: str
    reasoning_confidence: float
    memory_ids: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AlwaysOnAgentBody:
    """Permission-aware execution layer used by the cloud brain."""

    def __init__(self, orchestrator: Any, *, reasoner: ModelReasoner | None = None) -> None:
        self.orchestrator = orchestrator
        self.brain = orchestrator.brain_core
        self.store = orchestrator.store
        self.reasoner = reasoner or ModelReasoner()

    def execute_lane(self, *, agent_id: str, lane: str, topic: str, instruction: str, context: Any, execute: bool = True) -> AgentBodyAction:
        objective = f"{lane} lane: {topic}. {instruction}"
        reasoning = self.reasoner.reason(
            agent_id=agent_id,
            lane=lane,
            objective=objective,
            context=context,
            constraints=["public knowledge only", "no secret storage", "approval-gate risky actions", "verify before reporting success"],
        )
        task = Task(project="Gizmo", objective=objective, assigned_agent=agent_id, priority=3)
        task.record("reasoning", reasoning.answer[:900])
        task.lessons_learned.append("Agent body must reason from memory before safe execution.")
        self.orchestrator.tasks.create_task(task)
        executed = self.orchestrator._execute_allowed_task(task) if execute else task
        score = self._score(executed, reasoning)
        next_actions = self._next_actions(lane, topic, score, reasoning)
        action = AgentBodyAction(
            agent_id=agent_id,
            lane=lane,
            objective=objective,
            task_id=executed.id,
            status=executed.status.value if isinstance(executed.status, TaskStatus) else str(executed.status),
            score=score,
            reasoning_provider=reasoning.provider,
            reasoning_confidence=reasoning.confidence,
            memory_ids=reasoning.used_memory_ids,
            next_actions=next_actions,
        )
        self._persist_action(action, reasoning.to_dict())
        return action

    def supervisor_plan(self, *, topics: list[str], project: str = "Gizmo") -> dict[str, Any]:
        searches = []
        for topic in topics:
            matches = self.brain.hybrid_search(topic, project=project, limit=3, include_trace=True)
            searches.append({"topic": topic, "known": len(matches), "top_score": matches[0][0].score if matches else 0})
        ranked = sorted(searches, key=lambda row: (row["known"], row["top_score"]))
        plan = {
            "planned_at": now_iso(),
            "project": project,
            "priority_topics": [row["topic"] for row in ranked],
            "reason": "Prioritize weakly known topics first, then deepen high-value existing knowledge.",
        }
        self.store.write(plan, "body", "supervisor_plan.json")
        self.store.append_list(plan, "body", "supervisor_history.json")
        return plan

    def scorecard(self) -> dict[str, Any]:
        actions = self.store.read("body", "actions.json", default=[])
        by_agent: dict[str, list[float]] = {}
        for action in actions:
            by_agent.setdefault(action.get("agent_id", "unknown"), []).append(float(action.get("score", 0)))
        scores = {agent: round(sum(vals) / max(1, len(vals)), 3) for agent, vals in by_agent.items()}
        card = {"generated_at": now_iso(), "agents": scores, "actions": len(actions)}
        self.store.write(card, "body", "scorecard.json")
        return card

    def _persist_action(self, action: AgentBodyAction, reasoning: dict[str, Any]) -> None:
        row = action.to_dict() | {"created_at": now_iso(), "reasoning": reasoning}
        self.store.append_list(row, "body", "actions.json")
        self.store.write(row, "body", "latest_action.json")
        for next_action in action.next_actions:
            self.store.append_list({"created_at": now_iso(), "source_task": action.task_id, "objective": next_action, "priority": "MEDIUM"}, "body", "next_queue.json")

    @staticmethod
    def _score(task: Task, reasoning: Any) -> float:
        score = 0.35 + (0.35 if task.status == TaskStatus.COMPLETED else 0.1) + (reasoning.confidence * 0.25)
        if reasoning.used_memory_ids:
            score += 0.05
        return round(min(1.0, score), 3)

    @staticmethod
    def _next_actions(lane: str, topic: str, score: float, reasoning: Any) -> list[str]:
        actions = [f"Review {lane} lane output for {topic} and store one reusable lesson."]
        if score < 0.75:
            actions.append(f"Gather more public evidence for {topic} before expanding automation.")
        if reasoning.provider == "local":
            actions.append("Attach a configured model provider to strengthen reasoning depth.")
        return actions[:3]
