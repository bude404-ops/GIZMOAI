"""Universal public knowledge ingestion for GIZMO.

This layer is intentionally domain-neutral. It can ingest operator-provided text,
public URLs, repository notes, and seeded domain prompts, then preserve them as
Second Brain memories for later app creation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
import re
import urllib.request
from typing import Any

from gizmo.brain.models import BrainMemoryType
from gizmo.core.models import now_iso


@dataclass
class KnowledgeSource:
    kind: str
    locator: str
    title: str = ""
    domain: str = "general"
    trust: float = 0.65
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IngestionReport:
    generated_at: str
    domain: str
    sources_seen: int
    memories_created: list[str]
    facts: list[dict[str, Any]]
    gaps: list[dict[str, Any]]
    app_opportunities: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.skip = False

    def handle_data(self, data: str) -> None:
        if not self.skip:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)

    def text(self) -> str:
        return "\n".join(self.parts)


class UniversalKnowledgeIngestor:
    """Turns public/general sources into searchable memory and app opportunities."""

    DEFAULT_DOMAINS = [
        "education", "health literacy", "local business", "creative tools", "productivity",
        "automation", "finance", "community", "games", "developer tools", "data dashboards",
    ]

    def __init__(self, brain: Any, store: Any) -> None:
        self.brain = brain
        self.store = store

    def ingest(self, sources: list[KnowledgeSource] | None = None, *, domain: str = "general", limit: int = 8) -> IngestionReport:
        sources = sources or self.seed_sources(domain=domain, limit=limit)
        memories: list[str] = []
        facts: list[dict[str, Any]] = []
        opportunities: list[dict[str, Any]] = []
        gaps: list[dict[str, Any]] = []
        for source in sources[:limit]:
            text = self._load_source(source)
            if not text:
                gaps.append({"source": source.to_dict(), "gap": "source unavailable or empty", "priority": "MEDIUM"})
                continue
            summary = self._summarize(text)
            tags = ["universal-knowledge", source.kind, source.domain, "app-source"]
            memory = self.brain.remember(
                BrainMemoryType.RESEARCH,
                source.title or f"Universal source: {source.locator[:60]}",
                text[:6000],
                source="universal-ingestor",
                source_agent="agent-02",
                project="Gizmo",
                importance=7,
                confidence=max(0.45, min(0.95, source.trust)),
                tags=tags,
                entities=[source.domain, source.kind],
                metadata={"source": source.to_dict(), "summary": summary},
            )
            memories.append(memory.id)
            fact = {"memory_id": memory.id, "domain": source.domain, "title": memory.title, "summary": summary, "keywords": self._keywords(text)}
            facts.append(fact)
            opportunities.extend(self._opportunities(fact))
        report = IngestionReport(now_iso(), domain, len(sources), memories, facts, gaps, opportunities[:12])
        self.store.write(report.to_dict(), "knowledge", "latest_ingestion.json")
        self.store.append_list(report.to_dict(), "knowledge", "ingestion_history.json")
        for opportunity in opportunities[:12]:
            self.store.append_list({"created_at": now_iso(), **opportunity}, "knowledge", "app_opportunities.json")
        return report

    def seed_sources(self, *, domain: str = "general", limit: int = 8) -> list[KnowledgeSource]:
        domains = [domain] if domain != "general" else self.DEFAULT_DOMAINS
        seeds = []
        for item in domains[:limit]:
            text = (
                f"Domain: {item}. Learn public patterns, user pain points, workflows, datasets, "
                "interface needs, safety boundaries, and app ideas. Prefer tools that save time, "
                "teach clearly, compare options, automate repetitive work, or reveal hidden structure."
            )
            seeds.append(KnowledgeSource(kind="seed", locator=text, title=f"General learning seed: {item}", domain=item, trust=0.7))
        return seeds

    def _load_source(self, source: KnowledgeSource) -> str:
        if source.kind in {"text", "seed", "note"}:
            return source.locator.strip()
        if source.kind in {"url", "web", "docs"} and source.locator.startswith(("http://", "https://")):
            try:
                req = urllib.request.Request(source.locator, headers={"User-Agent": "GIZMO universal public knowledge ingestor"})
                with urllib.request.urlopen(req, timeout=20) as response:
                    raw = response.read(750_000).decode("utf-8", errors="ignore")
                if "<html" in raw.lower() or "<!doctype" in raw.lower():
                    parser = _TextExtractor()
                    parser.feed(raw)
                    return parser.text()[:12000]
                return raw[:12000]
            except Exception as exc:
                return f"Unable to retrieve public URL {source.locator}: {type(exc).__name__}"
        return source.locator.strip()

    @staticmethod
    def _summarize(text: str) -> str:
        cleaned = " ".join(text.split())
        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        useful = [s for s in sentences if len(s) > 35][:3]
        return " ".join(useful)[:600] if useful else cleaned[:350]

    @staticmethod
    def _keywords(text: str) -> list[str]:
        words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text.lower())
        stop = {"this", "that", "with", "from", "will", "should", "public", "domain", "learn", "patterns", "tools"}
        counts: dict[str, int] = {}
        for word in words:
            if word not in stop:
                counts[word] = counts.get(word, 0) + 1
        return [word for word, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:12]]

    @staticmethod
    def _opportunities(fact: dict[str, Any]) -> list[dict[str, Any]]:
        domain = fact["domain"]
        keywords = fact.get("keywords", [])[:5]
        base = ", ".join(keywords) if keywords else domain
        return [
            {
                "domain": domain,
                "title": f"{domain.title()} Command Center",
                "problem": f"People need a clear way to organize and act on {base}.",
                "app_type": "dashboard",
                "source_memory_id": fact["memory_id"],
                "confidence": 0.72,
            },
            {
                "domain": domain,
                "title": f"{domain.title()} Decision Helper",
                "problem": f"Users need guided choices and checklists for {base}.",
                "app_type": "interactive-tool",
                "source_memory_id": fact["memory_id"],
                "confidence": 0.68,
            },
        ]
