"""Autonomous ideation and self-upgrade thinking for GIZMO.

This module lets GIZMO inspect its own memory, gaps, body scorecard, app backlog,
and recent cycle state, then generate ranked ideas and upgrade proposals without
waiting for the operator to name every next step.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from gizmo.ai.reasoning import ModelReasoner
from gizmo.brain.models import BrainMemoryType
from gizmo.core.models import now_iso


@dataclass
class AutonomousIdea:
    id: str
    title: str
    category: str
    reason: str
    expected_value: float
    effort: float
    risk: float
    score: float
    next_step: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class UpgradeProposal:
    id: str
    title: str
    problem: str
    proposed_change: str
    safety_level: str
    approval_required: bool
    score: float
    source_idea_id: str
    build_queue_item: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ThinkingReport:
    generated_at: str
    cycle_id: str
    questions_asked: list[str]
    ideas: list[dict[str, Any]]
    upgrades: list[dict[str, Any]]
    chosen_next: list[dict[str, Any]]
    memories_created: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AutonomousThinker:
    """Self-reflective ideation loop used by the Super Brain."""

    QUESTIONS = [
        "What knowledge would make GIZMO more useful across all domains?",
        "What app could GIZMO create from the patterns it already knows?",
        "What repeated failure or low-confidence area should be upgraded next?",
        "What operator friction should be removed from Telegram or dashboards?",
        "What safe autonomous action can be attempted without external side effects?",
    ]

    def __init__(self, brain: Any, store: Any, *, reasoner: ModelReasoner | None = None) -> None:
        self.brain = brain
        self.store = store
        self.reasoner = reasoner or ModelReasoner()

    def think(self, *, cycle_id: str = "manual", topics: list[str] | None = None, limit: int = 8) -> ThinkingReport:
        context = self._collect_context(topics or [])
        ideas = self._generate_ideas(context, limit=limit)
        upgrades = [self._upgrade_from_idea(idea) for idea in ideas if idea.category in {"upgrade", "automation", "app"}]
        chosen = sorted([idea.to_dict() for idea in ideas], key=lambda item: item["score"], reverse=True)[:3]
        memory_ids: list[str] = []
        for idea in ideas[:limit]:
            memory = self.brain.remember(
                BrainMemoryType.IDEA,
                f"Autonomous idea: {idea.title}",
                self._idea_memory_text(idea),
                source="autonomous-thinker",
                source_agent="agent-26",
                project="Gizmo",
                importance=8 if idea.score >= 0.7 else 6,
                confidence=max(0.55, min(0.93, idea.score)),
                tags=["autonomous-thinking", "self-generated", idea.category],
                entities=[idea.category, idea.title],
                metadata={"idea": idea.to_dict(), "cycle_id": cycle_id},
            )
            memory_ids.append(memory.id)
        for proposal in upgrades[:5]:
            self.store.append_list(proposal.to_dict() | {"created_at": now_iso()}, "ideas", "upgrade_queue.json")
        for idea in chosen:
            self.store.append_list({"created_at": now_iso(), **idea}, "ideas", "chosen_next.json")
        report = ThinkingReport(now_iso(), cycle_id, self.QUESTIONS, [i.to_dict() for i in ideas], [u.to_dict() for u in upgrades], chosen, memory_ids)
        self.store.write(report.to_dict(), "ideas", "latest_thinking.json")
        self.store.append_list(report.to_dict(), "ideas", "thinking_history.json")
        return report

    def latest(self) -> dict[str, Any]:
        return self.store.read("ideas", "latest_thinking.json", default={})

    def _collect_context(self, topics: list[str]) -> dict[str, Any]:
        app_backlog = self.store.read("apps", "blueprint_backlog.json", default=[])
        body_scorecard = self.store.read("body", "scorecard.json", default={})
        last_cloud = self.store.read("cloud", "brain_latest.json", default={})
        next_queue = self.store.read("body", "next_queue.json", default=[])
        searches = []
        for query in (topics[:4] or ["app ideas", "self improvement", "automation", "knowledge gaps"]):
            matches = self.brain.hybrid_search(query, project="Gizmo", limit=3, include_trace=True)
            searches.append({
                "query": query,
                "matches": [getattr(memory, "title", "unknown") for _, memory in matches],
                "top_score": matches[0][0].score if matches else 0,
            })
        return {"topics": topics, "app_backlog": app_backlog[-12:], "body_scorecard": body_scorecard, "last_cloud": last_cloud, "next_queue": next_queue[-12:], "searches": searches}

    def _generate_ideas(self, context: dict[str, Any], *, limit: int) -> list[AutonomousIdea]:
        seeds: list[dict[str, Any]] = []
        backlog = context.get("app_backlog") or []
        for item in backlog[-4:]:
            seeds.append({"category": "app", "title": f"Build {item.get('title', 'knowledge app')}", "reason": item.get("problem", "Backlog app idea has enough structure to become a Mini App."), "evidence": [item.get("id", "backlog")], "value": 0.82, "effort": 0.48, "risk": 0.2})
        for row in context.get("searches", []):
            if row.get("top_score", 0) < 2:
                seeds.append({"category": "knowledge", "title": f"Deepen knowledge on {row.get('query')}", "reason": "Memory search shows a weak evidence base; learning more improves future app creation.", "evidence": row.get("matches", []), "value": 0.68, "effort": 0.34, "risk": 0.08})
            else:
                seeds.append({"category": "automation", "title": f"Automate next step for {row.get('query')}", "reason": "Existing memory is strong enough to convert into a repeated workflow.", "evidence": row.get("matches", []), "value": 0.74, "effort": 0.42, "risk": 0.18})
        scorecard = context.get("body_scorecard") or {}
        if scorecard.get("actions", 0) > 0:
            seeds.append({"category": "upgrade", "title": "Add agent performance review before every build", "reason": "Body actions are now scored; low-scoring lanes should trigger upgrades instead of repeating weak work.", "evidence": ["body-scorecard"], "value": 0.78, "effort": 0.36, "risk": 0.12})
        next_queue = context.get("next_queue") or []
        if next_queue:
            seeds.append({"category": "upgrade", "title": "Turn next-action queue into ranked execution queue", "reason": "The body already creates next actions; ranking them gives GIZMO a stronger sense of what to do without being told.", "evidence": [item.get("objective", "queued action") for item in next_queue[-3:]], "value": 0.86, "effort": 0.4, "risk": 0.15})
        seeds.append({"category": "upgrade", "title": "Ask five self-improvement questions every cloud cycle", "reason": "Persistent self-questioning makes GIZMO generate ideas and upgrades before the operator asks.", "evidence": self.QUESTIONS[:2], "value": 0.9, "effort": 0.28, "risk": 0.08})
        ideas = [self._idea_from_seed(seed) for seed in seeds]
        ideas.sort(key=lambda idea: idea.score, reverse=True)
        return ideas[:limit]

    def _idea_from_seed(self, seed: dict[str, Any]) -> AutonomousIdea:
        value = float(seed.get("value", 0.6))
        effort = float(seed.get("effort", 0.5))
        risk = float(seed.get("risk", 0.2))
        score = round(max(0.05, min(1.0, value - effort * 0.22 - risk * 0.35)), 3)
        title = str(seed.get("title", "Untitled idea"))[:80]
        return AutonomousIdea(
            id="idea-" + uuid4().hex[:10],
            title=title,
            category=str(seed.get("category", "idea")),
            reason=str(seed.get("reason", "GIZMO generated this from its current memory state."))[:600],
            expected_value=round(value, 3),
            effort=round(effort, 3),
            risk=round(risk, 3),
            score=score,
            next_step=self._next_step(str(seed.get("category", "idea")), title),
            evidence=[str(item)[:140] for item in seed.get("evidence", []) if item],
        )

    def _upgrade_from_idea(self, idea: AutonomousIdea) -> UpgradeProposal:
        approval = idea.risk >= 0.35
        return UpgradeProposal(
            id="upgrade-" + uuid4().hex[:10],
            title=f"Upgrade: {idea.title}"[:90],
            problem=idea.reason[:500],
            proposed_change=idea.next_step,
            safety_level="approval-required" if approval else "safe-autonomous",
            approval_required=approval,
            score=idea.score,
            source_idea_id=idea.id,
            build_queue_item=f"Implement or prototype: {idea.next_step}",
        )

    @staticmethod
    def _next_step(category: str, title: str) -> str:
        if category == "app":
            return f"Create a minimal app spec for {title}, then queue a Mini App build if it requires no backend."
        if category == "knowledge":
            return f"Collect more public knowledge for {title} and rebuild semantic memory."
        if category == "automation":
            return f"Convert {title} into a safe repeatable workflow with tests."
        return f"Prototype {title} behind tests and keep external side effects approval-gated."

    @staticmethod
    def _idea_memory_text(idea: AutonomousIdea) -> str:
        return (
            f"Idea: {idea.title}\nCategory: {idea.category}\nReason: {idea.reason}\n"
            f"Score: {idea.score}\nValue: {idea.expected_value}\nEffort: {idea.effort}\nRisk: {idea.risk}\n"
            f"Next step: {idea.next_step}\nEvidence: {', '.join(idea.evidence)}"
        )
