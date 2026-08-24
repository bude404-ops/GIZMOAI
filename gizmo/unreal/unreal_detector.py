"""Unreal Engine capability detection."""
from __future__ import annotations

import shutil
from pathlib import Path


class UnrealDetector:
    candidates = ["UnrealEditor", "UE4Editor", "RunUAT.sh", "RunUAT.bat"]

    def detect(self) -> dict:
        found = {name: shutil.which(name) for name in self.candidates if shutil.which(name)}
        common_paths = [Path("/opt/UnrealEngine"), Path.home() / "UnrealEngine"]
        existing = [str(path) for path in common_paths if path.exists()]
        return {
            "available": bool(found or existing),
            "commands": found,
            "paths": existing,
            "limitation": "Unreal automation unavailable in this environment" if not (found or existing) else "",
        }
