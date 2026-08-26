"""Central shared memory API for all Gizmo agents."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from gizmo.brain.embedding import LocalLexicalEmbedder
from gizmo.brain.models import BrainMemory, BrainMemoryStatus, BrainMemoryType, BrainRelationship
from gizmo.brain.vault import ObsidianVault
from gizmo.core.models import now_iso
from gizmo.core.store import JsonStore


class SecondBrain:
    """Persistent brain with structured storage and Obsidian-compatible vault."""

    def __init__(self, workspace: str | Path, embedder: LocalLexicalEmbedder | None = None) -> None:
        self.workspace = Path(workspace)
        self.store = JsonStore(self.workspace / "structured")
        self.vault = ObsidianVault(self.workspace / "brain")
        self.embedder = embedder or LocalLexicalEmbedder()
        self.store.write({"backend": "local-json", "fallback": "markdown-vault", "provider_independent": True}, "config", "storage.json")

    def remember(self, memory_type: BrainMemoryType | str, title: str, content: str, *, summary: str | None = None,
                 source: str = "agent", source_agent: str = "reaper", project: str = "Gizmo",
                 importance: int = 5, confidence: float = 0.5, tags: list[str] | None = None,
                 entities: list[str] | None = None, metadata: dict[str, Any] | None = None) -> BrainMemory:
        kind = BrainMemoryType(memory_type)
        summary_text = summary or self._summarize(content)
        embedding = self.embedder.embed(" ".join([title, summary_text, content, " ".join(tags or [])]))
        memory = BrainMemory(
            type=kind, title=title, content=content, summary=summary_text, source=source,
            source_agent=source_agent, project=project, importance=max(1, min(10, importance)),
            confidence=max(0.0, min(1.0, confidence)), tags=tags or [], entities=entities or [],
            embedding=embedding, metadata=metadata or {},
        )
        self._persist(memory)
        return memory

    def recall(self, query: str, *, project: str | None = None, limit: int = 5) -> list[BrainMemory]:
        return self.search_memory(query, project=project, limit=limit)

    def search_memory(self, query: str, *, project: str | None = None, memory_type: BrainMemoryType | str | None = None,
                      limit: int = 10) -> list[BrainMemory]:
        query_terms = [term.lower() for term in query.split() if term.strip()]
        query_embedding = self.embedder.embed(query)
        desired_type = BrainMemoryType(memory_type).value if memory_type else None
        scored: list[tuple[float, BrainMemory]] = []
        for memory in self._all_memories():
            if memory.status != BrainMemoryStatus.ACTIVE:
                continue
            if project and memory.project != project:
                continue
            if desired_type and memory.type.value != desired_type:
                continue
            haystack = " ".join([memory.title, memory.summary, memory.content, " ".join(memory.tags), " ".join(memory.entities)]).lower()
            keyword_score = sum(1 for term in query_terms if term in haystack)
            semantic_score = self.embedder.cosine(query_embedding, memory.embedding)
            relationship_bonus = 0.05 * len(memory.relationships)
            score = keyword_score + semantic_score + (memory.importance / 20) + memory.confidence + relationship_bonus
            if score > 0:
                scored.append((score, memory))
        scored.sort(key=lambda item: item[0], reverse=True)
        results = [memory for _, memory in scored[:limit]]
        for memory in results:
            memory.access_count += 1
            memory.last_accessed = now_iso()
            self._persist(memory)
        return results

    def semantic_search(self, query: str, *, limit: int = 10) -> list[BrainMemory]:
        query_embedding = self.embedder.embed(query)
        scored = [(self.embedder.cosine(query_embedding, memory.embedding), memory) for memory in self._all_memories() if memory.status == BrainMemoryStatus.ACTIVE]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [memory for score, memory in scored[:limit] if score > 0]

    def get_related_memory(self, memory_id: str) -> list[BrainMemory]:
        memory = self.get(memory_id)
        ids = {rel.target_id for rel in memory.relationships}
        return [self.get(mid) for mid in ids if self.exists(mid)]

    def get_project_memory(self, project: str, *, limit: int = 50) -> list[BrainMemory]:
        return [m for m in self._all_memories() if m.project == project and m.status == BrainMemoryStatus.ACTIVE][:limit]

    def get_agent_memory(self, agent_id: str, *, limit: int = 50) -> list[BrainMemory]:
        return [m for m in self._all_memories() if m.source_agent == agent_id and m.status == BrainMemoryStatus.ACTIVE][:limit]

    def record_fact(self, title: str, content: str, **kwargs: Any) -> BrainMemory:
        return self.remember(BrainMemoryType.FACT, title, content, **kwargs)

    def record_decision(self, title: str, content: str, **kwargs: Any) -> BrainMemory:
        return self.remember(BrainMemoryType.DECISION, title, content, importance=kwargs.pop("importance", 9), confidence=kwargs.pop("confidence", 1.0), **kwargs)

    def record_lesson(self, title: str, content: str, **kwargs: Any) -> BrainMemory:
        return self.remember(BrainMemoryType.LESSON, title, content, **kwargs)

    def record_experience(self, title: str, content: str, **kwargs: Any) -> BrainMemory:
        return self.remember(BrainMemoryType.EXPERIENCE, title, content, **kwargs)

    def record_research(self, title: str, content: str, **kwargs: Any) -> BrainMemory:
        return self.remember(BrainMemoryType.RESEARCH, title, content, **kwargs)

    def record_experiment(self, title: str, content: str, **kwargs: Any) -> BrainMemory:
        return self.remember(BrainMemoryType.EXPERIMENT, title, content, **kwargs)

    def record_evaluation(self, title: str, content: str, **kwargs: Any) -> BrainMemory:
        return self.remember(BrainMemoryType.EVALUATION, title, content, **kwargs)

    def record_goal(self, title: str, content: str, **kwargs: Any) -> BrainMemory:
        return self.remember(BrainMemoryType.GOAL, title, content, **kwargs)

    def record_procedure(self, title: str, content: str, **kwargs: Any) -> BrainMemory:
        return self.remember(BrainMemoryType.PROCEDURE, title, content, **kwargs)

    def update_memory(self, memory_id: str, **changes: Any) -> BrainMemory:
        memory = self.get(memory_id)
        for key, value in changes.items():
            if hasattr(memory, key):
                setattr(memory, key, value)
        memory.updated_at = now_iso()
        if "content" in changes or "summary" in changes or "title" in changes:
            memory.embedding = self.embedder.embed(" ".join([memory.title, memory.summary, memory.content]))
        self._persist(memory)
        return memory

    def supersede_memory(self, old_id: str, new_id: str) -> None:
        old = self.get(old_id)
        new = self.get(new_id)
        old.status = BrainMemoryStatus.SUPERSEDED
        old.superseded_by.append(new_id)
        new.supersedes.append(old_id)
        self._persist(old)
        self._persist(new)

    def archive_memory(self, memory_id: str) -> BrainMemory:
        return self.update_memory(memory_id, status=BrainMemoryStatus.ARCHIVED)

    def link_memories(self, source_id: str, relation: str, target_id: str, confidence: float = 0.75) -> BrainRelationship:
        source = self.get(source_id)
        relationship = BrainRelationship(source_id=source_id, relation=relation, target_id=target_id, confidence=confidence)
        source.relationships.append(relationship)
        self._persist(source)
        self.store.append_list(relationship.to_dict(), "graph", "relationships.json")
        return relationship

    def get(self, memory_id: str) -> BrainMemory:
        data = self.store.read("memory", f"{memory_id}.json")
        if not data:
            raise KeyError(memory_id)
        return BrainMemory.from_dict(data)

    def exists(self, memory_id: str) -> bool:
        return self.store.path("memory", f"{memory_id}.json").exists()

    def export_health(self) -> dict[str, Any]:
        memories = self._all_memories()
        by_type: dict[str, int] = {}
        for memory in memories:
            by_type[memory.type.value] = by_type.get(memory.type.value, 0) + 1
        return {
            "memories": len(memories),
            "active": sum(1 for m in memories if m.status == BrainMemoryStatus.ACTIVE),
            "by_type": by_type,
            "vault_directories": 16,
            "backend": "local-json",
            "markdown_vault": True,
            "provider_independent_embeddings": True,
        }

    def _persist(self, memory: BrainMemory) -> None:
        self.store.write(memory.to_dict(), "memory", f"{memory.id}.json")
        self.store.append_list(memory.id, "indexes", f"type-{memory.type.value}.json")
        self.store.append_list(memory.id, "indexes", f"project-{memory.project}.json")
        self.vault.write_memory(memory)

    def _all_memories(self) -> list[BrainMemory]:
        directory = self.store.path("memory")
        return [BrainMemory.from_dict(__import__("json").loads(path.read_text())) for path in sorted(directory.glob("*.json"))]

    @staticmethod
    def _summarize(content: str) -> str:
        compact = " ".join(content.split())
        return compact[:180] + ("..." if len(compact) > 180 else "")
