"""Safe Mini App auto-prototyper for GIZMO.

The prototyper turns chosen autonomous ideas and app blueprints into real HTML
prototype files plus manifests. It deliberately stops short of publishing; that
boundary keeps autonomous creation useful while leaving external release under
operator approval.
"""
from __future__ import annotations

import html
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from gizmo.brain.models import BrainMemoryType
from gizmo.core.models import now_iso


@dataclass
class MiniAppPrototype:
    id: str
    title: str
    source_type: str
    source_id: str
    problem: str
    features: list[str]
    safety_boundaries: list[str]
    status: str
    approval_required: bool
    html_path: str
    manifest_path: str
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PrototypeReport:
    generated_at: str
    prototypes_created: list[str]
    review_queue_size: int
    top_prototypes: list[dict[str, Any]]
    published: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SafeMiniAppPrototyper:
    """Creates mobile Mini App prototype files from GIZMO's own ideas."""

    def __init__(self, brain: Any, store: Any) -> None:
        self.brain = brain
        self.store = store

    def run(self, *, limit: int = 3, allow_publish: bool = False) -> PrototypeReport:
        candidates = self._candidate_sources(limit=limit)
        prototypes: list[MiniAppPrototype] = []
        for source in candidates:
            prototype = self._prototype_from_source(source)
            html_text = self._render_html(prototype)
            html_path = self.store.path("apps", "prototypes", f"{prototype.id}.html")
            html_path.write_text(html_text)
            manifest_path = self.store.write(prototype.to_dict(), "apps", "prototypes", f"{prototype.id}.json")
            prototype.html_path = str(html_path)
            prototype.manifest_path = str(manifest_path)
            self.store.write(prototype.to_dict(), "apps", "prototypes", f"{prototype.id}.json")
            self.store.append_list(prototype.to_dict(), "apps", "prototype_review_queue.json")
            self.brain.remember(
                BrainMemoryType.IDEA,
                f"Prototype draft: {prototype.title}",
                self._memory_text(prototype),
                source="safe-mini-app-prototyper",
                source_agent="agent-26",
                project="Gizmo",
                importance=8,
                confidence=0.76,
                tags=["prototype", "mini-app", "approval-gated", prototype.source_type],
                entities=[prototype.title, prototype.source_type],
                metadata={"prototype": prototype.to_dict()},
            )
            prototypes.append(prototype)
        queue = self.store.read("apps", "prototype_review_queue.json", default=[])
        report = PrototypeReport(now_iso(), [p.id for p in prototypes], len(queue), [p.to_dict() for p in prototypes], published=allow_publish and False)
        self.store.write(report.to_dict(), "apps", "latest_prototype_report.json")
        self.store.append_list(report.to_dict(), "apps", "prototype_history.json")
        return report

    def latest(self) -> dict[str, Any]:
        return self.store.read("apps", "latest_prototype_report.json", default={})

    def _candidate_sources(self, *, limit: int) -> list[dict[str, Any]]:
        sources: list[dict[str, Any]] = []
        chosen = self.store.read("ideas", "chosen_next.json", default=[])
        for item in reversed(chosen[-limit * 2:]):
            sources.append({
                "source_type": "chosen-idea",
                "source_id": item.get("id", "unknown"),
                "title": item.get("title", "Autonomous Idea App"),
                "problem": item.get("reason", item.get("next_step", "Turn a chosen idea into a usable app.")),
                "features": [
                    item.get("next_step", "Show the next action clearly"),
                    "Score value, effort, and risk",
                    "Provide a simple checklist",
                    "Keep publishing approval-gated",
                ],
                "safety": ["prototype only", "no external side effects", "approval required before publishing"],
            })
        backlog = self.store.read("apps", "blueprint_backlog.json", default=[])
        for item in reversed(backlog[-limit * 2:]):
            sources.append({
                "source_type": "blueprint",
                "source_id": item.get("id", "unknown"),
                "title": item.get("title", "Knowledge Tool"),
                "problem": item.get("problem", "Help users act on knowledge."),
                "features": item.get("core_features", [])[:5],
                "safety": item.get("safety_boundaries", [])[:5] or ["public information only", "approval before side effects"],
            })
        if not sources:
            matches = self.brain.hybrid_search("autonomous app idea prototype", project="Gizmo", limit=limit, include_trace=True)
            for _, memory in matches:
                sources.append({
                    "source_type": "memory",
                    "source_id": memory.id,
                    "title": memory.title,
                    "problem": memory.summary or memory.content[:300],
                    "features": ["Summarize the memory", "Extract decisions", "Create action checklist"],
                    "safety": ["public knowledge only", "prototype only"],
                })
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for source in sources:
            key = f"{source.get('source_type')}:{source.get('source_id')}"
            if key not in seen:
                seen.add(key)
                unique.append(source)
        return unique[:limit]

    def _prototype_from_source(self, source: dict[str, Any]) -> MiniAppPrototype:
        title = str(source.get("title") or "Autonomous Prototype")[:64]
        slug = self._slug(title)
        pid = f"proto-{slug}-{uuid4().hex[:6]}"[:72]
        return MiniAppPrototype(
            id=pid,
            title=title,
            source_type=str(source.get("source_type", "idea")),
            source_id=str(source.get("source_id", "unknown")),
            problem=str(source.get("problem", "Turn knowledge into a useful mobile tool."))[:700],
            features=[str(item)[:160] for item in source.get("features", [])[:6] if item],
            safety_boundaries=[str(item)[:160] for item in source.get("safety", [])[:6] if item],
            status="READY_FOR_REVIEW",
            approval_required=True,
            html_path="",
            manifest_path="",
        )

    @staticmethod
    def _slug(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug[:36] or "autonomous-app"

    def _render_html(self, prototype: MiniAppPrototype) -> str:
        title = html.escape(prototype.title)
        problem = html.escape(prototype.problem)
        features = "\n".join(f"<li class='bg-neutral-800 rounded-2lg p-3'>{html.escape(feature)}</li>" for feature in prototype.features)
        boundaries = "\n".join(f"<li class='text-neutral-300'>• {html.escape(boundary)}</li>" for boundary in prototype.safety_boundaries)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <link
    href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@300;400;500;600;700&display=swap"
    rel="stylesheet"
  />
  <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
  <script src="https://static.print.world/reaper-cdn/print-lol-tokens.js"></script>
</head>
<body class="font-rajdhani h-full bg-neutral-950 text-neutral-50 overflow-auto p-4">
  <main class="max-w-xl mx-auto space-y-4">
    <section class="bg-neutral-900 border border-primary/40 rounded-2_5xl p-5 shadow-glow">
      <p class="text-primary font-semibold uppercase tracking-wide text-sm">Autonomous prototype</p>
      <h1 class="text-3xl font-bold mt-2">{title}</h1>
      <p class="text-neutral-300 mt-3">{problem}</p>
    </section>
    <section class="bg-neutral-900 border border-neutral-800 rounded-2_5xl p-5">
      <h2 class="text-xl font-bold mb-3">Core Flow</h2>
      <ol class="space-y-2 text-neutral-300">
        <li>1. Paste a goal, idea, or context.</li>
        <li>2. Break it into decisions and blockers.</li>
        <li>3. Return a ranked checklist with uncertainty exposed.</li>
      </ol>
    </section>
    <section class="bg-neutral-900 border border-neutral-800 rounded-2_5xl p-5">
      <h2 class="text-xl font-bold mb-3">Features</h2>
      <ul class="space-y-2">{features}</ul>
    </section>
    <section class="bg-neutral-900 border border-neutral-800 rounded-2_5xl p-5">
      <h2 class="text-xl font-bold mb-3">Safety</h2>
      <ul class="space-y-1">{boundaries}</ul>
      <p class="text-primary mt-3 font-semibold">Status: ready for review. Publishing remains approval-gated.</p>
    </section>
  </main>
</body>
</html>
"""

    @staticmethod
    def _memory_text(prototype: MiniAppPrototype) -> str:
        return (
            f"Prototype: {prototype.title}\nSource: {prototype.source_type}:{prototype.source_id}\n"
            f"Problem: {prototype.problem}\nFeatures: {', '.join(prototype.features)}\n"
            f"Safety: {', '.join(prototype.safety_boundaries)}\nStatus: {prototype.status}"
        )
