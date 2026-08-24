"""JSON persistence utilities for local, auditable GIZMO state."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, *parts: str) -> Path:
        path = self.root.joinpath(*parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def read(self, *parts: str, default: Any = None) -> Any:
        path = self.path(*parts)
        if not path.exists():
            return default
        return json.loads(path.read_text())

    def write(self, data: Any, *parts: str) -> Path:
        path = self.path(*parts)
        path.write_text(json.dumps(data, indent=2, sort_keys=True))
        return path

    def append_list(self, item: Any, *parts: str) -> Path:
        current = self.read(*parts, default=[])
        if not isinstance(current, list):
            raise TypeError(f"store path is not a list: {'/'.join(parts)}")
        current.append(item)
        return self.write(current, *parts)
