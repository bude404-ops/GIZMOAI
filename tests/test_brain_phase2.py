from pathlib import Path

from gizmo.brain.bootstrap import BrainBootstrapper
from gizmo.brain.memory_api import SecondBrain
from gizmo.brain.models import BrainMemoryType
from gizmo.orchestrator.orchestrator import GizmoOrchestrator


def seeded_brain(tmp_path: Path) -> SecondBrain:
    brain = SecondBrain(tmp_path)
    brain.record_decision(
        "Creator approval required for dangerous changes",
        "Changing security, credentials, spending money, deleting data, or major architecture changes requires Creator approval.",
        importance=10,
        confidence=1.0,
        source="creator",
        source_agent="reaper",
        tags=["approval", "security"],
        entities=["Creator", "Policy Gate"],
    )
    brain.record_lesson(
        "Workflow failures need preserved logs",
        "When GitHub workflows fail, collect logs, identify probable cause, run safe fixes, evaluate, and store a lesson.",
        importance=8,
        confidence=0.82,
        source="phase-2-test",
        source_agent="agent-26",
        tags=["github", "workflow", "failure"],
    )
    brain.record_procedure(
        "Deployment preflight procedure",
        "Verify environment variables, permissions, tests, build output, deployment target, health check, and rollback before deployment.",
        importance=9,
        confidence=0.9,
        source="phase-2-test",
        source_agent="agent-09",
        tags=["deploy", "procedure"],
    )
    brain.record_fact(
        "Gizmo repository state exists",
        "The repository has source code, tests, documentation, GitHub workflows, policy engine, and second brain foundation.",
        importance=7,
        confidence=0.95,
        source="phase-2-test",
        source_agent="reaper",
        tags=["project-state", "github"],
    )
    return brain


def test_hybrid_retrieval_returns_trace_and_weights_creator_decisions(tmp_path: Path):
    brain = seeded_brain(tmp_path)
    results = brain.hybrid_search("Creator approval security architecture", project="Gizmo", include_trace=True, limit=3)
    assert results
    trace, memory = results[0]
    assert memory.type == BrainMemoryType.DECISION
    assert trace.score > 0
    assert trace.keyword_score > 0
    assert "important" in trace.reason or "high-confidence" in trace.reason


def test_context_builder_collects_decisions_lessons_procedures_and_gaps(tmp_path: Path):
    brain = seeded_brain(tmp_path)
    pack = brain.build_context("Prepare GitHub workflow deployment learning", project="Gizmo")
    assert pack.useful_context
    assert pack.decisions
    assert pack.lessons
    assert pack.procedures
    assert pack.retrieval_trace
    assert isinstance(pack.gaps, list)


def test_knowledge_gap_detector_creates_research_tasks_for_critical_gaps(tmp_path: Path):
    brain = SecondBrain(tmp_path)
    brain.record_fact("Project state", "Gizmo is active.", confidence=0.9)
    pack = brain.build_context("Deploy database-backed learning engine", project="Gizmo")
    critical = [gap for gap in pack.gaps if gap["critical"]]
    assert critical
    assert pack.proposed_research_tasks
    assert brain.recall("Research needed database configuration", limit=5)


def test_bootstrapped_brain_phase2_context(tmp_path: Path):
    brain = SecondBrain(tmp_path)
    BrainBootstrapper(brain, Path.cwd()).initialize_from_repository()
    pack = brain.build_context("Improve autonomous learning memory retrieval", project="Gizmo")
    assert pack.useful_context
    assert pack.retrieval_trace
    assert brain.export_health()["hybrid_retrieval"] is True


def test_orchestrator_brain_phase2_demo(tmp_path: Path):
    result = GizmoOrchestrator(tmp_path).brain_phase2_demo()
    assert result["ready"] is True
    assert result["initialization"] is True
    assert result["hybrid_results"] > 0
    assert result["context"]["retrieval_trace"]
