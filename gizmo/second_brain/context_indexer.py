"""Repository context indexer for GIZMO second brain."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
from typing import Any

TEXT_EXTENSIONS = {".py", ".md", ".yml", ".yaml", ".toml", ".json", ".txt", ".html", ".js", ".ts", ".css"}
EXCLUDED_PARTS = {".git", "__pycache__", ".pytest_cache", ".gizmo_runtime", "node_modules", "dist", "build"}


@dataclass
class ContextFile:
    path: str
    kind: str
    lines: int
    size: int
    digest: str
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RepoContextIndexer:
    def __init__(self, repo_path: Path, max_file_bytes: int = 120_000) -> None:
        self.repo_path = Path(repo_path)
        self.max_file_bytes = max_file_bytes

    def build_index(self) -> dict[str, Any]:
        files = [item.to_dict() for item in self._iter_context_files()]
        by_kind: dict[str, int] = {}
        for item in files:
            by_kind[item["kind"]] = by_kind.get(item["kind"], 0) + 1
        return {
            "repo": self.repo_path.name,
            "file_count": len(files),
            "by_kind": by_kind,
            "files": files,
        }

    def context_pack(self, query: str = "", limit: int = 12) -> dict[str, Any]:
        index = self.build_index()
        query_terms = [term.lower() for term in query.split() if term.strip()]
        scored = []
        for file in index["files"]:
            haystack = f"{file['path']} {file['summary']} {file['kind']}".lower()
            score = sum(2 if term in file["path"].lower() else 1 for term in query_terms if term in haystack)
            if not query_terms:
                score = self._default_importance(file)
            if score > 0:
                scored.append((score, file))
        scored.sort(key=lambda pair: (-pair[0], pair[1]["path"]))
        selected = [file for _, file in scored[:limit]]
        return {
            "query": query,
            "selected_count": len(selected),
            "files": selected,
            "guidance": [
                "Read architecture and policy docs before changing behavior.",
                "Keep high-risk GitHub writes approval-gated.",
                "Run tests and secret scan before proposing merge.",
            ],
        }

    def _iter_context_files(self):
        for path in sorted(self.repo_path.rglob("*")):
            if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.parts):
                continue
            if path.suffix not in TEXT_EXTENSIONS:
                continue
            if path.stat().st_size > self.max_file_bytes:
                continue
            relative = path.relative_to(self.repo_path).as_posix()
            text = path.read_text(errors="ignore")
            yield ContextFile(
                path=relative,
                kind=self._kind(relative),
                lines=text.count("\n") + (1 if text else 0),
                size=path.stat().st_size,
                digest=hashlib.sha256(text.encode()).hexdigest()[:16],
                summary=self._summarize(relative, text),
            )

    def _kind(self, path: str) -> str:
        if path.startswith("tests/"):
            return "test"
        if path.startswith("gizmo/documentation/") or path.endswith("README.md"):
            return "documentation"
        if path.startswith(".github/"):
            return "github-workflow"
        if path.startswith("gizmo/"):
            return "source"
        return "support"

    def _summarize(self, path: str, text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip().strip('#').strip()
            if stripped and not stripped.startswith(('from ', 'import ', '---')):
                return stripped[:160]
        return f"Context file {path}"

    def _default_importance(self, file: dict[str, Any]) -> int:
        path = file["path"]
        if path == "README.md":
            return 10
        if "orchestrator" in path or "second_brain" in path:
            return 9
        if file["kind"] == "documentation":
            return 7
        if file["kind"] == "test":
            return 5
        return 3
