"""Obsidian-compatible markdown vault for the shared brain."""
from __future__ import annotations

from collections import defaultdict
import json
import re
from pathlib import Path
from typing import Any

from gizmo.brain.models import BrainMemory
from gizmo.core.models import now_iso

VAULT_DIRS = [
    "memory", "facts", "decisions", "preferences", "lessons", "experiences",
    "projects", "research", "experiments", "goals", "evaluations", "agents",
    "tasks", "sessions", "archive", "inbox",
]

TYPE_TO_DIR = {
    "FACT": "facts", "DECISION": "decisions", "PREFERENCE": "preferences", "LESSON": "lessons",
    "EXPERIENCE": "experiences", "PROJECT_STATE": "projects", "TASK": "tasks", "RESEARCH": "research",
    "CONVERSATION": "sessions", "AGENT_MEMORY": "agents", "RELATIONSHIP": "memory", "WARNING": "memory",
    "IDEA": "inbox", "HYPOTHESIS": "research", "EXPERIMENT": "experiments", "EVALUATION": "evaluations",
    "GOAL": "goals", "PROCEDURE": "memory", "SKILL": "memory",
}


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:80] or "memory"


def _yaml_value(value: Any) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(repr(str(v)) for v in value) + "]"
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return "null"
    return repr(str(value))


