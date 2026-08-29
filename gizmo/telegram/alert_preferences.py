"""Owner-controlled Telegram alert preferences for GIZMO."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from gizmo.telegram.notifier import PRIORITY_ORDER

DEFAULT_CATEGORIES = {
    "progress",
    "campaign",
    "approval",
    "failure_learning",
    "health",
    "cycle",
}

CATEGORY_ALIASES = {
    "progress": "progress",
    "stalled": "progress",
    "mixed": "progress",
    "campaign": "campaign",
    "milestone": "campaign",
    "approval": "approval",
    "approvals": "approval",
    "failure": "failure_learning",
    "failures": "failure_learning",
    "learning": "failure_learning",
    "health": "health",
    "risk": "health",
    "cycle": "cycle",
    "cloud": "cycle",
}


@dataclass
class AlertPreferences:
    enabled: bool = True
    min_priority: str = "IMPORTANT"
    categories: list[str] = field(default_factory=lambda: sorted(DEFAULT_CATEGORIES))
    quiet_hours_enabled: bool = False
    quiet_hours_start: int = 23
    quiet_hours_end: int = 7
    quiet_hours_allow: list[str] = field(default_factory=lambda: ["URGENT", "APPROVAL_REQUIRED", "FAILURE", "SECURITY"])
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TelegramAlertPreferenceStore:
    """Persist and apply alert preferences."""

    def __init__(self, store: Any) -> None:
        self.store = store

    def load(self) -> AlertPreferences:
        raw = self.store.read("telegram", "alert_preferences.json", default=None)
        if not raw:
            return AlertPreferences()
        defaults = AlertPreferences().to_dict()
        defaults.update({k: v for k, v in raw.items() if k in defaults})
        defaults["categories"] = self._normalize_categories(defaults.get("categories", []))
        defaults["min_priority"] = self._normalize_priority(defaults.get("min_priority", "IMPORTANT"))
        defaults["quiet_hours_allow"] = [self._normalize_priority(p) for p in defaults.get("quiet_hours_allow", [])]
        return AlertPreferences(**defaults)

    def save(self, prefs: AlertPreferences) -> AlertPreferences:
        prefs.categories = self._normalize_categories(prefs.categories)
        prefs.min_priority = self._normalize_priority(prefs.min_priority)
        prefs.quiet_hours_allow = [self._normalize_priority(p) for p in prefs.quiet_hours_allow]
        prefs.updated_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        self.store.write(prefs.to_dict(), "telegram", "alert_preferences.json")
        self.store.append_list(prefs.to_dict(), "telegram", "alert_preferences_history.json")
        return prefs

    def update_from_text(self, text: str) -> tuple[AlertPreferences, list[str]]:
        prefs = self.load()
        raw = (text or "").strip()
        words = raw.lower().replace(",", " ").split()
        changes: list[str] = []
        if not words or words[0] in {"show", "status", "view", "check"}:
            return prefs, changes
        if words[0] in {"on", "enable", "enabled"}:
            prefs.enabled = True
            changes.append("enabled alerts")
        elif words[0] in {"off", "disable", "disabled", "mute"}:
            prefs.enabled = False
            changes.append("disabled alerts")
        elif words[0] in {"min", "minimum", "priority"} and len(words) >= 2:
            priority = self._normalize_priority(words[-1])
            prefs.min_priority = priority
            changes.append(f"minimum priority {priority}")
        elif words[0] in {"only"} and len(words) >= 2:
            cats = self._normalize_categories(words[1:])
            if cats:
                prefs.categories = cats
                changes.append("categories " + ", ".join(cats))
        elif words[0] in {"add", "include"} and len(words) >= 2:
            cats = sorted(set(prefs.categories) | set(self._normalize_categories(words[1:])))
            prefs.categories = cats
            changes.append("added categories " + ", ".join(cats))
        elif words[0] in {"remove", "exclude"} and len(words) >= 2:
            remove = set(self._normalize_categories(words[1:]))
            prefs.categories = sorted([cat for cat in prefs.categories if cat not in remove])
            changes.append("removed categories " + ", ".join(sorted(remove)))
        elif words[0] in {"quiet", "quiet-hours"}:
            change = self._apply_quiet_hours(prefs, words[1:])
            changes.append(change)
        elif words[0] == "reset":
            prefs = AlertPreferences()
            changes.append("reset defaults")
        if changes:
            prefs = self.save(prefs)
        return prefs, changes

    def allows(self, event: Any, *, now_hour: int | None = None) -> tuple[bool, str]:
        prefs = self.load()
        if not prefs.enabled:
            return False, "alerts disabled"
        priority = self._normalize_priority(getattr(event, "priority", "NORMAL"))
        category = self.category_for(event)
        if category not in set(prefs.categories):
            return False, f"category {category} muted"
        if PRIORITY_ORDER.get(priority, 0) < PRIORITY_ORDER.get(prefs.min_priority, 30):
            return False, f"priority below {prefs.min_priority}"
        hour = datetime.utcnow().hour if now_hour is None else now_hour
        if prefs.quiet_hours_enabled and self._in_quiet_hours(hour, prefs.quiet_hours_start, prefs.quiet_hours_end):
            allowed = {self._normalize_priority(p) for p in prefs.quiet_hours_allow}
            if priority not in allowed:
                return False, "quiet hours"
        return True, "allowed"

    @staticmethod
    def category_for(event: Any) -> str:
        source = str(getattr(event, "source", "") or "").lower()
        priority = str(getattr(event, "priority", "") or "").upper()
        title = str(getattr(event, "title", "") or "").lower()
        if priority == "APPROVAL_REQUIRED" or "approval" in source or "approval" in title:
            return "approval"
        if "progress" in source:
            return "progress"
        if "campaign" in source or "tracker" in source or "milestone" in title:
            return "campaign"
        if "failure" in source or "learn" in source:
            return "failure_learning"
        if "health" in source or "risk" in title:
            return "health"
        return "cycle"

    @staticmethod
    def _in_quiet_hours(hour: int, start: int, end: int) -> bool:
        hour = max(0, min(23, int(hour)))
        start = max(0, min(23, int(start)))
        end = max(0, min(23, int(end)))
        if start == end:
            return False
        if start < end:
            return start <= hour < end
        return hour >= start or hour < end

    @classmethod
    def _normalize_categories(cls, cats: list[str]) -> list[str]:
        normalized = []
        for cat in cats:
            mapped = CATEGORY_ALIASES.get(str(cat).lower().replace("-", "_"))
            if mapped and mapped not in normalized:
                normalized.append(mapped)
        return sorted(normalized or DEFAULT_CATEGORIES)

    @staticmethod
    def _normalize_priority(priority: str) -> str:
        candidate = str(priority or "IMPORTANT").upper().replace("-", "_")
        return candidate if candidate in PRIORITY_ORDER else "IMPORTANT"

    def _apply_quiet_hours(self, prefs: AlertPreferences, words: list[str]) -> str:
        if not words or words[0] in {"on", "enable", "enabled"}:
            prefs.quiet_hours_enabled = True
            return "enabled quiet hours"
        if words[0] in {"off", "disable", "disabled"}:
            prefs.quiet_hours_enabled = False
            return "disabled quiet hours"
        joined = " ".join(words)
        if "-" in joined:
            left, right = joined.split("-", 1)
            prefs.quiet_hours_start = self._parse_hour(left, prefs.quiet_hours_start)
            prefs.quiet_hours_end = self._parse_hour(right, prefs.quiet_hours_end)
            prefs.quiet_hours_enabled = True
            return f"quiet hours {prefs.quiet_hours_start}:00-{prefs.quiet_hours_end}:00"
        return "quiet hours unchanged"

    @staticmethod
    def _parse_hour(value: str, fallback: int) -> int:
        digits = "".join(ch for ch in value if ch.isdigit())
        if not digits:
            return fallback
        return max(0, min(23, int(digits[:2])))
