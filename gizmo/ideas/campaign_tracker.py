"""Autonomous strategic campaign tracking for GIZMO.

The strategy planner creates campaigns. This tracker judges whether each
milestone has enough evidence to advance, identifies blocked work, and records
campaign progress back into memory and the goal loop.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from gizmo.brain.models import BrainMemoryType
from gizmo.core.models import now_iso


@dataclass
class MilestoneAssessment:
    milestone_id: str
    objective: str
    lane: str
    previous_status: str
    status: str
    verdict: str
    confidence: float
    evidence_found: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CampaignTrackingReport:
    tracking_id: str
    campaign_id: str
    tracked_at: str
    verdict: str
    score: float
    completed: int
    blocked: int
    planned: int
    active_milestone: dict[str, Any] | None
    assessments: list[dict[str, Any]]
    next_objective: str
    next_actions: list[str]
    memory_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AutonomousCampaignTracker:
    """Track campaign milestones against current GIZMO evidence."""

    def __init__(self, orchestrator: Any) -> None:
        self.orchestrator = orchestrator
        self.store = orchestrator.store
        self.brain = orchestrator.brain_core

    def track(self, *, campaign_id: str | None = None, route: bool = False, execute: bool = False) -> CampaignTrackingReport:
        campaign = self._load_campaign(campaign_id)
        if not campaign:
            campaign = self.orchestrator.autonomous_strategy_cycle(route=False)["campaign"]
        evidence = self._collect_evidence()
        assessments = [self._assess_milestone(milestone, evidence) for milestone in campaign.get("milestones", [])]
        updated_milestones = self._merge_statuses(campaign.get("milestones", []), assessments)
        campaign["milestones"] = updated_milestones
        active = self._active_milestone(updated_milestones)
        score = self._score(assessments)
        verdict = self._verdict(assessments, score)
        next_objective = self._next_objective(active, verdict, campaign)
        report = CampaignTrackingReport(
            tracking_id="tracking-" + uuid4().hex[:10],
            campaign_id=campaign.get("campaign_id", "campaign-unknown"),
            tracked_at=now_iso(),
            verdict=verdict,
            score=score,
            completed=sum(1 for item in assessments if item.status == "COMPLETED"),
            blocked=sum(1 for item in assessments if item.status == "BLOCKED"),
            planned=sum(1 for item in assessments if item.status in {"PLANNED", "IN_PROGRESS"}),
            active_milestone=active,
            assessments=[item.to_dict() for item in assessments],
            next_objective=next_objective,
            next_actions=self._next_actions(verdict, active, campaign),
        )
        report.memory_id = self._record_memory(report)
        campaign["tracking"] = report.to_dict()
        campaign["next_objective"] = next_objective
        if route:
            campaign["tracking"]["routed_plan"] = self.orchestrator.universal_route(next_objective, project="Gizmo", execute=execute)
        self.store.write(campaign, "strategy", "latest_campaign.json")
        self.store.append_list(campaign, "strategy", "campaign_history.json")
        data = report.to_dict()
        self.store.write(data, "strategy", "latest_tracking.json")
        self.store.append_list(data, "strategy", "tracking_history.json")
        return report

    def _load_campaign(self, campaign_id: str | None) -> dict[str, Any]:
        latest = self.store.read("strategy", "latest_campaign.json", default={})
        if not campaign_id or latest.get("campaign_id") == campaign_id:
            return latest
        for item in reversed(self.store.read("strategy", "campaign_history.json", default=[])):
            if item.get("campaign_id") == campaign_id:
                return item
        return {}

    def _collect_evidence(self) -> dict[str, Any]:
        return {
            "health": self.orchestrator.universal_health_report(stale_after_minutes=60),
            "progress": self.store.read("progress", "latest_progress_evaluation.json", default={}),
            "goal": self.store.read("goals", "latest_goal_decision.json", default={}),
            "outcome": self.store.read("universal", "latest_outcome_evaluation.json", default={}),
            "route": self.store.read("universal", "route_latest_result.json", default={}),
            "run": self.store.read("universal", "latest_run_result.json", default={}),
            "learning": self.store.read("learning", "latest_failure_learning.json", default={}),
        }

    def _assess_milestone(self, milestone: dict[str, Any], evidence: dict[str, Any]) -> MilestoneAssessment:
        required = list(milestone.get("evidence_required") or [])
        found: list[str] = []
        missing: list[str] = []
        for item in required:
            if self._evidence_present(item, evidence):
                found.append(item)
            else:
                missing.append(item)
        previous = milestone.get("status", "PLANNED")
        dependency_blocked = bool(milestone.get("depends_on")) and previous == "PLANNED"
        if required and not missing and not dependency_blocked:
            status = "COMPLETED"
            verdict = "EVIDENCE_SATISFIED"
            next_action = "Advance to the next campaign milestone"
            confidence = 0.88
        elif dependency_blocked:
            status = "PLANNED"
            verdict = "WAITING_DEPENDENCY"
            next_action = "Complete prerequisite milestone first"
            confidence = 0.72
        elif found:
            status = "IN_PROGRESS"
            verdict = "PARTIAL_EVIDENCE"
            next_action = f"Collect missing evidence: {missing[0] if missing else 'fresh verification'}"
            confidence = 0.68
        else:
            status = "BLOCKED" if previous == "IN_PROGRESS" else "PLANNED"
            verdict = "NO_EVIDENCE"
            next_action = f"Produce first evidence for: {milestone.get('objective', 'milestone')}"
            confidence = 0.6
        return MilestoneAssessment(
            milestone_id=milestone.get("id", "milestone-unknown"),
            objective=milestone.get("objective", "Unknown milestone"),
            lane=milestone.get("lane", "strategy"),
            previous_status=previous,
            status=status,
            verdict=verdict,
            confidence=confidence,
            evidence_found=found,
            missing_evidence=missing,
            next_action=next_action,
        )

    @staticmethod
    def _evidence_present(requirement: str, evidence: dict[str, Any]) -> bool:
        lowered = requirement.lower()
        health = evidence.get("health") or {}
        progress = evidence.get("progress") or {}
        outcome = evidence.get("outcome") or {}
        route = evidence.get("route") or {}
        run = evidence.get("run") or {}
        learning = evidence.get("learning") or {}
        goal = evidence.get("goal") or {}
        if "health" in lowered:
            return bool(health) and health.get("risk") != "HIGH"
        if "progress" in lowered or "score" in lowered:
            return bool(progress) and progress.get("score") is not None
        if "goal" in lowered:
            return bool(goal.get("selected_goal"))
        if "route" in lowered or "universal plan" in lowered:
            return bool(route.get("plan"))
        if "execution" in lowered or "outcome" in lowered:
            return bool(run.get("execution")) or outcome.get("verdict") in {"SOLVED", "NEEDS_REVIEW"}
        if "test" in lowered or "acceptance" in lowered:
            return bool(outcome.get("verification")) or bool(learning.get("lessons"))
        if "campaign history" in lowered:
            return True
        return bool(progress or goal or route or outcome or learning)

    @staticmethod
    def _merge_statuses(milestones: list[dict[str, Any]], assessments: list[MilestoneAssessment]) -> list[dict[str, Any]]:
        by_id = {item.milestone_id: item for item in assessments}
        merged: list[dict[str, Any]] = []
        for milestone in milestones:
            item = dict(milestone)
            assessment = by_id.get(item.get("id"))
            if assessment:
                item["status"] = assessment.status
                item["last_verdict"] = assessment.verdict
                item["last_tracked_at"] = now_iso()
            merged.append(item)
        return merged

    @staticmethod
    def _active_milestone(milestones: list[dict[str, Any]]) -> dict[str, Any] | None:
        for milestone in milestones:
            if milestone.get("status") in {"PLANNED", "IN_PROGRESS", "BLOCKED"}:
                return milestone
        return milestones[-1] if milestones else None

    @staticmethod
    def _score(assessments: list[MilestoneAssessment]) -> float:
        if not assessments:
            return 0.0
        points = 0.0
        for item in assessments:
            if item.status == "COMPLETED":
                points += 1.0
            elif item.status == "IN_PROGRESS":
                points += 0.55
            elif item.status == "PLANNED":
                points += 0.25
            elif item.status == "BLOCKED":
                points += 0.05
        return round(points / len(assessments), 3)

    @staticmethod
    def _verdict(assessments: list[MilestoneAssessment], score: float) -> str:
        if not assessments:
            return "NO_CAMPAIGN"
        if all(item.status == "COMPLETED" for item in assessments):
            return "CAMPAIGN_COMPLETE"
        if any(item.status == "BLOCKED" for item in assessments) and score < 0.45:
            return "BLOCKED"
        if score >= 0.65:
            return "ADVANCING"
        return "NEEDS_EVIDENCE"

    @staticmethod
    def _next_objective(active: dict[str, Any] | None, verdict: str, campaign: dict[str, Any]) -> str:
        if verdict == "CAMPAIGN_COMPLETE":
            return "Re-evaluate autonomous progress and design the next strategic campaign"
        if active:
            return str(active.get("objective", campaign.get("next_objective", "Continue active campaign")))
        return str(campaign.get("next_objective", "Continue active campaign"))

    @staticmethod
    def _next_actions(verdict: str, active: dict[str, Any] | None, campaign: dict[str, Any]) -> list[str]:
        actions = []
        if active:
            actions.append(f"Work active milestone: {active.get('objective')}")
        if verdict in {"BLOCKED", "NEEDS_EVIDENCE"}:
            actions.append("Route the active milestone and produce missing evidence")
        if verdict == "CAMPAIGN_COMPLETE":
            actions.append("Run autonomous-progress, then autonomous-strategy for the next campaign")
        actions.append("Run autonomous-track-campaign after the next execution or progress cycle")
        return actions[:4]

    def _record_memory(self, report: CampaignTrackingReport) -> str | None:
        try:
            memory = self.brain.remember(
                BrainMemoryType.EVALUATION,
                f"Campaign tracking verdict: {report.verdict}",
                f"Campaign {report.campaign_id} tracked at score {report.score}. Verdict: {report.verdict}. Completed: {report.completed}; blocked: {report.blocked}; planned: {report.planned}. Next objective: {report.next_objective}.",
                source="autonomous-campaign-tracker",
                source_agent="agent-27",
                project="Gizmo",
                importance=8 if report.verdict in {"BLOCKED", "NEEDS_EVIDENCE"} else 7,
                confidence=max(0.5, report.score),
                tags=["autonomous-strategy", "campaign-tracking", report.verdict.lower()],
                entities=["strategy", "campaign", report.campaign_id],
                metadata={"tracking": report.to_dict()},
            )
            return memory.id
        except Exception:
            return None
