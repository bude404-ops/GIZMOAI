"""Controlled Unreal Engine bridge manifest and automation helpers."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from gizmo.core.models import now_iso
from gizmo.core.store import JsonStore
from gizmo.unreal.unreal_detector import UnrealDetector


@dataclass
class UnrealBridgeReport:
    requested_project: str
    objective: str
    detected: dict[str, Any]
    bridge_available: bool
    automation_interfaces: list[str]
    planned_files: list[str]
    required_evidence: list[str]
    blockers: list[str]
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class UnrealIntegrationLayer:
    def __init__(self, store: JsonStore, detector: UnrealDetector | None = None) -> None:
        self.store = store
        self.detector = detector or UnrealDetector()

    def inspect(self, project_path: str | None = None, objective: str = "") -> UnrealBridgeReport:
        detected = self.detector.detect()
        project = Path(project_path).expanduser() if project_path else None
        project_exists = bool(project is not None and project.exists())
        uproject = list(project.glob("*.uproject")) if project is not None and project_exists else []
        bridge_available = bool(detected.get("available") or detected.get("editor") or uproject)
        blockers: list[str] = []
        if not project_exists and project_path:
            blockers.append("requested Unreal project path does not exist")
        if not bridge_available:
            blockers.append("Unreal editor/project bridge not detected in current environment")
        report = UnrealBridgeReport(
            requested_project=str(project) if project else "unspecified",
            objective=objective,
            detected={**detected, "project_exists": project_exists, "uproject_files": [p.name for p in uproject]},
            bridge_available=bridge_available,
            automation_interfaces=["Unreal Python Editor scripting", "C++ source generation", "Blueprint-supporting asset scripts", "command-line build/test logs"],
            planned_files=["Content/Python", "Source", "Config", "Saved/Logs"],
            required_evidence=["uproject file", "generated script/source diff", "Unreal command output", "error log inspection", "playable/package proof when requested"],
            blockers=blockers,
        )
        self.store.write(report.to_dict(), "unreal", "bridge_latest.json")
        self.store.append_list(report.to_dict(), "unreal", "bridge_history.json")
        return report

    def python_level_script(self, level_name: str = "GizmoPrototype") -> str:
        return f'''# Generated Unreal Python automation scaffold for {level_name}\nimport unreal\n\nasset_tools = unreal.AssetToolsHelpers.get_asset_tools()\neditor_level = unreal.EditorLevelLibrary\nworld = editor_level.get_editor_world()\n# Create or open a level, spawn placeholder actors, then save through official Unreal editor APIs.\n# This script must be executed inside Unreal Editor Python, not treated as proof until run logs exist.\n'''
