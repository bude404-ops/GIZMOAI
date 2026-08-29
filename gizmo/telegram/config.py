"""Telegram control center configuration."""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any

REQUIRED_SECRET_NAMES = [
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_ADMIN_ID",
    "GITHUB_REPOSITORY",
    "REAPER_AUTH_SECRET",
]
OPTIONAL_SECRET_NAMES = [
    "GITHUB_APP_ID",
    "GITHUB_PRIVATE_KEY",
    "GITHUB_TOKEN",
    "REAPER_ENDPOINT",
]


@dataclass
class TelegramConfig:
    bot_token: str
    admin_ids: set[str]
    github_repository: str
    reaper_endpoint: str = "local-orchestrator"
    reaper_auth_secret_available: bool = False
    github_app_id_available: bool = False
    github_private_key_available: bool = False
    github_token_available: bool = False
    notification_min_priority: str = "NORMAL"
    daily_report_enabled: bool = False
    important_events_enabled: bool = True

    @classmethod
    def from_env(cls) -> "TelegramConfig":
        admin_raw = os.environ.get("TELEGRAM_ADMIN_ID", "")
        admin_ids = {item.strip() for item in admin_raw.replace(";", ",").split(",") if item.strip()}
        return cls(
            bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            admin_ids=admin_ids,
            github_repository=os.environ.get("GITHUB_REPOSITORY", "bude404-ops/GIZMOAI"),
            reaper_endpoint=os.environ.get("REAPER_ENDPOINT", "local-orchestrator"),
            reaper_auth_secret_available=bool(os.environ.get("REAPER_AUTH_SECRET")),
            github_app_id_available=bool(os.environ.get("GITHUB_APP_ID")),
            github_private_key_available=bool(os.environ.get("GITHUB_PRIVATE_KEY")),
            github_token_available=bool(os.environ.get("GITHUB_TOKEN")),
            notification_min_priority=os.environ.get("GIZMO_NOTIFICATION_MIN_PRIORITY", "NORMAL"),
            daily_report_enabled=os.environ.get("GIZMO_DAILY_REPORT", "false").lower() in {"1", "true", "yes", "on"},
            important_events_enabled=os.environ.get("GIZMO_IMPORTANT_EVENTS", "true").lower() in {"1", "true", "yes", "on"},
        )

    def validate_runtime(self) -> dict[str, Any]:
        missing = []
        if not self.bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.admin_ids:
            missing.append("TELEGRAM_ADMIN_ID")
        if not self.github_repository:
            missing.append("GITHUB_REPOSITORY")
        if not self.reaper_auth_secret_available:
            missing.append("REAPER_AUTH_SECRET")
        return {"ready": not missing, "missing": missing, "secrets": self.secret_status()}

    def secret_status(self) -> dict[str, bool]:
        return {
            "TELEGRAM_BOT_TOKEN": bool(self.bot_token),
            "TELEGRAM_ADMIN_ID": bool(self.admin_ids),
            "GITHUB_REPOSITORY": bool(self.github_repository),
            "REAPER_AUTH_SECRET": self.reaper_auth_secret_available,
            "GITHUB_APP_ID": self.github_app_id_available,
            "GITHUB_PRIVATE_KEY": self.github_private_key_available,
            "GITHUB_TOKEN": self.github_token_available,
        }

    def safe_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["bot_token"] = "[SET]" if self.bot_token else "[MISSING]"
        data["admin_ids"] = ["[CONFIGURED]"] if self.admin_ids else []
        return data
