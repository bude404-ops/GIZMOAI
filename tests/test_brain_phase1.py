from pathlib import Path

from gizmo.brain.bootstrap import BrainBootstrapper
from gizmo.brain.memory_api import SecondBrain
from gizmo.brain.models import BrainMemoryStatus, BrainMemoryType


def test_brain_remember_recall_and_markdown_vault(tmp_path: Path):
    brain = SecondBrain(tmp_path)
    memory = brain.record_decision(
        "Creator requires model independence",
        "Gizmo must not depend on Claude, GPT, Gemini, Grok, or any single AI provider.",
        source="creator",
        source_agent="reaper",
        tags=["creator", "model-independent"],
        entities=["Creator", "Gizmo"],
    )
    recalled = brain.recall("model independence provider", limit=3)
    assert recalled[0].id == memory.id
    assert recalled[0].access_count >= 1
    vault_files = list((tmp_path / "brain" / "decisions").glob("*.md"))
    assert vault_files
    text = vault_files[0].read_text()
    assert "---" in text
    assert "[[Creator]]" in text
    assert "model-independent" in text


def test_brain_memory_types_exist():
    expected = {
        "FACT", "DECISION", "PREFERENCE", "LESSON", "EXPERIENCE", "PROJECT_STATE", "TASK",
        "RESEARCH", "CONVERSATION", "AGENT_MEMORY", "RELATIONSHIP", "WARNING", "IDEA",
        "HYPOTHESIS", "EXPERIMENT", "EVALUATION", "GOAL", "PROCEDURE", "SKILL",
    }
    assert expected == {item.value for item in BrainMemoryType}


def test_brain_links_supersedes_and_archives(tmp_path: Path):
    brain = SecondBrain(tmp_path)
    old = brain.record_fact("Old deployment fact", "Use process X.")
    new = brain.record_fact("Current deployment fact", "Use process Y.")
    rel = brain.link_memories(new.id, "supersedes", old.id, confidence=0.9)
    brain.supersede_memory(old.id, new.id)
    archived = brain.archive_memory(new.id)
    assert rel.target_id == old.id
    assert brain.get(old.id).status == BrainMemoryStatus.SUPERSEDED
    assert archived.status == BrainMemoryStatus.ARCHIVED


def test_bootstrap_imports_repository_agents_docs_and_goals(tmp_path: Path):
    brain = SecondBrain(tmp_path)
    report = BrainBootstrapper(brain, Path.cwd()).initialize_from_repository()
    assert report["created"] >= 40
    assert report["health"]["markdown_vault"] is True
    assert report["health"]["provider_independent_embeddings"] is True
    assert (tmp_path / "brain" / "README.md").exists()
    assert len(list((tmp_path / "brain" / "agents").glob("*.md"))) == 27
    assert brain.recall("GitHub approval policy", limit=1)


def test_semantic_search_model_independent(tmp_path: Path):
    brain = SecondBrain(tmp_path)
    brain.record_lesson("Hybrid retrieval improves brain recall", "Keyword and lexical vector retrieval should be combined with recency and importance.")
    results = brain.semantic_search("memory retrieval vectors", limit=5)
    assert results
    assert results[0].embedding
