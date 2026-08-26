"""Phase 4 central Brain integration for Gizmo agents."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from gizmo.agents.core_agents import core_agent_map
from gizmo.brain.models import BrainMemoryType
from gizmo.core.models import Task, TaskStatus, now_iso
from gizmo.core.store import JsonStore


@dataclass
class AgentPreflight:
    agent_id: str
    task_id: str
    project: str
    objective: str
    created_at: str = field(default_factory=now_iso)
    context: dict[str, Any] = field(default_factory=dict)
    recalled_memory_ids: list[str] = field(default_factory=list)
    knowledge_gaps: list[dict[str, Any]] = field(default_factory=list)
    ready: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentEvaluation:
    agent_id: str
    task_id: str
    project: str
    objective: str
    achieved: bool
    score: float
    created_at: str = field(default_factory=now_iso)
    worked: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    learned: list[str] = field(default_factory=list)
    captured_memory_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AgentBrainBridge:
    """Forces agents through the central Brain before and after meaningful work."""

    def __init__(self, brain: Any, store: JsonStore) -> None:
        self.brain = brain
        self.store = store

    def before_task(self, task: Task) -> AgentPreflight:
        agent = core_agent_map().get(task.assigned_agent)
        agent_name = agent.name if agent else task.assigned_agent
        context_pack = self.brain.build_context(task.objective, project=task.project)
        recalled = [item["id"] for item in context_pack.useful_context]
        preflight = AgentPreflight(
            agent_id=task.assigned_agent,
            task_id=task.id,
            project=task.project,
            objective=task.objective,
            context=context_pack.to_dict(),
            recalled_memory_ids=recalled,
            knowledge_gaps=context_pack.gaps,
            ready=context_pack.ready,
        )
        task.record(
            "brain_preflight",
            f"{agent_name} recalled {len(recalled)} central Brain memories and found {len(context_pack.gaps)} gaps",
            recalled_memory_ids=recalled,
            critical_gaps=sum(1 for gap in context_pack.gaps if gap.get("critical")),
        )
        self.store.write(preflight.to_dict(), "brain", "agent_preflights", f"{task.id}.json")
        self._update_agent_profile(task.assigned_agent, agent_name, preflight=preflight)
        return preflight

    def after_task(self, task: Task, *, worked: list[str] | None = None, failed: list[str] | None = None) -> AgentEvaluation:
        achieved = task.status == TaskStatus.COMPLETED
        score = 0.9 if achieved else 0.35
        if task.lessons_learned:
            score = min(1.0, score + 0.05)
        evaluation = AgentEvaluation(
            agent_id=task.assigned_agent,
            task_id=task.id,
            project=task.project,
            objective=task.objective,
            achieved=achieved,
            score=round(score, 3),
            worked=worked or (["central Brain preflight completed"] if achieved else []),
            failed=failed or ([] if achieved else [task.result or "task did not complete"]),
            learned=list(task.lessons_learned),
        )
        captured = self.capture_meaningful_memory(task, evaluation)
        evaluation.captured_memory_ids = [memory.id for memory in captured]
        self.store.write(evaluation.to_dict(), "brain", "agent_evaluations", f"{task.id}.json")
        self._update_agent_profile(task.assigned_agent, task.assigned_agent, evaluation=evaluation)
        self._write_collective_memory(evaluation, captured)
        return evaluation

    def capture_meaningful_memory(self, task: Task, evaluation: AgentEvaluation) -> list[Any]:
        captured: list[Any] = []
        meaningful = bool(task.result or task.lessons_learned or evaluation.failed or evaluation.worked)
        if not meaningful:
            return captured
        experience = self.brain.record_experience(
            f"{task.assigned_agent} worked on {task.objective[:70]}",
            "\n".join([
                f"Problem: {task.objective}",
                f"Context: project {task.project}, status {task.status.value}",
                f"Action/result: {task.result or 'No result recorded'}",
                f"Worked: {', '.join(evaluation.worked) or 'none recorded'}",
                f"Failed: {', '.join(evaluation.failed) or 'none recorded'}",
                f"Lesson: {'; '.join(task.lessons_learned) or 'none recorded'}",
                f"Prevention: use central Brain preflight and capture evaluation after work.",
            ]),
            source="agent-memory-bridge",
            source_agent=task.assigned_agent,
            project=task.project,
            importance=7 if evaluation.achieved else 8,
            confidence=0.82 if evaluation.achieved else 0.65,
            tags=["experience", "agent-memory", task.assigned_agent],
            entities=[task.assigned_agent, task.project, "Second Brain"],
            metadata={"task_id": task.id, "evaluation_score": evaluation.score},
        )
        captured.append(experience)
        if task.lessons_learned:
            lesson = self.brain.record_lesson(
                f"Lesson from {task.assigned_agent}: {task.objective[:60]}",
                "\n".join(task.lessons_learned),
                source="agent-memory-bridge",
                source_agent=task.assigned_agent,
                project=task.project,
                importance=8,
                confidence=0.78,
                tags=["lesson", "collective-agent-memory", task.assigned_agent],
                entities=[task.assigned_agent, task.project, "Agent Network"],
                metadata={"task_id": task.id},
            )
            self.brain.link_memories(experience.id, "produced_lesson", lesson.id, confidence=0.82)
            captured.append(lesson)
        evaluation_memory = self.brain.record_evaluation(
            f"Evaluation: {task.objective[:70]}",
            f"Objective: {task.objective}\nAchieved: {evaluation.achieved}\nScore: {evaluation.score}\nWhat worked: {evaluation.worked}\nWhat failed: {evaluation.failed}\nWhat was learned: {evaluation.learned}",
            source="agent-memory-bridge",
            source_agent="agent-27",
            project=task.project,
            importance=7,
            confidence=0.84,
            tags=["evaluation", "agent-performance", task.assigned_agent],
            entities=[task.assigned_agent, "Quality/Synthesis Agent", task.project],
            metadata={"task_id": task.id, "agent_id": task.assigned_agent},
        )
        if captured:
            self.brain.link_memories(evaluation_memory.id, "evaluates", captured[0].id, confidence=0.8)
        captured.append(evaluation_memory)
        return captured

    def agent_profile(self, agent_id: str) -> dict[str, Any]:
        return self.store.read("brain", "agent_profiles", f"{agent_id}.json", default={
            "agent_id": agent_id,
            "tasks_seen": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "average_evaluation": 0.0,
            "memory_contributions": 0,
            "common_failures": [],
            "best_skills": [],
            "last_used": None,
        })

    def collective_memory(self) -> dict[str, Any]:
        return self.store.read("brain", "collective_agent_memory.json", default={"discoveries": [], "lessons": [], "evaluations": []})

    def _update_agent_profile(self, agent_id: str, agent_name: str, *, preflight: AgentPreflight | None = None, evaluation: AgentEvaluation | None = None) -> None:
        profile = self.agent_profile(agent_id)
        profile["agent_name"] = agent_name
        profile["last_used"] = now_iso()
        if preflight:
            profile["tasks_seen"] = profile.get("tasks_seen", 0) + 1
            profile["last_recalled_memory_ids"] = preflight.recalled_memory_ids
            profile["last_gap_count"] = len(preflight.knowledge_gaps)
        if evaluation:
            if evaluation.achieved:
                profile["tasks_completed"] = profile.get("tasks_completed", 0) + 1
            else:
                profile["tasks_failed"] = profile.get("tasks_failed", 0) + 1
                profile.setdefault("common_failures", []).extend(evaluation.failed[:3])
            total = max(1, profile.get("tasks_completed", 0) + profile.get("tasks_failed", 0))
            prior = profile.get("average_evaluation", 0.0)
            profile["average_evaluation"] = round(((prior * (total - 1)) + evaluation.score) / total, 3)
            profile["memory_contributions"] = profile.get("memory_contributions", 0) + len(evaluation.captured_memory_ids)
            if evaluation.worked:
                skills = set(profile.get("best_skills", []))
                skills.update(evaluation.worked)
                profile["best_skills"] = sorted(skills)[:10]
        self.store.write(profile, "brain", "agent_profiles", f"{agent_id}.json")

    def _write_collective_memory(self, evaluation: AgentEvaluation, captured: list[Any]) -> None:
        collective = self.collective_memory()
        if evaluation.learned:
            collective.setdefault("lessons", []).append({"agent_id": evaluation.agent_id, "task_id": evaluation.task_id, "learned": evaluation.learned, "created_at": now_iso()})
        collective.setdefault("evaluations", []).append(evaluation.to_dict())
        for memory in captured:
            collective.setdefault("discoveries", []).append({"memory_id": memory.id, "type": memory.type.value, "title": memory.title, "source_agent": memory.source_agent})
        self.store.write(collective, "brain", "collective_agent_memory.json")
