import json
from pathlib import Path

from gizmo.brain.memory_api import SecondBrain
from gizmo.orchestrator.orchestrator import GizmoOrchestrator


def test_vault_rebuild_creates_indexes_graph_backlinks_and_quality_report(tmp_path: Path):
    brain = SecondBrain(tmp_path)
    decision = brain.record_decision(
        "Creator approval protects architecture",
        "Major architecture changes require Creator approval.",
        source="creator",
        confidence=1.0,
        importance=10,
        entities=["Creator", "Architecture"],
        tags=["approval"],
    )
    lesson = brain.record_lesson(
        "Vault indexes improve recall",
        "Index pages make Markdown memory readable without the application.",
        confidence=0.9,
        importance=8,
        entities=["Second Brain"],
        tags=["vault"],
    )
    brain.link_memories(decision.id, "affects", lesson.id)
    report = brain.rebuild_vault_indexes()
    root = tmp_path / "brain"
    assert report["graph_nodes"] == 2
    assert report["graph_edges"] == 1
    assert (root / "indexes" / "Memory Index.md").exists()
    assert (root / "indexes" / "Project Index.md").exists()
    assert (root / "indexes" / "Agent Index.md").exists()
    assert (root / "indexes" / "Quality Report.md").exists()
    assert (root / "graph" / "Knowledge Graph.md").exists()
    assert (root / "graph" / "Backlinks.md").exists()
    graph = json.loads((root / "graph" / "knowledge-graph.json").read_text())
    assert graph["edges"][0]["relation"] == "affects"


def test_vault_revision_view_preserves_previous_markdown(tmp_path: Path):
    brain = SecondBrain(tmp_path)
    memory = brain.record_fact("Mutable fact", "Original content", confidence=0.8)
    brain.update_memory(memory.id, content="Updated content")
    revision_dir = tmp_path / "brain" / "revisions" / memory.id
    revisions = list(revision_dir.glob("*.md"))
    assert revisions
    assert "Original content" in revisions[0].read_text()


def test_session_note_references_memories(tmp_path: Path):
    brain = SecondBrain(tmp_path)
    memory = brain.record_goal("Improve vault", "Make the vault navigable.", confidence=0.8)
    filename = brain.record_session_note("Vault session", "Generated indexes.", [memory.id])
    note = tmp_path / "brain" / "sessions" / filename
    assert note.exists()
    assert memory.id in note.read_text()


def test_export_health_exposes_phase3_capabilities(tmp_path: Path):
    brain = SecondBrain(tmp_path)
    health = brain.export_health()
    assert health["vault_indexes"] is True
    assert health["graph_export"] is True
    assert health["session_notes"] is True
    assert health["revision_views"] is True


def test_orchestrator_brain_phase3_demo(tmp_path: Path):
    result = GizmoOrchestrator(tmp_path).brain_phase3_demo()
    assert result["ready"] is True
    assert result["phase2_ready"] is True
    assert result["graph_nodes"] > 0
    assert "Memory Index.md" in result["required_files"]
