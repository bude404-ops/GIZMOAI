"""Durable semantic memory index for GIZMO's Second Brain."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from gizmo.core.models import now_iso


@dataclass
class SemanticIndexReport:
    generated_at: str
    indexed_memories: int
    active_memories: int
    top_terms: list[dict[str, Any]]
    hot_memories: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DurableSemanticMemoryIndex:
    """Builds a portable search manifest from the local embedding store."""

    def __init__(self, brain: Any) -> None:
        self.brain = brain
        self.store = brain.store

    def rebuild(self, *, project: str = "Gizmo") -> SemanticIndexReport:
        memories = [m for m in self.brain._all_memories() if m.project == project]
        active = [m for m in memories if m.status.value == "ACTIVE"]
        term_counts: dict[str, int] = {}
        for memory in active:
            tokens = self._tokens(" ".join([memory.title, memory.summary, memory.content, " ".join(memory.tags)]))
            for token in set(tokens):
                if len(token) >= 4:
                    term_counts[token] = term_counts.get(token, 0) + 1
        top_terms = [{"term": term, "count": count} for term, count in sorted(term_counts.items(), key=lambda item: (-item[1], item[0]))[:50]]
        hot = sorted(active, key=lambda m: ((m.access_count or 0), m.importance, m.confidence), reverse=True)[:25]
        hot_memories = [
            {"id": m.id, "title": m.title, "type": m.type.value, "importance": m.importance, "confidence": m.confidence, "access_count": m.access_count}
            for m in hot
        ]
        report = SemanticIndexReport(now_iso(), len(memories), len(active), top_terms, hot_memories)
        self.store.write(report.to_dict(), "semantic", "index_report.json")
        self.store.write({"terms": top_terms, "hot_memories": hot_memories}, "semantic", "manifest.json")
        return report

    def search(self, query: str, *, project: str = "Gizmo", limit: int = 8) -> list[dict[str, Any]]:
        results = self.brain.hybrid_search(query, project=project, limit=limit, include_trace=True)
        rows = []
        for trace, memory in results:
            rows.append({
                "id": memory.id,
                "title": memory.title,
                "type": memory.type.value,
                "summary": memory.summary,
                "score": trace.score,
                "reason": trace.reason,
            })
        self.store.append_list({"query": query, "project": project, "results": rows, "searched_at": now_iso()}, "semantic", "search_log.json")
        return rows

    @staticmethod
    def _tokens(text: str) -> list[str]:
        cleaned = []
        word = []
        for char in text.lower():
            if char.isalnum() or char in {"_", "-"}:
                word.append(char)
            elif word:
                cleaned.append("".join(word).strip("-_"))
                word = []
        if word:
            cleaned.append("".join(word).strip("-_"))
        stop = {"that", "with", "from", "this", "into", "should", "future", "cycle", "agent"}
        return [token for token in cleaned if token and token not in stop]
