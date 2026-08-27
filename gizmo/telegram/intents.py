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
        alias = self._from_plain_english_alias(raw, lowered)
        if alias:
            return alias
        return self._from_natural_language(raw, lowered)

    def _from_plain_english_alias(self, raw: str, lowered: str) -> TelegramIntent | None:
        compact = " ".join(lowered.replace("?", " ").replace("!", " ").split())
        exact: dict[str, tuple[str, str, dict[str, Any], bool, float]] = {
            "hi": ("start", "Open Telegram control center", {}, False, 0.98),
            "hello": ("start", "Open Telegram control center", {}, False, 0.98),
            "hey": ("start", "Open Telegram control center", {}, False, 0.98),
            "start": ("start", "Open Telegram control center", {}, False, 0.98),
            "help": ("help", "Show available commands", {}, False, 0.98),
            "commands": ("help", "Show available commands", {}, False, 0.96),
            "menu": ("help", "Show available commands", {}, False, 0.94),
            "status": ("status", "Show Gizmo status", {}, False, 0.99),
            "check status": ("status", "Show Gizmo status", {}, False, 0.98),
            "what is running": ("status", "Show Gizmo status", {}, False, 0.96),
            "what's running": ("status", "Show Gizmo status", {}, False, 0.96),
            "agents": ("agents", "Show agent registry", {}, False, 0.98),
            "show agents": ("agents", "Show agent registry", {}, False, 0.97),
            "tasks": ("tasks", "Show tasks", {}, False, 0.98),
            "show tasks": ("tasks", "Show tasks", {}, False, 0.97),
            "projects": ("projects", "Show projects", {}, False, 0.96),
            "logs": ("logs", "latest", {"filter": "latest"}, False, 0.96),
            "show logs": ("logs", "latest", {"filter": "latest"}, False, 0.96),
            "memory": ("memory", "Gizmo", {"query": "Gizmo"}, False, 0.94),
            "what did you learn": ("memory", "autonomous learning", {"query": "autonomous learning"}, False, 0.98),
            "what have you learned": ("memory", "autonomous learning", {"query": "autonomous learning"}, False, 0.98),
            "show what you learned": ("memory", "autonomous learning", {"query": "autonomous learning"}, False, 0.97),
            "start learning": ("learn", "autonomous cycle", {"raw_args": "autonomous cycle"}, False, 0.98),
            "begin learning": ("learn", "autonomous cycle", {"raw_args": "autonomous cycle"}, False, 0.98),
            "learn now": ("learn", "autonomous cycle", {"raw_args": "autonomous cycle"}, False, 0.98),
            "run learning cycle": ("learn", "autonomous cycle", {"raw_args": "autonomous cycle"}, False, 0.98),
            "become smarter": ("cloud_brain", "start smarter cloud work", {"raw_args": "start"}, False, 0.99),
            "start working": ("cloud_brain", "start multi-agent cloud work", {"raw_args": "start"}, False, 0.99),
            "start cloud brain": ("cloud_brain", "start cloud brain", {"raw_args": "start"}, False, 0.99),
            "run the agents": ("cloud_brain", "run multi-agent cloud work", {"raw_args": "run"}, False, 0.98),
            "make yourself smarter": ("cloud_brain", "start smarter cloud work", {"raw_args": "start"}, False, 0.98),
            "activate super ai": ("cloud_brain", "activate super ai", {"raw_args": "start"}, False, 0.99),
            "run super brain": ("cloud_brain", "run super brain", {"raw_args": "run"}, False, 0.99),
            "start super brain": ("cloud_brain", "start super brain", {"raw_args": "start"}, False, 0.99),
            "learn anything": ("universal_learn", "general", {"domain": "general"}, False, 0.97),
            "learn from all sources": ("universal_learn", "general", {"domain": "general"}, False, 0.98),
            "create app ideas": ("app_factory", "general", {"domain": "general"}, False, 0.98),
            "make app ideas": ("app_factory", "general", {"domain": "general"}, False, 0.98),
            "app factory": ("app_factory", "general", {"domain": "general"}, False, 0.98),
            "think for yourself": ("autonomous_think", "self improvement, app ideas, upgrades", {"raw_args": "self improvement, app ideas, upgrades"}, False, 0.99),
            "generate your own ideas": ("autonomous_think", "self improvement, app ideas, upgrades", {"raw_args": "self improvement, app ideas, upgrades"}, False, 0.99),
            "find your own upgrades": ("autonomous_think", "self improvement, app ideas, upgrades", {"raw_args": "self improvement, app ideas, upgrades"}, False, 0.99),
            "decide what to build next": ("autonomous_think", "app ideas, upgrades, operator friction", {"raw_args": "app ideas, upgrades, operator friction"}, False, 0.98),
            "enable learning": ("autonomous", "on", {"raw_args": "on"}, True, 0.98),
            "turn on learning": ("autonomous", "on", {"raw_args": "on"}, True, 0.98),
            "turn learning on": ("autonomous", "on", {"raw_args": "on"}, True, 0.98),
            "autonomous on": ("autonomous", "on", {"raw_args": "on"}, True, 0.98),
            "disable learning": ("autonomous", "off", {"raw_args": "off"}, False, 0.98),
            "turn off learning": ("autonomous", "off", {"raw_args": "off"}, False, 0.98),
            "pause": ("pause", "Pause autonomous work", {}, False, 0.95),
            "pause learning": ("pause", "Pause autonomous work", {}, False, 0.96),
            "resume": ("resume", "Resume autonomous work", {}, False, 0.95),
            "resume learning": ("resume", "Resume autonomous work", {}, False, 0.96),
            "stop": ("emergency_stop", "Emergency stop Gizmo", {}, True, 0.97),
            "stop everything": ("emergency_stop", "Emergency stop Gizmo", {}, True, 0.99),
            "run tests": ("test", "Run tests", {}, False, 0.95),
            "test": ("test", "Run tests", {}, False, 0.94),
        }
        if compact in exact:
            intent, objective, args, requires, confidence = exact[compact]
            return TelegramIntent(intent, "english", objective, requires_approval=requires, args=args, confidence=confidence)
        if compact.startswith(("remember ", "remember that ")):
            objective = raw.split(" ", 1)[1] if " " in raw else raw
            if objective.lower().startswith("that "):
                objective = objective[5:]
            return TelegramIntent("remember", "english", objective, args={"raw_args": objective}, confidence=0.94)
        if compact.startswith(("search memory for ", "find memory for ", "look up memory for ")):
            query = raw.split(" for ", 1)[1]
            return TelegramIntent("memory", "english", query, args={"query": query}, confidence=0.94)
        if compact.startswith(("learn about ", "study ", "research ")):
            domain = compact.replace("learn about ", "", 1).replace("study ", "", 1).replace("research ", "", 1).strip() or "general"
            return TelegramIntent("universal_learn", "english", raw, args={"domain": domain, "raw_args": raw}, confidence=0.93)
        if compact.startswith(("create app ideas from ", "make app ideas from ", "build apps from ")):
            domain = raw.split(" from ", 1)[1] if " from " in raw.lower() else raw
            return TelegramIntent("app_factory", "english", domain, args={"domain": domain}, confidence=0.93)
        if any(phrase in compact for phrase in ["think for yourself", "own ideas", "your own ideas", "own upgrades", "decide what to build", "what should you build", "upgrade yourself"]):
            return TelegramIntent("autonomous_think", "english", raw, args={"raw_args": raw}, confidence=0.92)
        if any(phrase in compact for phrase in ["become smarter", "make yourself smarter", "start working", "run the agents", "multi agents", "multi-agent", "cloud brain", "super brain", "super ai", "24/7", "twenty four seven"]):
            return TelegramIntent("cloud_brain", "english", raw, args={"raw_args": raw}, confidence=0.9)
        if compact.startswith(("build ", "make ", "create ", "implement ")):
            return TelegramIntent("build", "english", raw, priority="normal", confidence=0.9)
        if compact.startswith(("deploy ", "ship ", "release ")):
            return TelegramIntent("deploy", "english", raw, requires_approval=True, confidence=0.9)
        return None

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
