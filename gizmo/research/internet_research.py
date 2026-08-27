"""Provider-neutral internet research pipeline for GIZMO.

The pipeline is intentionally separable from any one search provider. A runner can
feed it search results, fetched documents, or manual source text; it will filter,
score, cross-check, synthesize, cite, and selectively preserve useful knowledge.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import re
from typing import Any
from urllib.parse import urlparse

from gizmo.brain.models import BrainMemoryType
from gizmo.core.models import now_iso
from gizmo.core.store import JsonStore


@dataclass
class ResearchSource:
    title: str
    url: str
    text: str
    source_type: str = "web"
    fetched_at: str = field(default_factory=now_iso)
    quality_score: float = 0.5
    quality_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResearchClaim:
    kind: str
    statement: str
    source_url: str
    confidence: float
    evidence: str
    conflicts_with: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResearchReport:
    query: str
    generated_at: str
    sources_considered: list[dict[str, Any]]
    facts: list[dict[str, Any]]
    inferences: list[dict[str, Any]]
    hypotheses: list[dict[str, Any]]
    uncertainties: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    synthesis: str
    memories_created: list[str]
    ready: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class InternetResearchPipeline:
    def __init__(self, brain: Any, store: JsonStore) -> None:
        self.brain = brain
        self.store = store

    def run(self, query: str, sources: list[ResearchSource] | None = None, *, project: str = "Gizmo", store_useful: bool = True) -> ResearchReport:
        normalized = " ".join((query or "").split())
        scored_sources = [self._score_source(src) for src in (sources or self._offline_seed_sources(normalized))]
        filtered = [src for src in scored_sources if src.quality_score >= 0.35 and len(src.text.strip()) >= 40]
        claims = self._extract_claims(normalized, filtered)
        conflicts = self._detect_conflicts(claims)
        for conflict in conflicts:
            a = claims[conflict["a"]]
            b = claims[conflict["b"]]
            a.conflicts_with.append(b.statement)
            b.conflicts_with.append(a.statement)
            a.confidence = min(a.confidence, 0.55)
            b.confidence = min(b.confidence, 0.55)
        facts = [c for c in claims if c.kind == "FACT"]
        inferences = [c for c in claims if c.kind == "INFERENCE"]
        hypotheses = [c for c in claims if c.kind == "HYPOTHESIS"]
        uncertainties = [c for c in claims if c.kind == "UNCERTAINTY"]
        citations = [{"url": src.url, "title": src.title, "quality": src.quality_score, "notes": src.quality_notes} for src in filtered]
        synthesis = self._synthesize(normalized, facts, inferences, hypotheses, uncertainties, conflicts)
        memories: list[str] = []
        if store_useful:
            memories = self._store_useful(normalized, filtered, facts, inferences, hypotheses, uncertainties, project)
        report = ResearchReport(
            query=normalized,
            generated_at=now_iso(),
            sources_considered=[src.to_dict() for src in filtered],
            facts=[c.to_dict() for c in facts],
            inferences=[c.to_dict() for c in inferences],
            hypotheses=[c.to_dict() for c in hypotheses],
            uncertainties=[c.to_dict() for c in uncertainties],
            citations=citations,
            conflicts=conflicts,
            synthesis=synthesis,
            memories_created=memories,
            ready=bool(filtered) and bool(facts or inferences or uncertainties),
        )
        self.store.write(report.to_dict(), "research", "latest_report.json")
        self.store.write(report.to_dict(), "research", "reports", f"research-{sha256(normalized.encode()).hexdigest()[:16]}.json")
        self.store.append_list(report.to_dict(), "research", "history.json")
        return report

    def _score_source(self, source: ResearchSource) -> ResearchSource:
        parsed = urlparse(source.url)
        host = parsed.netloc.lower()
        score = 0.45
        notes: list[str] = []
        if parsed.scheme in {"http", "https"}:
            score += 0.08
            notes.append("addressable source")
        if any(host.endswith(domain) for domain in [".gov", ".edu"]):
            score += 0.18
            notes.append("institutional domain")
        if any(token in host for token in ["docs", "developer", "github", "wikipedia", "openai", "unrealengine", "epicgames"]):
            score += 0.12
            notes.append("documentation or reference-oriented host")
        if len(source.text) > 500:
            score += 0.08
            notes.append("substantial text")
        if re.search(r"\b(updated|published|last modified|202[4-9])\b", source.text, re.I):
            score += 0.06
            notes.append("date or freshness signal")
        if not source.url or source.url == "memory://offline-seed":
            score -= 0.08
            notes.append("seed knowledge; replace with live source when online")
        source.quality_score = max(0.0, min(1.0, round(score, 2)))
        source.quality_notes = notes
        return source

    def _extract_claims(self, query: str, sources: list[ResearchSource]) -> list[ResearchClaim]:
        claims: list[ResearchClaim] = []
        for src in sources:
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", src.text.replace("\n", " ")) if len(s.strip()) > 24]
            for sentence in sentences[:8]:
                lower = sentence.lower()
                kind = "FACT"
                conf = min(0.92, src.quality_score + 0.12)
                if any(word in lower for word in ["may", "might", "could", "potential", "possible"]):
                    kind = "HYPOTHESIS"
                    conf = min(conf, 0.58)
                elif any(word in lower for word in ["therefore", "suggests", "indicates", "likely", "implies"]):
                    kind = "INFERENCE"
                    conf = min(conf, 0.7)
                elif any(word in lower for word in ["unknown", "unclear", "conflicting", "not enough", "uncertain"]):
                    kind = "UNCERTAINTY"
                    conf = min(conf, 0.52)
                if self._relevant(query, sentence):
                    claims.append(ResearchClaim(kind, sentence[:500], src.url, round(conf, 2), sentence[:240]))
        return claims[:40]

    def _relevant(self, query: str, sentence: str) -> bool:
        query_terms = {t for t in re.findall(r"[a-zA-Z0-9]{4,}", query.lower())}
        if not query_terms:
            return True
        sentence_terms = set(re.findall(r"[a-zA-Z0-9]{4,}", sentence.lower()))
        return bool(query_terms & sentence_terms) or len(sentence_terms) >= 8

    def _detect_conflicts(self, claims: list[ResearchClaim]) -> list[dict[str, Any]]:
        conflicts: list[dict[str, Any]] = []
        for i, a in enumerate(claims):
            la = a.statement.lower()
            for j, b in enumerate(claims[i + 1:], start=i + 1):
                lb = b.statement.lower()
                shared = set(re.findall(r"[a-zA-Z0-9]{5,}", la)) & set(re.findall(r"[a-zA-Z0-9]{5,}", lb))
                if len(shared) < 2:
                    continue
                opposite = (("not" in la or "no " in la) and not ("not" in lb or "no " in lb)) or (("increase" in la and "decrease" in lb) or ("decrease" in la and "increase" in lb))
                if opposite:
                    conflicts.append({"a": i, "b": j, "terms": sorted(shared)[:5], "note": "Claims appear directionally conflicting; keep uncertainty until reconciled."})
        return conflicts[:10]

    def _synthesize(self, query: str, facts: list[ResearchClaim], inferences: list[ResearchClaim], hypotheses: list[ResearchClaim], uncertainties: list[ResearchClaim], conflicts: list[dict[str, Any]]) -> str:
        pieces = [f"Research query: {query}."]
        if facts:
            pieces.append(f"Strongest facts: {' '.join(c.statement for c in facts[:3])}")
        if inferences:
            pieces.append(f"Inferences: {' '.join(c.statement for c in inferences[:2])}")
        if hypotheses:
            pieces.append(f"Hypotheses: {' '.join(c.statement for c in hypotheses[:2])}")
        if uncertainties or conflicts:
            pieces.append(f"Uncertainty remains: {len(uncertainties)} explicit uncertainties and {len(conflicts)} possible conflicts.")
        return " ".join(pieces)[:1800]

    def _store_useful(self, query: str, sources: list[ResearchSource], facts: list[ResearchClaim], inferences: list[ResearchClaim], hypotheses: list[ResearchClaim], uncertainties: list[ResearchClaim], project: str) -> list[str]:
        ids: list[str] = []
        for src in sources[:6]:
            if src.quality_score >= 0.55:
                mem = self.brain.record_research(
                    f"Source document: {src.title[:80]}",
                    f"Query: {query}\nSource: {src.url}\nQuality: {src.quality_score}\nNotes: {src.quality_notes}\nExcerpt: {src.text[:1200]}",
                    source=src.url,
                    source_agent="agent-02",
                    project=project,
                    importance=6,
                    confidence=src.quality_score,
                    tags=["source-document", "research", project],
                    metadata={"url": src.url, "quality": src.quality_score},
                )
                ids.append(mem.id)
        for claim in facts[:8]:
            mem = self.brain.record_fact(
                f"Fact: {claim.statement[:70]}",
                f"FACT\nStatement: {claim.statement}\nSource: {claim.source_url}\nEvidence: {claim.evidence}",
                source=claim.source_url,
                source_agent="agent-02",
                project=project,
                importance=7,
                confidence=claim.confidence,
                tags=["fact", "research", project],
                metadata=claim.to_dict(),
            )
            ids.append(mem.id)
        for claim, kind in [(c, BrainMemoryType.HYPOTHESIS) for c in hypotheses[:4]] + [(c, BrainMemoryType.RESEARCH) for c in inferences[:4]] + [(c, BrainMemoryType.WARNING) for c in uncertainties[:4]]:
            mem = self.brain.remember(
                kind,
                f"{claim.kind.title()}: {claim.statement[:70]}",
                f"{claim.kind}\nStatement: {claim.statement}\nSource: {claim.source_url}\nEvidence: {claim.evidence}\nConflicts: {claim.conflicts_with}",
                source=claim.source_url,
                source_agent="agent-02",
                project=project,
                importance=5,
                confidence=claim.confidence,
                tags=[claim.kind.lower(), "research", project],
                metadata=claim.to_dict(),
            )
            ids.append(mem.id)
        return ids

    def _offline_seed_sources(self, query: str) -> list[ResearchSource]:
        return [ResearchSource(
            title="Research pipeline seed",
            url="memory://offline-seed",
            text=(
                f"GIZMO could not receive live web documents for query '{query}' inside this invocation. "
                "The correct research behavior is to search, collect, filter, read, cross-check, synthesize, cite, and store useful knowledge with provenance. "
                "Unknown or current facts remain uncertain until live sources are read."
            ),
        )]
