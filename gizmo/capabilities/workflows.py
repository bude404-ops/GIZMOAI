"""General-purpose autonomous workflow library for GIZMO."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from gizmo.core.models import now_iso
from gizmo.core.store import JsonStore


@dataclass
class WorkflowTemplate:
    name: str
    trigger_categories: list[str]
    phases: list[str]
    default_agents: list[str]
    required_evidence: list[str]
    memory_outputs: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


WORKFLOWS: list[WorkflowTemplate] = [
    WorkflowTemplate(
        "question_answer_mode",
        ["question_answer"],
        ["classify freshness", "retrieve relevant memory", "research only if needed", "answer directly", "record useful lesson only if new"],
        ["agent-02", "agent-27"],
        ["confidence", "source citations when researched"],
        ["facts", "lessons"],
    ),
    WorkflowTemplate(
        "autonomous_research_mode",
        ["web_research", "business_analysis"],
        ["search", "collect", "filter", "read", "cross-check", "synthesize", "cite", "store useful knowledge"],
        ["agent-02", "agent-20", "agent-21", "agent-22", "agent-23", "agent-27"],
        ["sources", "fact/source/inference/hypothesis/uncertainty split", "source quality", "conflict notes"],
        ["source documents", "facts", "discoveries", "warnings"],
    ),
    WorkflowTemplate(
        "project_mode",
        ["software_development", "github", "unreal_engine", "ai_generation"],
        ["discover", "requirements", "research", "architecture", "plan", "build", "test", "debug", "deploy or package", "monitor", "improve"],
        ["agent-01", "agent-03", "agent-06", "agent-07", "agent-08", "agent-09", "agent-10", "agent-11", "agent-12", "agent-23", "agent-27"],
        ["project record", "files", "commands", "test/build output", "review result"],
        ["project state", "decisions", "procedures", "failures", "successful strategies"],
    ),
    WorkflowTemplate(
        "debugging_mode",
        ["software_development", "github", "system_administration"],
        ["reproduce", "identify root cause", "research if needed", "propose fix", "implement", "test", "verify", "store fix"],
        ["agent-10", "agent-11", "agent-12", "agent-24", "agent-27"],
        ["reproduction evidence", "root cause", "diff", "passing verification"],
        ["failures", "procedures", "lessons"],
    ),
    WorkflowTemplate(
        "unreal_engine_mode",
        ["unreal_engine", "game development"],
        ["inspect project", "detect bridge", "plan gameplay/assets", "generate C++/Python/Blueprint-support files", "run editor/build automation", "inspect logs", "iterate", "package proof"],
        ["agent-04", "agent-05", "agent-14", "agent-15", "agent-16", "agent-17", "agent-27"],
        ["Unreal project files", "automation bridge status", "generated scripts", "build/test logs or explicit blocker"],
        ["project state", "asset relationships", "failures", "procedures"],
    ),
    WorkflowTemplate(
        "ai_generation_mode",
        ["ai_generation"],
        ["determine modality", "select provider", "submit generation", "record model/request/result/cost/license", "quality review", "move to project pipeline"],
        ["agent-13", "agent-14", "agent-15", "agent-16", "agent-17", "agent-18", "agent-19", "agent-27"],
        ["generation manifest", "asset artifact", "license/use notes", "quality score"],
        ["entities", "source documents", "project assets", "decisions"],
    ),
    WorkflowTemplate(
        "unknown_problem_mode",
        ["question_answer", "web_research", "software_development", "unreal_engine", "system_administration"],
        ["identify unknown", "search docs", "search examples", "inspect environment", "generate options", "test safest option", "try alternative", "record successful solution"],
        ["agent-02", "agent-09", "agent-11", "agent-26", "agent-27"],
        ["unknown stated", "sources/examples", "tested option output", "final confidence"],
        ["procedures", "lessons", "failures", "successful strategies"],
    ),
]


class WorkflowLibrary:
    def __init__(self, store: JsonStore) -> None:
        self.store = store
        self.persist()

    def persist(self) -> None:
        self.store.write({"generated_at": now_iso(), "workflows": [w.to_dict() for w in WORKFLOWS]}, "capabilities", "workflows.json")

    def select(self, category: str) -> list[WorkflowTemplate]:
        selected = [workflow for workflow in WORKFLOWS if category in workflow.trigger_categories]
        if not selected and category in {"game development", "Unreal Engine"}:
            selected = [workflow for workflow in WORKFLOWS if workflow.name == "unreal_engine_mode"]
        return selected or [WORKFLOWS[0]]

    def export_status(self) -> dict[str, Any]:
        return {"generated_at": now_iso(), "total": len(WORKFLOWS), "workflows": [w.to_dict() for w in WORKFLOWS]}
