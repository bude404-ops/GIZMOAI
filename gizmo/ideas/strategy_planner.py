"""Autonomous strategic planning for GIZMO.

Goal selection chooses the next move. Progress evaluation judges the trend.
This planner converts both into an explicit multi-step campaign with milestones,
success criteria, risks, and the next route-ready objective.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from gizmo.brain.models import BrainMemoryType
from gizmo.core.models import now_iso


@dataclass
class StrategyMilestone:
    id: str
    objective: str
    lane: str
    success_criteria: list[str]
    evidence_required: list[str]
    status: str = "PLANNED"
    depends_on: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StrategicCampaign:
    campaign_id: str
    created_at: str
    thesis: str
    horizon: str
    selected_goal: dict[str, Any]
    progress_context: dict[str, Any]
    milestones: list[dict[str, Any]]
    risks: list[str]
    success_metrics: list[str]
    next_objective: str
    routed_plan: dict[str, Any] | None = None
    memory_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AutonomousStrategyPlanner:
    """Create long-horizon campaigns from GIZMO's own autonomy signals."""

    def __init__(self, orchestrator: Any) -> None:
        self.orchestrator = orchestrator
        self.store = orchestrator.store
        self.brain = orchestrator.brain_core

    def plan(self, *, horizon: str = "next 3 cycles", route: bool = False, execute: bool = False) -> StrategicCampaign:
        progress = self._latest_or_fresh_progress()
        goal_decision = self._latest_or_fresh_goal(progress)
        selected_goal = goal_decision.get("selected_goal", {})
        thesis = self._thesis(progress, selected_goal, horizon)
        milestones = self._milestones(progress, selected_goal)
        next_objective = milestones[0].objective if milestones else selected_goal.get("objective", "Refresh autonomous situational awareness")
        campaign = StrategicCampaign(
            campaign_id="campaign-" + uuid4().hex[:10],
            created_at=now_iso(),
            thesis=thesis,
            horizon=horizon,
            selected_goal=selected_goal,
            progress_context=self._progress_context(progress),
            milestones=[milestone.to_dict() for milestone in milestones],
            risks=self._risks(progress, selected_goal),
            success_metrics=self._success_metrics(progress, selected_goal),
            next_objective=next_objective,
        )
        campaign.memory_id = self._record_memory(campaign)
        if route:
            campaign.routed_plan = self.orchestrator.universal_route(next_objective, project="Gizmo", execute=execute)
        data = campaign.to_dict()
        self.store.write(data, "strategy", "latest_campaign.json")
        self.store.append_list(data, "strategy", "campaign_history.json")
        return campaign

    def _latest_or_fresh_progress(self) -> dict[str, Any]:
        progress = self.store.read("progress", "latest_progress_evaluation.json", default={})
        if progress:
            return progress
        return self.orchestrator.autonomous_progress_cycle()["progress"]

    def _latest_or_fresh_goal(self, progress: dict[str, Any]) -> dict[str, Any]:
        goal = self.store.read("goals", "latest_goal_decision.json", default={})
        selected = goal.get("selected_goal", {}) if isinstance(goal, dict) else {}
        if selected:
            return goal
        return self.orchestrator.autonomous_goal_cycle()["decision"]

    @staticmethod
    def _progress_context(progress: dict[str, Any]) -> dict[str, Any]:
        return {
            "verdict": progress.get("verdict"),
            "score": progress.get("score"),
            "trend": progress.get("trend"),
            "blockers": list(progress.get("blockers") or [])[:5],
            "strategic_gaps": list(progress.get("strategic_gaps") or [])[:5],
            "next_actions": list(progress.get("next_actions") or [])[:5],
        }

    @staticmethod
    def _thesis(progress: dict[str, Any], selected_goal: dict[str, Any], horizon: str) -> str:
        verdict = progress.get("verdict", "UNKNOWN")
        score = progress.get("score", "unknown")
        goal = selected_goal.get("objective", "refresh autonomous awareness")
        if verdict == "ADVANCING":
            posture = "compound the working autonomy loop"
        elif verdict == "MIXED_PROGRESS":
            posture = "convert mixed signals into durable execution wins"
        else:
            posture = "break the stall by clearing blockers and forcing evidence"
        return f"Over {horizon}, {posture}. Current progress verdict is {verdict} at score {score}; primary goal is: {goal}."

    def _milestones(self, progress: dict[str, Any], selected_goal: dict[str, Any]) -> list[StrategyMilestone]:
        gaps = list(progress.get("strategic_gaps") or [])
        blockers = list(progress.get("blockers") or [])
        goal_objective = selected_goal.get("objective", "Advance selected autonomous goal")
        lane = selected_goal.get("lane", "strategy")
        milestones: list[StrategyMilestone] = []
        if blockers:
            milestones.append(StrategyMilestone(
                id="milestone-" + uuid4().hex[:8],
                objective=f"Clear autonomy blocker: {blockers[0]}",
                lane="blocker-clearance",
                success_criteria=["Blocker no longer appears in autonomous-progress", "universal-health risk is not HIGH"],
                evidence_required=["fresh autonomous-progress output", "fresh universal-health output"],
            ))
        if gaps:
            milestones.append(StrategyMilestone(
                id="milestone-" + uuid4().hex[:8],
                objective=f"Close strategic gap: {gaps[0]}",
                lane="gap-closure",
                success_criteria=["Strategic gap removed or downgraded", "new test or acceptance evidence records the closure"],
                evidence_required=["progress evaluation history", "test or acceptance proof"],
                depends_on=[milestones[-1].id] if milestones else [],
            ))
        milestones.append(StrategyMilestone(
            id="milestone-" + uuid4().hex[:8],
            objective=goal_objective,
            lane=lane,
            success_criteria=["selected goal routed into a universal plan", "outcome evaluation returns SOLVED or NEEDS_REVIEW with clear next actions"],
            evidence_required=["latest goal decision", "universal route or execution record", "outcome evaluation"],
            depends_on=[milestones[-1].id] if milestones else [],
        ))
        milestones.append(StrategyMilestone(
            id="milestone-" + uuid4().hex[:8],
            objective="Re-evaluate autonomous progress and update the next campaign",
            lane="progress-review",
            success_criteria=["autonomous-progress score improves or blockers shrink", "next campaign uses fresh evidence"],
            evidence_required=["progress score", "campaign history entry"],
            depends_on=[milestones[-1].id] if milestones else [],
        ))
        return milestones[:5]

    @staticmethod
    def _risks(progress: dict[str, Any], selected_goal: dict[str, Any]) -> list[str]:
        risks = []
        if progress.get("verdict") == "STALLED":
            risks.append("Autonomy may keep planning without producing solved execution evidence")
        if selected_goal.get("approval_required"):
            risks.append("Selected goal requires explicit approval before side effects")
        if progress.get("trend") == "DECLINING":
            risks.append("Recent cycle output is declining; narrow scope before expansion")
        if not risks:
            risks.append("Strategy can drift if progress is not re-evaluated after each campaign")
        return risks

    @staticmethod
    def _success_metrics(progress: dict[str, Any], selected_goal: dict[str, Any]) -> list[str]:
        baseline = progress.get("score", 0)
        return [
            f"Raise autonomous-progress score above baseline {baseline}",
            "Reduce blocker count from latest progress context",
            "Produce at least one routed universal plan or solved execution outcome",
            "Record campaign memory and follow-up progress evaluation",
            f"Advance selected lane: {selected_goal.get('lane', 'unknown')}",
        ]

    def _record_memory(self, campaign: StrategicCampaign) -> str | None:
        try:
            memory = self.brain.remember(
                BrainMemoryType.GOAL,
                f"Autonomous strategic campaign: {campaign.next_objective[:80]}",
                f"Thesis: {campaign.thesis}\nNext objective: {campaign.next_objective}\nMilestones: {len(campaign.milestones)}\nRisks: {'; '.join(campaign.risks)}\nSuccess metrics: {'; '.join(campaign.success_metrics)}",
                source="autonomous-strategy-planner",
                source_agent="agent-27",
                project="Gizmo",
                importance=9,
                confidence=float(campaign.progress_context.get("score") or 0.7) if isinstance(campaign.progress_context.get("score"), (int, float)) else 0.7,
                tags=["autonomous-strategy", str(campaign.progress_context.get("verdict", "unknown")).lower()],
                entities=["strategy", "campaign", "autonomy"],
                metadata={"campaign": campaign.to_dict()},
            )
            return memory.id
        except Exception:
            return None
