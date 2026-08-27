"""Universal task router for GIZMO's general-purpose autonomous worker."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any

from gizmo.brain.models import BrainMemoryType
from gizmo.capabilities.registry import CapabilityRecord, CapabilityRegistry
from gizmo.core.models import Task, now_iso
from gizmo.core.store import JsonStore


CATEGORY_PATTERNS: list[tuple[str, list[str]]] = [
    ("ai_generation", ["generate image", "make an image", "video", "audio", "voice", "3d asset", "character", "cinematic", "trailer", "animation"]),
    ("unreal_engine", ["unreal", "blueprint", "third-person", "level", "enemy", "game prototype", "playable build"]),
    ("software_development", ["general-purpose autonomous worker", "capability registry", "software project", "architecture", "build an app", "build me an app", "saas", "api", "frontend", "backend", "database", "fix this project", "debug", "broken", "code", "implement", "tests"]),
    ("github", ["github", "pull request", "branch", "commit", "repo", "repository", "ci", "workflow"]),
    ("web_research", ["latest", "research", "find out", "current", "documentation", "docs", "compare sources", "competitors"]),
    ("business_analysis", ["would people pay", "business model", "market", "competitor", "make money", "pricing", "customers"]),
    ("data_analysis", ["analyze data", "dataset", "csv", "spreadsheet", "statistics", "chart"]),
    ("system_administration", ["install", "configure", "server", "process", "port", "environment", "dependency"]),
    ("trading", ["token", "buy", "sell", "mcap", "wallet", "solana", "holders", "liquidity", "limit order"]),
    ("project_management", ["continue", "where we left", "project plan", "milestone", "roadmap"]),
    ("question_answer", ["how does", "what is", "why", "explain", "teach"]),
]

DANGEROUS_WORDS = {"delete", "drop database", "wipe", "force push", "production", "deploy", "publish", "buy", "sell", "transfer", "secret", "credential"}


@dataclass
class TaskClassification:
    category: str
    effort: str
    needs_research: bool
    needs_memory: bool
    needs_code: bool
    needs_external_software: bool
    needs_existing_project: bool
    needs_approval: bool
    confidence: float
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskStep:
    order: int
    name: str
    assigned_agent: str
    capability: str
    objective: str
    verification: str
    status: str = "PLANNED"
    task_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class UniversalTaskPlan:
    request_id: str
    objective: str
    classification: dict[str, Any]
    capabilities: list[dict[str, Any]]
    context_memory_ids: list[str]
    decomposition: list[dict[str, Any]]
    selected_tools: list[str]
    selected_agents: list[str]
    permission_mode: str
    approval_required: bool
    verification_plan: list[str]
    memory_plan: list[str]
    project_record_id: str | None = None
    execution_task_ids: list[str] = field(default_factory=list)
    status: str = "PLANNED"
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class UniversalTaskRouter:
    def __init__(self, orchestrator: Any, store: JsonStore | None = None) -> None:
        self.orchestrator = orchestrator
        self.store = store or orchestrator.store
        self.brain = orchestrator.brain_core
        self.registry = CapabilityRegistry(self.store)

    def route(self, request: str, *, creator: str = "Creator", project: str = "Gizmo", execute: bool = False) -> UniversalTaskPlan:
        objective = " ".join((request or "").split())
        classification = self.classify(objective)
        capabilities = self.registry.match(classification.category, objective)
        memories = self.brain.hybrid_search(objective, project=project, limit=6) if classification.needs_memory else []
        project_memory_id = self._maybe_record_project(objective, classification, project)
        steps = self.decompose(objective, classification, capabilities)
        selected_tools = sorted({tool for cap in capabilities for tool in cap.tools})
        selected_agents = sorted({agent for cap in capabilities for agent in cap.agents})
        permission_mode = self._permission_mode(classification, capabilities)
        verification = self._verification_plan(classification, capabilities)
        memory_plan = self._memory_plan(classification)
        execution_task_ids: list[str] = []
        if execute and not (classification.needs_approval or self._permission_mode(classification, capabilities) == "APPROVAL_REQUIRED"):
            execution_task_ids = self._create_tasks(project, objective, steps)
            for step, task_id in zip(steps, execution_task_ids):
                step.status = "QUEUED"
                step.task_id = task_id
        plan = UniversalTaskPlan(
            request_id=f"universal-{now_iso().replace(':', '').replace('.', '').replace('-', '')}",
            objective=objective,
            classification=classification.to_dict(),
            capabilities=[cap.to_dict() for cap in capabilities],
            context_memory_ids=[m.id for m in memories],
            decomposition=[step.to_dict() for step in steps],
            selected_tools=selected_tools,
            selected_agents=selected_agents,
            permission_mode=permission_mode,
            approval_required=classification.needs_approval or permission_mode == "APPROVAL_REQUIRED",
            verification_plan=verification,
            memory_plan=memory_plan,
            project_record_id=project_memory_id,
            execution_task_ids=execution_task_ids,
            status="QUEUED" if execute else "PLANNED",
        )
        self.store.write(plan.to_dict(), "universal", "latest_plan.json")
        self.store.write(plan.to_dict(), "universal", "plans", f"{plan.request_id}.json")
        self.store.append_list(plan.to_dict(), "universal", "plan_history.json")
        self._remember_plan(plan, creator, project)
        return plan

    def classify(self, request: str) -> TaskClassification:
        lowered = request.lower()
        category = "question_answer"
        best = 0
        for candidate, patterns in CATEGORY_PATTERNS:
            score = sum(1 for pattern in patterns if pattern in lowered)
            if score > best:
                best = score
                category = candidate
        needs_research = any(word in lowered for word in ["latest", "research", "current", "competitor", "documentation", "docs", "find out", "figure out", "unknown", "people pay", "market"])
        needs_code = category in {"software_development", "github", "unreal_engine", "system_administration", "data_analysis"} or any(word in lowered for word in ["build", "code", "fix", "debug", "app", "script", "automation"])
        needs_external = category in {"web_research", "github", "unreal_engine", "ai_generation", "system_administration"} or needs_research
        needs_existing_project = any(word in lowered for word in ["this project", "existing", "repo", "repository", "continue", "broken", "unreal project"])
        dangerous = any(word in lowered for word in DANGEROUS_WORDS)
        effort = "simple"
        if needs_code or needs_research:
            effort = "standard"
        if category in {"software_development", "unreal_engine", "ai_generation"} and any(word in lowered for word in ["complete", "saas", "game", "deploy", "pipeline"]):
            effort = "project"
        rationale = f"Matched {category} from request terms; effort={effort}; research={needs_research}; code={needs_code}."
        return TaskClassification(
            category=category,
            effort=effort,
            needs_research=needs_research,
            needs_memory=True,
            needs_code=needs_code,
            needs_external_software=needs_external,
            needs_existing_project=needs_existing_project,
            needs_approval=dangerous,
            confidence=0.9 if best else 0.62,
            rationale=rationale,
        )

    def decompose(self, objective: str, classification: TaskClassification, capabilities: list[CapabilityRecord]) -> list[TaskStep]:
        primary = capabilities[0]
        steps: list[TaskStep] = []
        def add(name: str, agent: str, cap: str, detail: str, verify: str) -> None:
            steps.append(TaskStep(len(steps) + 1, name, agent, cap, detail, verify))
        add("Understand request", "agent-01", primary.name, f"Clarify objective and constraints for: {objective}", "requirements or answer scope recorded")
        if classification.needs_memory:
            add("Retrieve memory", "agent-26", "question_answer", "Pull only relevant project, procedure, decision, and lesson memories.", "retrieval trace lists memory ids")
        if classification.needs_research or classification.category in {"web_research", "business_analysis"}:
            add("Research", "agent-02", "web_research", "Search, collect, filter, read, cross-check, cite, and capture uncertainty.", "citations and source quality records exist")
        if classification.needs_existing_project:
            add("Inspect existing project", "agent-10", "github", "Inspect repository/project files, issues, build system, and current state.", "file/project evidence recorded")
        if classification.category == "software_development":
            if any(word in objective.lower() for word in ["broken", "debug", "fix", "failure", "error"]):
                add("Reproduce failure", "agent-11", "software_development", "Reproduce the bug or failing behavior against the actual project before changing code.", "reproduction output or explicit blocker recorded")
                add("Identify root cause", "agent-24", "software_development", "Trace the failure to a specific cause, dependency, configuration, or code path.", "root cause note links evidence to proposed fix")
            add("Architect and build", "agent-06", "software_development", "Create real code, data model, tests, docs, and local verification.", "files, tests, and build output exist")
        elif classification.category == "unreal_engine":
            add("Unreal automation", "agent-05", "unreal_engine", "Use Unreal automation bridge/scripts when available; otherwise create verifiable Unreal project artifacts and bridge requirements.", "Unreal files/scripts/build logs or bridge blocker recorded")
        elif classification.category == "ai_generation":
            add("Generation routing", "agent-13", "ai_generation", "Select modality/provider abstraction and record request, model, license, cost, and result artifact.", "asset manifest exists")
        elif classification.category == "data_analysis":
            add("Analyze data", "agent-20", "data_analysis", "Run reproducible analysis and produce structured outputs.", "script/query output exists")
        elif classification.category == "trading":
            add("Trading analysis", "agent-20", "trading", "Use Print World token data as one tool path; require approval for trades or fund movement.", "market data and risk notes recorded")
        add("Verify", "agent-27", primary.name, "Check output against the original request; reject fake completion.", primary.verification_method)
        add("Remember", "agent-26", "question_answer", "Store useful facts, procedures, decisions, failures, and project state selectively with provenance.", "Memory Vault contains selective record")
        return steps

    def _permission_mode(self, classification: TaskClassification, capabilities: list[CapabilityRecord]) -> str:
        if classification.needs_approval or any(cap.dangerous_actions for cap in capabilities if cap.name in {"trading", "github", "software_development", "unreal_engine"} and classification.category == cap.name and any(word in classification.rationale.lower() for word in ["deploy", "production"])):
            return "APPROVAL_REQUIRED"
        if any(cap.mode == "DISABLED" for cap in capabilities):
            return "DISABLED"
        return "AUTO"

    def _verification_plan(self, classification: TaskClassification, capabilities: list[CapabilityRecord]) -> list[str]:
        checks = ["Original request restated and matched to result", "Relevant memory retrieval trace recorded"]
        if classification.needs_research:
            checks += ["At least two sources considered when available", "Facts/inferences/hypotheses/uncertainties separated", "Citations retained with source quality"]
        if classification.needs_code:
            checks += ["Files changed or project artifacts exist", "Tests/build/lint or equivalent command output recorded", "Failure path captured if blocked"]
        if classification.category == "unreal_engine":
            checks.append("Real Unreal bridge/project evidence required; no pretending text equals editor control")
        if classification.category == "ai_generation":
            checks.append("Generation manifest tracks provider/model/result/cost/license")
        checks += [cap.verification_method for cap in capabilities[:3]]
        return list(dict.fromkeys(checks))

    def _memory_plan(self, classification: TaskClassification) -> list[str]:
        plan = ["Store only useful knowledge", "Record source/provenance/confidence", "Link to project/entity when relevant"]
        if classification.needs_code:
            plan += ["Record project state, files, technologies, tests, failures, fixes, and decisions"]
        if classification.needs_research:
            plan += ["Store source documents and confirmed facts separately from inferences and uncertainty"]
        return plan

    def _maybe_record_project(self, objective: str, classification: TaskClassification, project: str) -> str | None:
        if classification.effort != "project" and not classification.needs_existing_project:
            return None
        memory = self.brain.remember(
            BrainMemoryType.PROJECT_STATE,
            f"Project mode: {objective[:70]}",
            f"GIZMO entered project-aware routing for: {objective}\nCategory: {classification.category}\nNeeds existing project: {classification.needs_existing_project}",
            source="universal-router",
            source_agent="agent-01",
            project=project,
            importance=8,
            confidence=0.86,
            tags=["project-mode", classification.category],
            metadata={"classification": classification.to_dict()},
        )
        return memory.id

    def _remember_plan(self, plan: UniversalTaskPlan, creator: str, project: str) -> None:
        self.brain.remember(
            BrainMemoryType.PROCEDURE,
            f"Universal route: {plan.classification['category']}",
            f"Creator request: {plan.objective}\nClassification: {plan.classification}\nCapabilities: {[c['name'] for c in plan.capabilities]}\nVerification: {plan.verification_plan}\nMemory plan: {plan.memory_plan}",
            source="creator-request",
            source_agent="agent-01",
            project=project,
            importance=7,
            confidence=plan.classification.get("confidence", 0.7),
            tags=["universal-router", plan.classification["category"], "creator-request"],
            entities=[creator, "GizmoAI"],
            metadata={"request_id": plan.request_id, "permission_mode": plan.permission_mode},
        )

    def _create_tasks(self, project: str, objective: str, steps: list[TaskStep]) -> list[str]:
        ids: list[str] = []
        for step in steps:
            task = Task(project=project, objective=f"{step.name}: {step.objective}", assigned_agent=step.assigned_agent, priority=min(9, step.order), dependencies=ids[-1:])
            task.record("universal_router", f"Planned by universal router for objective: {objective}", capability=step.capability, verification=step.verification)
            self.orchestrator.tasks.create_task(task)
            ids.append(task.id)
        return ids
