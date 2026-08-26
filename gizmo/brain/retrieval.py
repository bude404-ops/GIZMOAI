"""Phase 2 intelligent retrieval, task preflight, and knowledge-gap detection."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import re
from typing import Any

from gizmo.brain.models import BrainMemory, BrainMemoryType
from gizmo.core.models import now_iso

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


@dataclass
class RetrievalTrace:
    memory_id: str
    title: str
    memory_type: str
    score: float
    keyword_score: float
    semantic_score: float
    project_score: float
    recency_score: float
    importance_score: float
    confidence_score: float
    graph_score: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ContextPack:
    task: str
    project: str
    created_at: str = field(default_factory=now_iso)
    useful_context: list[dict[str, Any]] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    lessons: list[dict[str, Any]] = field(default_factory=list)
    procedures: list[dict[str, Any]] = field(default_factory=list)
    project_state: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    gaps: list[dict[str, Any]] = field(default_factory=list)
    proposed_research_tasks: list[dict[str, Any]] = field(default_factory=list)
    retrieval_trace: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def ready(self) -> bool:
        return not any(gap.get("critical") for gap in self.gaps)


class HybridRetriever:
    """Hybrid retrieval: keyword + semantic + project + recency + importance + graph."""

    def __init__(self, brain: Any) -> None:
        self.brain = brain

    def search(self, query: str, *, project: str | None = None, limit: int = 10,
               memory_type: BrainMemoryType | str | None = None) -> list[tuple[RetrievalTrace, BrainMemory]]:
        terms = [token.lower() for token in _TOKEN_RE.findall(query)]
        query_embedding = self.brain.embedder.embed(query)
        desired_type = BrainMemoryType(memory_type).value if memory_type else None
        scored: list[tuple[RetrievalTrace, BrainMemory]] = []
        for memory in self.brain._all_memories():
            if memory.status.value != "ACTIVE":
                continue
            if desired_type and memory.type.value != desired_type:
                continue
            text = " ".join([memory.title, memory.summary, memory.content, " ".join(memory.tags), " ".join(memory.entities)]).lower()
            keyword = sum(1 for term in terms if term in text) / max(1, len(set(terms)))
            semantic = max(0.0, self.brain.embedder.cosine(query_embedding, memory.embedding))
            project_score = 1.0 if project and memory.project == project else (0.25 if not project else 0.0)
            importance = memory.importance / 10
            confidence = memory.confidence
            graph = min(1.0, len(memory.relationships) * 0.15)
            recency = self._recency(memory.updated_at)
            score = (keyword * 3.0) + (semantic * 2.0) + (project_score * 1.2) + (importance * 0.9) + (confidence * 0.8) + (graph * 0.5) + (recency * 0.4)
            if score > 0.35:
                trace = RetrievalTrace(
                    memory_id=memory.id, title=memory.title, memory_type=memory.type.value,
                    score=round(score, 4), keyword_score=round(keyword, 4), semantic_score=round(semantic, 4),
                    project_score=round(project_score, 4), recency_score=round(recency, 4),
                    importance_score=round(importance, 4), confidence_score=round(confidence, 4), graph_score=round(graph, 4),
                    reason=self._reason(keyword, semantic, project_score, importance, confidence, graph),
                )
                scored.append((trace, memory))
        scored.sort(key=lambda item: item[0].score, reverse=True)
        results = scored[:limit]
        for _, memory in results:
            memory.access_count += 1
            memory.last_accessed = now_iso()
            self.brain._persist(memory)
        return results

    @staticmethod
    def _recency(timestamp: str) -> float:
        try:
            dt = datetime.fromisoformat(timestamp)
            age_days = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400)
            return 1.0 / (1.0 + age_days / 30.0)
        except Exception:
            return 0.1

    @staticmethod
    def _reason(keyword: float, semantic: float, project: float, importance: float, confidence: float, graph: float) -> str:
        reasons = []
        if keyword > 0: reasons.append("keyword")
        if semantic > 0.2: reasons.append("semantic")
        if project > 0.5: reasons.append("project")
        if importance > 0.7: reasons.append("important")
        if confidence > 0.8: reasons.append("high-confidence")
        if graph > 0: reasons.append("linked")
        return ", ".join(reasons) or "weak signal"


class KnowledgeGapDetector:
    """Determines what Gizmo knows, does not know, and should research."""

    REQUIRED_PATTERNS = {
        "deploy": ["deployment procedure", "environment variables", "health check"],
        "database": ["database configuration", "migration procedure", "backup restore"],
        "github": ["GitHub permissions", "workflow failure history", "repository state"],
        "retrieval": ["retrieval evaluation", "semantic recall", "hybrid search"],
        "experiment": ["hypothesis", "measurement", "sandbox"],
        "learning": ["goal", "evaluation", "procedure"],
    }

    def __init__(self, brain: Any) -> None:
        self.brain = brain

    def detect(self, task: str, *, project: str = "Gizmo") -> list[dict[str, Any]]:
        lower = task.lower()
        checks = []
        for trigger, requirements in self.REQUIRED_PATTERNS.items():
            if trigger in lower:
                checks.extend(requirements)
        if not checks:
            checks = ["project state", "relevant decisions", "previous lessons"]
        gaps = []
        for requirement in dict.fromkeys(checks):
            matches = self.brain.hybrid_search(requirement, project=project, limit=3, include_trace=True) if hasattr(self.brain, "hybrid_search") else []
            confidence = max([memory.confidence for trace, memory in matches if trace.keyword_score > 0], default=0.0)
            if len(matches) == 0 or confidence < 0.55:
                critical = any(word in requirement for word in ["deployment", "database", "permissions", "backup", "health"])
                gaps.append({
                    "requirement": requirement,
                    "known": False,
                    "confidence": round(confidence, 3),
                    "critical": critical,
                    "priority": "HIGH" if critical else "MEDIUM",
                    "recommended_action": f"Create research task: verify {requirement} for {project}.",
                })
        return gaps


class ContextBuilder:
    """Builds useful work context before significant action."""

    def __init__(self, brain: Any) -> None:
        self.brain = brain
        self.gaps = KnowledgeGapDetector(brain)

    def build(self, task: str, *, project: str = "Gizmo", limit: int = 12) -> ContextPack:
        results = self.brain.hybrid_search(task, project=project, limit=limit, include_trace=True)
        traces = [trace.to_dict() for trace, _ in results]
        memories = [memory for _, memory in results]
        pack = ContextPack(task=task, project=project, retrieval_trace=traces)
        pack.useful_context = [self._brief(m) for m in memories[:6]]
        pack.decisions = [self._brief(m) for m in memories if m.type == BrainMemoryType.DECISION][:4]
        pack.lessons = [self._brief(m) for m in memories if m.type == BrainMemoryType.LESSON][:4]
        pack.procedures = [self._brief(m) for m in memories if m.type in {BrainMemoryType.PROCEDURE, BrainMemoryType.SKILL}][:4]
        pack.project_state = [self._brief(m) for m in memories if m.type == BrainMemoryType.PROJECT_STATE][:3]
        pack.warnings = [self._brief(m) for m in memories if m.type == BrainMemoryType.WARNING][:3]
        pack.gaps = self.gaps.detect(task, project=project)
        for gap in pack.gaps:
            if gap["priority"] == "HIGH":
                research = self.brain.record_research(
                    f"Research needed: {gap['requirement']}",
                    gap["recommended_action"],
                    source="knowledge-gap-detector",
                    source_agent="agent-02",
                    project=project,
                    importance=8,
                    confidence=0.7,
                    tags=["research-task", "knowledge-gap", gap["priority"].lower()],
                    entities=[project, "Research Agent"],
                    metadata={"gap": gap, "origin_task": task},
                )
                pack.proposed_research_tasks.append(self._brief(research))
        return pack

    @staticmethod
    def _brief(memory: BrainMemory) -> dict[str, Any]:
        return {
            "id": memory.id,
            "type": memory.type.value,
            "title": memory.title,
            "summary": memory.summary,
            "importance": memory.importance,
            "confidence": memory.confidence,
            "tags": memory.tags,
        }
