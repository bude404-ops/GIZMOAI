"""Knowledge-to-app factory for GIZMO.

The factory transforms general memories and source opportunities into concrete app
specifications. It does not auto-deploy risky code; it creates verified blueprints
and a safe build queue that can be approved or executed by the app-building lane.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from gizmo.brain.models import BrainMemoryType
from gizmo.core.models import now_iso


@dataclass
class AppBlueprint:
    id: str
    title: str
    domain: str
    app_type: str
    problem: str
    target_user: str
    core_features: list[str]
    data_sources: list[str]
    safety_boundaries: list[str]
    build_steps: list[str]
    source_memory_ids: list[str] = field(default_factory=list)
    confidence: float = 0.65
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AppFactoryReport:
    generated_at: str
    blueprints_created: list[str]
    backlog_size: int
    top_blueprints: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class KnowledgeAppFactory:
    """Creates app blueprints from universal knowledge memories."""

    def __init__(self, brain: Any, store: Any) -> None:
        self.brain = brain
        self.store = store

    def run(self, *, domain: str = "general", limit: int = 6) -> AppFactoryReport:
        opportunities = self.store.read("knowledge", "app_opportunities.json", default=[])
        if domain != "general":
            opportunities = [item for item in opportunities if item.get("domain") == domain]
        if not opportunities:
            opportunities = self._mine_memories(domain=domain, limit=limit)
        blueprints: list[AppBlueprint] = []
        for opportunity in opportunities[:limit]:
            blueprint = self._blueprint_from_opportunity(opportunity)
            blueprints.append(blueprint)
            self.store.write(blueprint.to_dict(), "apps", "blueprints", f"{blueprint.id}.json")
            self.store.append_list(blueprint.to_dict(), "apps", "blueprint_backlog.json")
            memory = self.brain.remember(
                BrainMemoryType.IDEA,
                f"App blueprint: {blueprint.title}",
                self._memory_text(blueprint),
                source="knowledge-app-factory",
                source_agent="agent-26",
                project="Gizmo",
                importance=8,
                confidence=blueprint.confidence,
                tags=["app-factory", "blueprint", blueprint.domain, blueprint.app_type],
                entities=[blueprint.domain, blueprint.title],
                metadata={"blueprint": blueprint.to_dict()},
            )
            blueprint.source_memory_ids.append(memory.id)
        backlog = self.store.read("apps", "blueprint_backlog.json", default=[])
        report = AppFactoryReport(now_iso(), [b.id for b in blueprints], len(backlog), [b.to_dict() for b in blueprints[:5]])
        self.store.write(report.to_dict(), "apps", "latest_factory_report.json")
        self.store.append_list(report.to_dict(), "apps", "factory_history.json")
        return report

    def latest(self) -> dict[str, Any]:
        return self.store.read("apps", "latest_factory_report.json", default={})

    def _mine_memories(self, *, domain: str, limit: int) -> list[dict[str, Any]]:
        query = "app idea tool dashboard decision helper workflow automation"
        if domain != "general":
            query += f" {domain}"
        matches = self.brain.hybrid_search(query, project="Gizmo", limit=limit, include_trace=True)
        opportunities = []
        for trace, memory in matches:
            opportunities.append({
                "domain": domain if domain != "general" else (memory.tags[2] if len(memory.tags) > 2 else "general"),
                "title": f"{memory.title[:42]} App",
                "problem": memory.summary or memory.content[:180],
                "app_type": "knowledge-tool",
                "source_memory_id": memory.id,
                "confidence": min(0.85, max(0.55, trace.score / 5)),
            })
        return opportunities

    @staticmethod
    def _blueprint_from_opportunity(opportunity: dict[str, Any]) -> AppBlueprint:
        domain = opportunity.get("domain", "general")
        title = opportunity.get("title") or f"{domain.title()} App"
        app_type = opportunity.get("app_type", "interactive-tool")
        problem = opportunity.get("problem", f"Help users act on knowledge in {domain}.")
        source_memory = opportunity.get("source_memory_id")
        slug = "app-" + uuid4().hex[:10]
        return AppBlueprint(
            id=slug,
            title=title[:64],
            domain=domain,
            app_type=app_type,
            problem=problem[:400],
            target_user=f"Someone trying to understand or act inside {domain}.",
            core_features=[
                "Ask a goal or paste context",
                "Show a simple decision map",
                "Generate a prioritized checklist",
                "Save reusable lessons to GIZMO memory",
                "Expose evidence and uncertainty clearly",
            ],
            data_sources=["GIZMO Second Brain", "operator-provided text", "public URLs when supplied"],
            safety_boundaries=[
                "public information only",
                "no secrets stored",
                "no medical/legal/financial guarantees",
                "human approval before external side effects",
            ],
            build_steps=[
                "retrieve relevant memories",
                "generate minimal mobile interface",
                "add input parser and checklist generator",
                "test at mobile width",
                "publish as Mini App or queue Server App only if persistent shared state is required",
            ],
            source_memory_ids=[source_memory] if source_memory else [],
            confidence=float(opportunity.get("confidence", 0.65)),
        )

    @staticmethod
    def _memory_text(blueprint: AppBlueprint) -> str:
        return (
            f"Title: {blueprint.title}\nDomain: {blueprint.domain}\nProblem: {blueprint.problem}\n"
            f"Features: {', '.join(blueprint.core_features)}\n"
            f"Build steps: {', '.join(blueprint.build_steps)}\n"
            f"Boundaries: {', '.join(blueprint.safety_boundaries)}"
        )
