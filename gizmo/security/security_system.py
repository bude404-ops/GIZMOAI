"""Security policy and emergency stop controls."""
from __future__ import annotations

from gizmo.core.models import OperatingMode
from gizmo.core.store import JsonStore


DESTRUCTIVE_ACTIONS = {"delete_repo", "force_push", "deploy_production", "modify_secrets", "change_owner_permissions"}


class SecuritySystem:
    def __init__(self, store: JsonStore) -> None:
        self.store = store

    def set_mode(self, mode: OperatingMode) -> None:
        self.store.write({"mode": mode.value}, "config", "mode.json")

    def mode(self) -> OperatingMode:
        data = self.store.read("config", "mode.json", default={"mode": OperatingMode.MANUAL.value})
        return OperatingMode(data["mode"])

    def emergency_stop(self) -> None:
        self.set_mode(OperatingMode.EMERGENCY)
        self.store.write({"stopped": True, "reason": "GIZMO STOP"}, "security", "emergency_stop.json")

    def require_approval(self, action: str, production: bool = False) -> bool:
        mode = self.mode()
        if mode == OperatingMode.EMERGENCY:
            return True
        if action in DESTRUCTIVE_ACTIONS or production:
            return True
        if mode == OperatingMode.MANUAL and action not in {"read", "plan", "test", "memory_write"}:
            return True
        if mode == OperatingMode.ASSISTED and action in {"merge", "deploy", "external_write"}:
            return True
        return False
