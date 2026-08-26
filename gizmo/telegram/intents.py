"""Rule-based command and natural-language intent detection for Telegram."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

COMMANDS = {
    "/start", "/help", "/status", "/agents", "/projects", "/tasks", "/task", "/run", "/stop",
    "/pause", "/resume", "/autonomous", "/learn", "/memory", "/remember", "/logs", "/build",
    "/test", "/deploy", "/approve", "/deny", "/restart",
}


@dataclass
class TelegramIntent:
    intent: str
    command: str
    objective: str
    priority: str = "normal"
    requires_approval: bool = False
    args: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.7

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class IntentDetector:
    def detect(self, text: str) -> TelegramIntent:
        raw = (text or "").strip()
        lowered = raw.lower()
        if not raw:
            return TelegramIntent("help", "/help", "Show help", confidence=1.0)
        if raw.startswith("/"):
            parts = raw.split(maxsplit=1)
            command = parts[0].lower()
            rest = parts[1] if len(parts) > 1 else ""
            return self._from_command(command, rest, raw)
        return self._from_natural_language(raw, lowered)

    def _from_command(self, command: str, rest: str, raw: str) -> TelegramIntent:
        mapping = {
            "/start": ("start", "Start Telegram control center"),
            "/help": ("help", "Show available commands"),
            "/status": ("status", "Show Gizmo status"),
            "/agents": ("agents", "Show agent registry"),
            "/projects": ("projects", "Show projects"),
            "/tasks": ("tasks", "Show tasks"),
            "/task": ("task_detail", rest or "Show task detail"),
            "/run": ("run", rest or "Run queued task"),
            "/stop": ("emergency_stop", "Emergency stop Gizmo"),
            "/pause": ("pause", "Pause autonomous work"),
            "/resume": ("resume", "Resume autonomous work"),
            "/autonomous": ("autonomous", rest or "Show autonomous mode"),
            "/learn": ("learn", rest or "Run learning cycle"),
            "/memory": ("memory", rest or "Search memory"),
            "/remember": ("remember", rest or "Store explicit memory"),
            "/logs": ("logs", rest or "latest"),
            "/build": ("build", rest or "Build requested artifact"),
            "/test": ("test", rest or "Run tests"),
            "/deploy": ("deploy", rest or "Deploy latest version"),
            "/approve": ("approve", rest or "Approve action"),
            "/deny": ("deny", rest or "Deny action"),
            "/restart": ("restart", "Restart orchestration layer"),
        }
        intent, objective = mapping.get(command, ("natural_task", raw))
        requires = intent in {"deploy", "restart", "emergency_stop", "approve", "deny"}
        if intent == "autonomous" and rest.lower().strip() in {"on", "enable", "enabled"}:
            requires = True
        return TelegramIntent(intent, command, objective, requires_approval=requires, args={"raw_args": rest}, confidence=1.0)

    def _from_natural_language(self, raw: str, lowered: str) -> TelegramIntent:
        if any(phrase in lowered for phrase in ["what's gizmo doing", "what is gizmo doing", "status", "what's running", "whats running"]):
            return TelegramIntent("status", "natural", raw, confidence=0.86)
        if any(phrase in lowered for phrase in ["what agents", "agents working", "who is working"]):
            return TelegramIntent("agents", "natural", raw, confidence=0.84)
        if "stop everything" in lowered or lowered.strip() in {"stop", "shutdown"}:
            return TelegramIntent("emergency_stop", "natural", raw, requires_approval=True, confidence=0.9)
        if "pause" in lowered and "autonomous" in lowered:
            return TelegramIntent("pause", "natural", raw, confidence=0.88)
        if "resume" in lowered:
            return TelegramIntent("resume", "natural", raw, confidence=0.82)
        if "what did" in lowered and "learn" in lowered:
            return TelegramIntent("memory", "natural", raw, args={"query": raw}, confidence=0.82)
        if "failure" in lowered or "failed" in lowered:
            return TelegramIntent("logs", "natural", raw, args={"filter": "failures"}, confidence=0.78)
        if "deploy" in lowered:
            return TelegramIntent("deploy", "natural", raw, requires_approval=True, confidence=0.8)
        if any(word in lowered for word in ["build", "create", "implement", "make"]):
            return TelegramIntent("build", "natural", raw, priority="normal", confidence=0.82)
        if "test" in lowered:
            return TelegramIntent("test", "natural", raw, confidence=0.75)
        if "next" in lowered and "work" in lowered:
            return TelegramIntent("learn", "natural", raw, confidence=0.72)
        return TelegramIntent("natural_task", "natural", raw, confidence=0.55)
