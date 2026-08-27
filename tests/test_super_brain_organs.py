from gizmo.ai.reasoning import ModelReasoner
from gizmo.brain.semantic_index import DurableSemanticMemoryIndex
from gizmo.orchestrator.orchestrator import GizmoOrchestrator


def test_model_reasoner_falls_back_safely_without_provider_key(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    memory = orchestrator.brain_core.record_lesson(
        "Use memory before action",
        "Every agent should retrieve relevant context before acting.",
        project="Gizmo",
        tags=["super-brain", "memory"],
    )
    context = orchestrator.brain_core.build_context("memory before action", project="Gizmo")
    result = ModelReasoner(provider="local").reason(agent_id="agent-13", lane="ai", objective="strengthen super brain", context=context)

    assert result.ok is True
    assert result.provider == "local"
    assert result.confidence > 0.5
    assert memory.id in result.used_memory_ids
    assert "Safe next action" in result.answer


def test_semantic_index_rebuilds_and_searches(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    orchestrator.brain_core.record_research(
        "Super brain semantic memory",
        "A durable semantic index lets GIZMO search prior knowledge by meaning across cloud runs.",
        project="Gizmo",
        tags=["semantic", "search"],
    )
    index = DurableSemanticMemoryIndex(orchestrator.brain_core)
    report = index.rebuild(project="Gizmo")
    rows = index.search("search prior knowledge by meaning", project="Gizmo")

    assert report.indexed_memories >= 1
    assert report.active_memories >= 1
    assert rows
    assert any("semantic" in row["title"].lower() for row in rows)
    assert (tmp_path / "second_brain" / "structured" / "semantic" / "index_report.json").exists()
