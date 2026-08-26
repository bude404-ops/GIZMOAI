"""Telegram authorization and command safety gates."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

SENSITIVE_COMMANDS = {"/deploy", "/stop", "/restart", "/approve", "/deny", "/autonomous"}
SENSITIVE_INTENTS = {"deploy", "emergency_stop", "restart", "approve", "deny", "autonomous"}
DENIAL_MESSAGE = "Access denied."


@dataclass
class AuthorizationResult:
    allowed: bool
    user_id: str
    reason: str
    sensitive: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TelegramAuthorizer:
    def __init__(self, allowed_user_ids: set[str]) -> None:
        self.allowed_user_ids = {str(item) for item in allowed_user_ids}

    def authorize(self, user_id: int | str | None, command: str = "", intent: str = "") -> AuthorizationResult:
        normalized = "" if user_id is None else str(user_id)
        sensitive = command.split()[0] in SENSITIVE_COMMANDS if command.startswith("/") else intent in SENSITIVE_INTENTS
        if not normalized or normalized not in self.allowed_user_ids:
            return AuthorizationResult(False, normalized, DENIAL_MESSAGE, sensitive=sensitive)
        return AuthorizationResult(True, normalized, "authorized", sensitive=sensitive)


def sanitize_for_telegram(text: str) -> str:
    redacted = text
    markers = ["token", "secret", "private_key", "authorization", "api_key", "password"]
    for marker in markers:
        redacted = redacted.replace(marker.upper(), "[REDACTED]").replace(marker, "[redacted]")
    return redacted[:3500]
