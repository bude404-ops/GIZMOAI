"""Long-horizon autonomous progress evaluation for GIZMO.

Single-execution outcome checks answer: did this task solve its intent?
This module answers: is GIZMO becoming more capable across cycles, or just busy?
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from statistics import mean
from typing import Any
from uuid import uuid4

from gizmo.brain.models import BrainMemoryType
from gizmo.core.models import now_iso


@dataclass
class ProgressSignal:
    name: str
    value: float
    weight: float
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProgressEvaluation:
    evaluation_id: str
    evaluated_at: str
    verdict: str
    score: float
    confidence: float
    trend: str
    signals: list[dict[str, Any]]
    blockers: list[str]
    strategic_gaps: list[str]
    next_actions: list[str]
    memory_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AutonomousProgressEvaluator:
    """Judge long-horizon autonomous progress from persisted operating evidence."""

    def __init__(self, orchestrator: Any) -> None:
        self.orchestrator = orchestrator
        self.store = orchestrator.store
        self.brain = orchestrator.brain_core

    def evaluate(self, *, cycles: int = 5) -> ProgressEvaluation:
        cycles = max(1, cycles)
        context = self._collect_context(cycles=cycles)
        signals = self._score_signals(context)
        total_weight = sum(signal.weight for signal in signals) or 1.0
        score = round(sum(signal.value * signal.weight for signal in signals) / total_weight, 3)
        blockers = self._blockers(context)
        strategic_gaps = self._strategic_gaps(context, signals)
        trend = self._trend(context, score)
        verdict = self._verdict(score, blockers, trend)
        confidence = self._confidence(context, signals)
        evaluation = ProgressEvaluation(
            evaluation_id="progress-eval-" + uuid4().hex[:10],
            evaluated_at=now_iso(),
            verdict=verdict,
            score=score,
            confidence=confidence,
            trend=trend,
            signals=[signal.to_dict() for signal in signals],
            blockers=blockers,
            strategic_gaps=strategic_gaps,
            next_actions=self._next_actions(verdict, blockers, strategic_gaps),
        )
        evaluation.memory_id = self._record_memory(evaluation, context)
        data = evaluation.to_dict()
        self.store.write(data, "progress", "latest_progress_evaluation.json")
        self.store.append_list(data, "progress", "progress_evaluation_history.json")
        return evaluation

    def _collect_context(self, *, cycles: int) -> dict[str, Any]:
        cycle_history = self.store.read("cloud", "brain_history.json", default=[])
        snapshot_history = self.store.read("cloud", "brain_snapshots.json", default=[])
        goal_history = self.store.read("goals", "goal_decision_history.json", default=[])
        learning_history = self.store.read("learning", "failure_learning_history.json", default=[])
        latest_outcome = self.store.read("universal", "latest_outcome_evaluation.json", default={})
        health = self.orchestrator.universal_health_report(stale_after_minutes=60)
        return {
            "cycle_history": cycle_history[-cycles:],
            "snapshot_history": snapshot_history[-cycles:],
            "goal_history": goal_history[-cycles:],
            "learning_history": learning_history[-cycles:],
            "latest_outcome": latest_outcome,
            "health": health,
            "cycles_requested": cycles,
        }

    def _score_signals(self, context: dict[str, Any]) -> list[ProgressSignal]:
        snapshots = context.get("snapshot_history") or []
        goals = context.get("goal_history") or []
        learning = context.get("learning_history") or []
        health = context.get("health") or {}
        outcome = context.get("latest_outcome") or {}
        signals = [
            self._cycle_productivity_signal(snapshots),
            self._goal_quality_signal(goals),
            self._learning_signal(learning),
            self._health_signal(health),
            self._outcome_signal(outcome),
        ]
        return signals

    @staticmethod
    def _cycle_productivity_signal(snapshots: list[dict[str, Any]]) -> ProgressSignal:
        if not snapshots:
            return ProgressSignal("cycle_productivity", 0.35, 0.2, ["No cloud cycle snapshots yet"])
        counts = []
        evidence = []
        for snap in snapshots:
            produced = int(snap.get("memories_created", 0)) + int(snap.get("tasks_executed", 0)) + int(snap.get("autonomous_ideas_created", 0))
            counts.append(min(1.0, produced / 24))
            evidence.append(f"{snap.get('cycle_id', 'cycle')}: produced={produced}")
        return ProgressSignal("cycle_productivity", round(mean(counts), 3), 0.18, evidence[-4:])

    @staticmethod
    def _goal_quality_signal(goals: list[dict[str, Any]]) -> ProgressSignal:
        if not goals:
            return ProgressSignal("goal_quality", 0.4, 0.22, ["No autonomous goal decisions yet"])
        scores = [float((goal.get("selected_goal") or {}).get("score", 0.0)) for goal in goals]
        sources = sorted({str((goal.get("selected_goal") or {}).get("source", "unknown")) for goal in goals})
        value = round(mean(scores), 3) if scores else 0.4
        return ProgressSignal("goal_quality", value, 0.24, [f"avg_goal_score={value}", f"sources={', '.join(sources[:6])}"])

    @staticmethod
    def _learning_signal(learning: list[dict[str, Any]]) -> ProgressSignal:
        if not learning:
            return ProgressSignal("self_improvement", 0.38, 0.22, ["No failure-learning history yet"])
        patterns = sum(int(item.get("patterns_found", 0)) for item in learning)
        lessons = sum(int(item.get("lessons_created", 0)) for item in learning)
        rules = sum(len(item.get("recovery_rules", []) or []) for item in learning)
        value = min(1.0, 0.45 + lessons * 0.09 + rules * 0.05 + patterns * 0.03)
        return ProgressSignal("self_improvement", round(value, 3), 0.22, [f"patterns={patterns}", f"lessons={lessons}", f"rules={rules}"])

    @staticmethod
    def _health_signal(health: dict[str, Any]) -> ProgressSignal:
        risk = health.get("risk", "LOW")
        if risk == "LOW":
            value = 0.92
        elif risk == "MEDIUM":
            value = 0.55
        else:
            value = 0.18
        evidence = list(health.get("next_actions", []))[:4]
        return ProgressSignal("operational_health", value, 0.2, evidence or [f"risk={risk}"])

    @staticmethod
    def _outcome_signal(outcome: dict[str, Any]) -> ProgressSignal:
        if not outcome:
            return ProgressSignal("execution_outcomes", 0.42, 0.16, ["No latest outcome evaluation yet"])
        verdict = outcome.get("verdict")
        if verdict == "SOLVED":
            value = 0.94
        elif verdict == "NEEDS_REVIEW":
            value = 0.56
        else:
            value = 0.22
        evidence = [f"verdict={verdict}", f"confidence={outcome.get('confidence')}"] + list(outcome.get("next_actions", []))[:3]
        return ProgressSignal("execution_outcomes", value, 0.16, evidence)

    @staticmethod
    def _blockers(context: dict[str, Any]) -> list[str]:
        blockers = []
        health = context.get("health") or {}
        if health.get("risk") == "HIGH":
            blockers.append("High universal-worker risk remains unresolved")
        outcome = context.get("latest_outcome") or {}
        if outcome and outcome.get("verdict") == "NOT_SOLVED":
            blockers.append("Latest execution outcome is not solved")
        if not context.get("goal_history"):
            blockers.append("No autonomous goal history exists yet")
        if not context.get("learning_history"):
            blockers.append("No self-improvement learning history exists yet")
        return blockers[:6]

    @staticmethod
    def _strategic_gaps(context: dict[str, Any], signals: list[ProgressSignal]) -> list[str]:
        gaps = []
        by_name = {signal.name: signal for signal in signals}
        if by_name["cycle_productivity"].value < 0.55:
            gaps.append("Cloud cycles are not producing enough durable work artifacts")
        if by_name["goal_quality"].value < 0.65:
            gaps.append("Autonomous goals need stronger scoring or better source diversity")
        if by_name["self_improvement"].value < 0.6:
            gaps.append("Failure lessons are not yet accumulating into a strong recovery playbook")
        if by_name["execution_outcomes"].value < 0.65:
            gaps.append("Execution outcomes are not consistently closing as solved")
        return gaps[:6]

    @staticmethod
    def _trend(context: dict[str, Any], score: float) -> str:
        history = context.get("snapshot_history") or []
        if len(history) < 2:
            return "UNKNOWN" if score < 0.7 else "STABLE"
        def produced(snap: dict[str, Any]) -> int:
            return int(snap.get("memories_created", 0)) + int(snap.get("tasks_executed", 0)) + int(snap.get("autonomous_ideas_created", 0))
        if produced(history[-1]) > produced(history[0]):
            return "IMPROVING"
        if produced(history[-1]) < produced(history[0]):
            return "DECLINING"
        return "STABLE"

    @staticmethod
    def _verdict(score: float, blockers: list[str], trend: str) -> str:
        if score >= 0.78 and not blockers:
            return "ADVANCING"
        if score >= 0.6 and trend != "DECLINING":
            return "MIXED_PROGRESS"
        return "STALLED"

    @staticmethod
    def _confidence(context: dict[str, Any], signals: list[ProgressSignal]) -> float:
        evidence_count = sum(1 for signal in signals if signal.evidence)
        histories = sum(1 for key in ["snapshot_history", "goal_history", "learning_history"] if context.get(key))
        return round(min(0.94, 0.44 + evidence_count * 0.06 + histories * 0.08), 3)

    @staticmethod
    def _next_actions(verdict: str, blockers: list[str], gaps: list[str]) -> list[str]:
        actions = []
        if verdict == "ADVANCING":
            actions.append("Continue autonomous-goal --route and monitor next progress evaluation")
        else:
            if blockers:
                actions.append("Clear top blocker before expanding new work")
            if gaps:
                actions.append("Route the highest strategic gap into a universal execution plan")
            actions.append("Run autonomous-learn-failures before the next recovery cycle")
        actions.append("Re-run autonomous-progress after the next cloud or goal cycle")
        return actions[:4]

    def _record_memory(self, evaluation: ProgressEvaluation, context: dict[str, Any]) -> str | None:
        try:
            memory = self.brain.remember(
                BrainMemoryType.EVALUATION,
                f"Autonomous progress verdict: {evaluation.verdict}",
                f"Verdict: {evaluation.verdict}\nScore: {evaluation.score}\nTrend: {evaluation.trend}\nBlockers: {'; '.join(evaluation.blockers)}\nStrategic gaps: {'; '.join(evaluation.strategic_gaps)}\nNext actions: {'; '.join(evaluation.next_actions)}",
                source="autonomous-progress-evaluator",
                source_agent="agent-27",
                project="Gizmo",
                importance=9 if evaluation.verdict == "STALLED" else 8,
                confidence=evaluation.confidence,
                tags=["autonomous-progress", evaluation.verdict.lower(), evaluation.trend.lower()],
                entities=["progress", "autonomy", "gizmo"],
                metadata={"evaluation": evaluation.to_dict(), "cycles_requested": context.get("cycles_requested")},
            )
            return memory.id
        except Exception:
            return None
