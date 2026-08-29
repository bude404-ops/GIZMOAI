"""Autonomous goal selection for GIZMO.

This module turns passive reports into active intent: health, outcome verdicts,
next-action queues, upgrade proposals, and thinking history become ranked goals.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from gizmo.brain.models import BrainMemoryType
from gizmo.core.models import now_iso


@dataclass
class AutonomousGoalCandidate:
    id: str
    objective: str
    lane: str
    source: str
    reason: str
    urgency: float
    value: float
    confidence: float
    risk: float
    score: float
    evidence: list[str] = field(default_factory=list)
    recommended_command: str = "universal-route"
    approval_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AutonomousGoalDecision:
    decision_id: str
    selected_at: str
    selected_goal: dict[str, Any]
    candidates: list[dict[str, Any]]
    memory_id: str | None
    routed_plan: dict[str, Any] | None
    next_actions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AutonomousGoalLoop:
    """Choose what GIZMO should do next from its own operating evidence."""

    def __init__(self, orchestrator: Any) -> None:
        self.orchestrator = orchestrator
        self.store = orchestrator.store
        self.brain = orchestrator.brain_core

    def select_next_goal(self, *, route: bool = False, execute: bool = False, limit: int = 8) -> AutonomousGoalDecision:
        context = self._collect_context()
        candidates = self._build_candidates(context)
        candidates.sort(key=lambda goal: goal.score, reverse=True)
        selected = candidates[0] if candidates else self._fallback_goal()
        memory_id = self._record_goal_memory(selected, context)
        routed_plan = None
        if route:
            routed_plan = self.orchestrator.universal_route(selected.objective, project="Gizmo", execute=execute)
        decision = AutonomousGoalDecision(
            decision_id="goal-decision-" + uuid4().hex[:10],
            selected_at=now_iso(),
            selected_goal=selected.to_dict(),
            candidates=[goal.to_dict() for goal in candidates[:limit]],
            memory_id=memory_id,
            routed_plan=routed_plan,
            next_actions=self._next_actions(selected, route=route, execute=execute),
        )
        data = decision.to_dict()
        self.store.write(data, "goals", "latest_goal_decision.json")
        self.store.append_list(data, "goals", "goal_decision_history.json")
        return decision

    def _collect_context(self) -> dict[str, Any]:
        return {
            "health": self.orchestrator.universal_health_report(stale_after_minutes=60),
            "outcome": self.store.read("universal", "latest_outcome_evaluation.json", default={}),
            "next_queue": self.store.read("body", "next_queue.json", default=[])[-12:],
            "upgrade_queue": self.store.read("ideas", "upgrade_queue.json", default=[])[-12:],
            "chosen_next": self.store.read("ideas", "chosen_next.json", default=[])[-12:],
            "thinking": self.store.read("ideas", "latest_thinking.json", default={}),
            "last_goal": self.store.read("goals", "latest_goal_decision.json", default={}),
            "failure_learning": self.store.read("learning", "latest_failure_learning.json", default={}),
            "progress": self.store.read("progress", "latest_progress_evaluation.json", default={}),
            "campaign": self.store.read("strategy", "latest_campaign.json", default={}),
            "campaign_tracking": self.store.read("strategy", "latest_tracking.json", default={}),
        }

    def _build_candidates(self, context: dict[str, Any]) -> list[AutonomousGoalCandidate]:
        candidates: list[AutonomousGoalCandidate] = []
        health = context.get("health") or {}
        outcome = context.get("outcome") or {}
        progress = context.get("progress") or {}
        campaign = context.get("campaign") or {}
        tracking = context.get("campaign_tracking") or {}
        if tracking and tracking.get("verdict") in {"BLOCKED", "NEEDS_EVIDENCE"}:
            candidates.append(self._candidate(
                objective=f"Unblock strategic campaign tracking: {tracking.get('next_objective', 'active campaign milestone')}",
                lane="campaign-tracking",
                source="campaign-tracker",
                reason=f"Campaign tracking verdict is {tracking.get('verdict')} at score {tracking.get('score')}; active milestone needs evidence before strategy can advance.",
                urgency=0.74 if tracking.get("verdict") == "BLOCKED" else 0.64,
                value=0.88,
                confidence=0.78,
                risk=0.14,
                evidence=[str(tracking.get("tracking_id", "tracking")), str(tracking.get("campaign_id", "campaign"))],
                recommended_command="autonomous-track-campaign",
            ))

        if campaign and campaign.get("milestones"):
            open_milestone = next((item for item in campaign.get("milestones", []) if item.get("status") == "PLANNED"), campaign.get("milestones", [])[0])
            candidates.append(self._candidate(
                objective=f"Advance strategic campaign: {open_milestone.get('objective', campaign.get('next_objective', 'continue campaign'))}",
                lane="strategic-campaign",
                source="strategy-planner",
                reason=str(campaign.get("thesis", "Strategic campaign is active and should drive the next autonomous move."))[:500],
                urgency=0.66,
                value=0.9,
                confidence=0.78,
                risk=0.16,
                evidence=[str(campaign.get("campaign_id", "campaign")), str(open_milestone.get("id", "milestone"))],
                recommended_command="autonomous-strategy",
            ))

        if progress and progress.get("verdict") in {"STALLED", "MIXED_PROGRESS"}:
            gaps = progress.get("strategic_gaps") or progress.get("blockers") or []
            focus = gaps[0] if gaps else "Improve long-horizon autonomous progress"
            candidates.append(self._candidate(
                objective=f"Improve autonomous progress: {focus}",
                lane="strategic-progress",
                source="progress-evaluator",
                reason=f"Long-horizon verdict is {progress.get('verdict')} with score {progress.get('score')} and trend {progress.get('trend')}.",
                urgency=0.78 if progress.get("verdict") == "STALLED" else 0.62,
                value=0.92,
                confidence=float(progress.get("confidence", 0.68)),
                risk=0.14,
                evidence=[str(item) for item in (gaps[:4] or progress.get("next_actions", [])[:4])],
                recommended_command="autonomous-progress",
            ))

        next_actions = health.get("next_actions") or []
        if health.get("risk") in {"HIGH", "MEDIUM"}:
            action = next_actions[0] if next_actions else "Inspect universal execution health and clear blockers"
            candidates.append(self._candidate(
                objective=f"Stabilize GIZMO universal worker: {action}",
                lane="stability",
                source="universal-health",
                reason=f"Health risk is {health.get('risk')} with failed, paused, stale, approval, or escalated work needing operator-grade triage.",
                urgency=0.92 if health.get("risk") == "HIGH" else 0.72,
                value=0.88,
                confidence=0.9,
                risk=0.18,
                evidence=[str(item) for item in next_actions[:4]],
                recommended_command="universal-health",
            ))
        if outcome and outcome.get("verdict") != "SOLVED":
            candidates.append(self._candidate(
                objective=f"Resolve unsolved execution outcome: {outcome.get('objective', 'latest universal execution')}",
                lane="outcome",
                source="outcome-evaluator",
                reason=f"Latest verdict is {outcome.get('verdict')} at confidence {outcome.get('confidence')}; GIZMO should close the loop instead of merely reporting it.",
                urgency=0.86,
                value=0.9,
                confidence=float(outcome.get("confidence", 0.5)),
                risk=0.22,
                evidence=[str(item) for item in (outcome.get("blockers") or outcome.get("next_actions") or [])[:4]],
                recommended_command="universal-evaluate",
            ))
        learning = context.get("failure_learning") or {}
        for rule in (learning.get("recovery_rules") or [])[:6]:
            candidates.append(self._candidate(
                objective=f"Apply learned recovery rule for {rule.get('capability', 'unknown capability')}: {rule.get('rule', 'inspect failure pattern')}",
                lane="failure-learning",
                source="failure-learning",
                reason=str(rule.get("lesson", "Recovered failure pattern should shape the next run."))[:500],
                urgency=0.69 if rule.get("severity") == "HIGH" else 0.56,
                value=0.84,
                confidence=float(rule.get("confidence", 0.72)),
                risk=0.16,
                evidence=[str(rule.get("signature", "failure-pattern")), str(rule.get("memory_id", "lesson"))],
                recommended_command="autonomous-learn-failures",
            ))

        for item in context.get("next_queue") or []:
            objective = str(item.get("objective", "Execute queued body next action"))
            candidates.append(self._candidate(
                objective=objective,
                lane="body-next-action",
                source="agent-body",
                reason="The agent body already identified this as a next action; the goal loop turns it into ranked intent.",
                urgency=0.58,
                value=0.72,
                confidence=0.74,
                risk=0.16,
                evidence=[str(item.get("source_task", "body queue"))],
            ))
        for item in context.get("upgrade_queue") or []:
            score = float(item.get("score", 0.65))
            candidates.append(self._candidate(
                objective=str(item.get("build_queue_item") or item.get("proposed_change") or item.get("title", "Implement queued upgrade")),
                lane="self-upgrade",
                source="autonomous-thinker",
                reason=str(item.get("problem", "Autonomous thinker queued a self-upgrade."))[:500],
                urgency=0.54 + score * 0.22,
                value=0.76 + score * 0.18,
                confidence=min(0.92, 0.62 + score * 0.25),
                risk=0.34 if item.get("approval_required") else 0.18,
                evidence=[str(item.get("id", "upgrade_queue")), str(item.get("source_idea_id", "idea"))],
                approval_required=bool(item.get("approval_required")),
            ))
        for item in context.get("chosen_next") or []:
            candidates.append(self._candidate(
                objective=str(item.get("next_step") or item.get("title", "Advance chosen autonomous idea")),
                lane=str(item.get("category", "chosen-idea")),
                source="chosen-next",
                reason=str(item.get("reason", "Autonomous thinker selected this as a high-scoring next move."))[:500],
                urgency=0.52,
                value=float(item.get("expected_value", 0.7)),
                confidence=float(item.get("score", 0.65)),
                risk=float(item.get("risk", 0.18)),
                evidence=[str(item.get("id", "chosen_next"))],
            ))
        if not candidates:
            thinking = context.get("thinking") or {}
            questions = thinking.get("questions_asked") or []
            candidates.append(self._candidate(
                objective="Run autonomous thinking and generate fresh ranked self-improvement goals",
                lane="reflection",
                source="fallback-reflection",
                reason="No urgent health, outcome, queue, or upgrade signals exist; deepen autonomous self-questioning next.",
                urgency=0.42,
                value=0.72,
                confidence=0.7,
                risk=0.08,
                evidence=[str(item) for item in questions[:3]],
                recommended_command="autonomous-think",
            ))
        return self._dedupe(candidates)

    def _candidate(self, *, objective: str, lane: str, source: str, reason: str, urgency: float, value: float, confidence: float, risk: float, evidence: list[str] | None = None, recommended_command: str = "universal-route", approval_required: bool = False) -> AutonomousGoalCandidate:
        score = round(max(0.01, min(1.0, urgency * 0.34 + value * 0.34 + confidence * 0.22 - risk * 0.18)), 3)
        return AutonomousGoalCandidate(
            id="goal-" + uuid4().hex[:10],
            objective=objective[:500],
            lane=lane,
            source=source,
            reason=reason[:700],
            urgency=round(urgency, 3),
            value=round(value, 3),
            confidence=round(confidence, 3),
            risk=round(risk, 3),
            score=score,
            evidence=[item[:180] for item in (evidence or []) if item],
            recommended_command=recommended_command,
            approval_required=approval_required,
        )

    def _dedupe(self, candidates: list[AutonomousGoalCandidate]) -> list[AutonomousGoalCandidate]:
        seen: set[str] = set()
        unique: list[AutonomousGoalCandidate] = []
        for candidate in candidates:
            key = candidate.objective.lower().strip()
            if key in seen:
                continue
            seen.add(key)
            unique.append(candidate)
        return unique

    def _fallback_goal(self) -> AutonomousGoalCandidate:
        return self._candidate(
            objective="Inspect GIZMO state and generate a new autonomous improvement goal",
            lane="reflection",
            source="fallback",
            reason="No candidate signals were available, so GIZMO should refresh its own situational awareness.",
            urgency=0.35,
            value=0.62,
            confidence=0.66,
            risk=0.05,
            recommended_command="autonomous-think",
        )

    def _record_goal_memory(self, selected: AutonomousGoalCandidate, context: dict[str, Any]) -> str | None:
        try:
            memory = self.brain.remember(
                BrainMemoryType.GOAL,
                f"Autonomous goal selected: {selected.objective[:90]}",
                f"Selected goal: {selected.objective}\nLane: {selected.lane}\nSource: {selected.source}\nReason: {selected.reason}\nScore: {selected.score}\nEvidence: {'; '.join(selected.evidence)}",
                source="autonomous-goal-loop",
                source_agent="agent-26",
                project="Gizmo",
                importance=9 if selected.score >= 0.75 else 7,
                confidence=selected.confidence,
                tags=["autonomous-goal", selected.lane, selected.source],
                entities=[selected.lane, selected.source],
                metadata={"selected_goal": selected.to_dict(), "health_risk": (context.get("health") or {}).get("risk")},
            )
            return memory.id
        except Exception:
            return None

    @staticmethod
    def _next_actions(selected: AutonomousGoalCandidate, *, route: bool, execute: bool) -> list[str]:
        actions = [f"Use {selected.recommended_command} for: {selected.objective}"]
        if selected.approval_required:
            actions.append("Request operator approval before external side effects")
        if not route:
            actions.append("Run autonomous-goal --route to create a universal plan for the selected goal")
        elif route and not execute:
            actions.append("Review the routed plan, then execute if safe")
        elif execute:
            actions.append("Monitor health and outcome evaluation after execution")
        return actions[:4]
