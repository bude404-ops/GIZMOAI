"""Obsidian-compatible markdown vault for the shared brain."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from gizmo.brain.models import BrainMemory

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
        readme = self.root / "README.md"
        if not readme.exists():
            readme.write_text("# Gizmo Second Brain\n\nPortable Obsidian-compatible knowledge vault.\n")

    def memory_path(self, memory: BrainMemory) -> Path:
        directory = TYPE_TO_DIR.get(memory.type.value, "memory")
        return self.root / directory / f"{memory.id}-{_slug(memory.title)}.md"

    def write_memory(self, memory: BrainMemory) -> Path:
        path = self.memory_path(memory)
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
        path.write_text("\n".join(lines))
        return path