class ObsidianVault:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.initialize()

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        for directory in VAULT_DIRS:
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        (self.root / "graph").mkdir(parents=True, exist_ok=True)
        (self.root / "indexes").mkdir(parents=True, exist_ok=True)
        (self.root / "revisions").mkdir(parents=True, exist_ok=True)
        readme = self.root / "README.md"
        if not readme.exists():
            readme.write_text("# Gizmo Second Brain\n\nPortable Obsidian-compatible knowledge vault.\n")

    def memory_path(self, memory: BrainMemory) -> Path:
        directory = TYPE_TO_DIR.get(memory.type.value, "memory")
        return self.root / directory / f"{memory.id}-{_slug(memory.title)}.md"

    def write_memory(self, memory: BrainMemory) -> Path:
        path = self.memory_path(memory)
        if path.exists():
            self._write_revision(memory, path.read_text())
        frontmatter = {
            "id": memory.id,
            "type": memory.type.value,
            "title": memory.title,
            "project": memory.project,
            "importance": memory.importance,
            "confidence": memory.confidence,
            "status": memory.status.value,
            "source": memory.source,
            "source_agent": memory.source_agent,
            "created_at": memory.created_at,
            "updated_at": memory.updated_at,
            "last_accessed": memory.last_accessed,
            "access_count": memory.access_count,
            "tags": memory.tags,
            "entities": memory.entities,
            "supersedes": memory.supersedes,
            "superseded_by": memory.superseded_by,
        }
        lines = ["---"] + [f"{k}: {_yaml_value(v)}" for k, v in frontmatter.items()] + ["---", ""]
        lines += [f"# {memory.title}", "", f"> {memory.summary}", "", memory.content, ""]
        if memory.entities:
            lines += ["## Entities", ""] + [f"- [[{entity}]]" for entity in memory.entities] + [""]
        if memory.relationships:
            lines += ["## Relationships", ""]
            for rel in memory.relationships:
                lines.append(f"- `{rel.relation}` → [[{rel.target_id}]]")
            lines.append("")
        if memory.supersedes or memory.superseded_by:
            lines += ["## Temporal Memory", ""]
            lines += [f"- Supersedes: [[{item}]]" for item in memory.supersedes]
            lines += [f"- Superseded by: [[{item}]]" for item in memory.superseded_by]
            lines.append("")
        path.write_text("\n".join(lines))
        return path

    def rebuild_indexes(self, memories: list[BrainMemory]) -> dict[str, Any]:
        self.initialize()
        active = [m for m in memories if m.status.value == "ACTIVE"]
        by_type: dict[str, list[BrainMemory]] = defaultdict(list)
        by_project: dict[str, list[BrainMemory]] = defaultdict(list)
        by_agent: dict[str, list[BrainMemory]] = defaultdict(list)
        for memory in memories:
            by_type[memory.type.value].append(memory)
            by_project[memory.project].append(memory)
            by_agent[memory.source_agent].append(memory)
        self._write_home(memories, active, by_type, by_project, by_agent)
        self._write_type_indexes(by_type)
        self._write_project_pages(by_project)
        self._write_agent_pages(by_agent)
        graph = self._write_graph(memories)
        backlink_report = self._write_backlinks(memories)
        stale_report = self._write_quality_reports(memories)
        session_note = self.write_session_note("vault-rebuild", "Vault indexes, graph, backlinks, and reports regenerated.", memories[:12])
        return {
            "memories": len(memories),
            "active": len(active),
            "type_indexes": len(by_type),
            "project_pages": len(by_project),
            "agent_pages": len(by_agent),
            "graph_nodes": len(graph["nodes"]),
            "graph_edges": len(graph["edges"]),
            "backlinks": backlink_report["links"],
            "stale_or_conflicting": stale_report["flagged"],
            "session_note": str(session_note.name),
        }

    def write_session_note(self, title: str, summary: str, memories: list[BrainMemory] | None = None) -> Path:
        slug = _slug(title)
        path = self.root / "sessions" / f"{now_iso()[:10]}-{slug}.md"
        lines = ["---", f"title: {_yaml_value(title)}", "type: 'SESSION_NOTE'", f"created_at: {_yaml_value(now_iso())}", "---", "", f"# {title}", "", summary, ""]
        if memories:
            lines += ["## Referenced memories", ""]
            for memory in memories:
                lines.append(f"- [[{memory.id}]] — {memory.title}")
        path.write_text("\n".join(lines))
        return path

    def _write_revision(self, memory: BrainMemory, previous_markdown: str) -> Path:
        revision_dir = self.root / "revisions" / memory.id
        revision_dir.mkdir(parents=True, exist_ok=True)
        path = revision_dir / f"{now_iso().replace(':', '-')}.md"
        path.write_text(previous_markdown)
        return path

    def _write_home(self, memories: list[BrainMemory], active: list[BrainMemory], by_type: dict[str, list[BrainMemory]], by_project: dict[str, list[BrainMemory]], by_agent: dict[str, list[BrainMemory]]) -> None:
        lines = [
            "# Gizmo Second Brain",
            "",
            "Portable Obsidian-compatible knowledge vault for Gizmo.",
            "",
            "## Health",
            "",
            f"- Memories: **{len(memories)}**",
            f"- Active: **{len(active)}**",
            f"- Memory types: **{len(by_type)}**",
            f"- Projects: **{len(by_project)}**",
            f"- Agents: **{len(by_agent)}**",
            "",
            "## Navigation",
            "",
            "- [[indexes/Memory Index]]",
            "- [[indexes/Project Index]]",
            "- [[indexes/Agent Index]]",
            "- [[graph/Knowledge Graph]]",
            "- [[graph/Backlinks]]",
            "- [[indexes/Quality Report]]",
            "",
        ]
        self.root.joinpath("README.md").write_text("\n".join(lines))

    def _write_type_indexes(self, by_type: dict[str, list[BrainMemory]]) -> None:
        lines = ["# Memory Index", ""]
        for memory_type, items in sorted(by_type.items()):
            lines += [f"## {memory_type}", ""]
            for memory in sorted(items, key=lambda m: (-m.importance, m.title)):
                lines.append(f"- [[{memory.id}]] — {memory.title} `confidence:{memory.confidence}` `status:{memory.status.value}`")
            lines.append("")
        self.root.joinpath("indexes", "Memory Index.md").write_text("\n".join(lines))

    def _write_project_pages(self, by_project: dict[str, list[BrainMemory]]) -> None:
        index = ["# Project Index", ""]
        for project, items in sorted(by_project.items()):
            page = self.root / "projects" / f"Project-{_slug(project)}.md"
            index.append(f"- [[Project-{_slug(project)}|{project}]] — {len(items)} memories")
            lines = ["---", f"project: {_yaml_value(project)}", "type: 'PROJECT_PAGE'", "---", "", f"# {project}", ""]
            for memory_type in sorted({m.type.value for m in items}):
                lines += [f"## {memory_type}", ""]
                for memory in [m for m in items if m.type.value == memory_type]:
                    lines.append(f"- [[{memory.id}]] — {memory.title}")
                lines.append("")
            page.write_text("\n".join(lines))
        self.root.joinpath("indexes", "Project Index.md").write_text("\n".join(index))

    def _write_agent_pages(self, by_agent: dict[str, list[BrainMemory]]) -> None:
        index = ["# Agent Index", ""]
        for agent, items in sorted(by_agent.items()):
            page = self.root / "agents" / f"Agent-{_slug(agent)}.md"
            index.append(f"- [[Agent-{_slug(agent)}|{agent}]] — {len(items)} memories")
            lines = ["---", f"agent: {_yaml_value(agent)}", "type: 'AGENT_PAGE'", "---", "", f"# {agent}", ""]
            lines += ["## Knowledge contributed", ""]
            for memory in sorted(items, key=lambda m: m.created_at):
                lines.append(f"- [[{memory.id}]] — {memory.title}")
            page.write_text("\n".join(lines))
        self.root.joinpath("indexes", "Agent Index.md").write_text("\n".join(index))

    def _write_graph(self, memories: list[BrainMemory]) -> dict[str, Any]:
        nodes = [{"id": m.id, "title": m.title, "type": m.type.value, "project": m.project, "importance": m.importance} for m in memories]
        edges = []
        for memory in memories:
            for rel in memory.relationships:
                edges.append({"source": rel.source_id, "relation": rel.relation, "target": rel.target_id, "confidence": rel.confidence})
            for target in memory.supersedes:
                edges.append({"source": memory.id, "relation": "supersedes", "target": target, "confidence": 1.0})
            for target in memory.superseded_by:
                edges.append({"source": memory.id, "relation": "superseded_by", "target": target, "confidence": 1.0})
        graph = {"generated_at": now_iso(), "nodes": nodes, "edges": edges}
        self.root.joinpath("graph", "knowledge-graph.json").write_text(json.dumps(graph, indent=2, sort_keys=True))
        md = ["# Knowledge Graph", "", f"Nodes: **{len(nodes)}**", f"Edges: **{len(edges)}**", "", "## Edges", ""]
        for edge in edges:
            md.append(f"- [[{edge['source']}]] `{edge['relation']}` [[{edge['target']}]]")
        self.root.joinpath("graph", "Knowledge Graph.md").write_text("\n".join(md))
        return graph

    def _write_backlinks(self, memories: list[BrainMemory]) -> dict[str, Any]:
        backlinks: dict[str, list[str]] = defaultdict(list)
        known_ids = {m.id for m in memories}
        for memory in memories:
            for rel in memory.relationships:
                backlinks[rel.target_id].append(memory.id)
            for entity in memory.entities:
                if entity in known_ids:
                    backlinks[entity].append(memory.id)
        lines = ["# Backlinks", ""]
        link_count = 0
        for target, sources in sorted(backlinks.items()):
            lines += [f"## [[{target}]]", ""]
            for source in sorted(set(sources)):
                lines.append(f"- linked from [[{source}]]")
                link_count += 1
            lines.append("")
        self.root.joinpath("graph", "Backlinks.md").write_text("\n".join(lines))
        self.root.joinpath("graph", "backlinks.json").write_text(json.dumps(backlinks, indent=2, sort_keys=True))
        return {"links": link_count}

    def _write_quality_reports(self, memories: list[BrainMemory]) -> dict[str, Any]:
        flagged = [m for m in memories if m.status.value in {"CONFLICTING", "SUPERSEDED"} or m.confidence < 0.45]
        lines = ["# Quality Report", "", "## Stale, conflicting, or low-confidence knowledge", ""]
        if not flagged:
            lines.append("No stale, conflicting, or low-confidence memories found in this rebuild.")
        for memory in flagged:
            lines.append(f"- [[{memory.id}]] — {memory.title} `status:{memory.status.value}` `confidence:{memory.confidence}`")
        self.root.joinpath("indexes", "Quality Report.md").write_text("\n".join(lines))
        return {"flagged": len(flagged)}
