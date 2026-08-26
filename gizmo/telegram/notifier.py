"""Telegram notification formatting and delivery."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any

from gizmo.core.models import now_iso
from gizmo.core.store import JsonStore
from gizmo.telegram.security import sanitize_for_telegram

PRIORITY_ORDER = {"LOW": 10, "NORMAL": 20, "IMPORTANT": 30, "URGENT": 40, "APPROVAL_REQUIRED": 50, "FAILURE": 60, "SECURITY": 70}


@dataclass
class TelegramNotification:
    chat_id: str
    text: str
    priority: str = "NORMAL"
    inline_buttons: list[list[dict[str, str]]] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    status: str = "QUEUED"
    result: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TelegramNotifier:
    def __init__(self, store: JsonStore, bot_token: str = "", min_priority: str = "NORMAL") -> None:
        self.store = store
        self.bot_token = bot_token
        self.min_priority = min_priority

    def should_send(self, priority: str) -> bool:
        return PRIORITY_ORDER.get(priority, 20) >= PRIORITY_ORDER.get(self.min_priority, 20)

    def queue(self, chat_id: str, text: str, priority: str = "NORMAL", inline_buttons: list[list[dict[str, str]]] | None = None) -> TelegramNotification:
        note = TelegramNotification(chat_id=str(chat_id), text=sanitize_for_telegram(text), priority=priority, inline_buttons=inline_buttons or [])
        self.store.append_list(note.to_dict(), "telegram", "notifications.json")
        return note

    def send(self, chat_id: str, text: str, priority: str = "NORMAL", inline_buttons: list[list[dict[str, str]]] | None = None, execute: bool = False) -> TelegramNotification:
        note = self.queue(chat_id, text, priority, inline_buttons)
        if not execute or not self.bot_token or not self.should_send(priority):
            note.status = "PLANNED" if not execute else "SKIPPED"
            self.store.append_list(note.to_dict(), "telegram", "notification_results.json")
            return note
        payload = {"chat_id": str(chat_id), "text": note.text, "parse_mode": "HTML"}
        if note.inline_buttons:
            payload["reply_markup"] = {"inline_keyboard": note.inline_buttons}
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                note.status = "SENT"
                note.result = {"ok": True, "status": response.status}
        except urllib.error.URLError as exc:
            note.status = "FAILED"
            note.result = {"ok": False, "error": str(exc)}
        self.store.append_list(note.to_dict(), "telegram", "notification_results.json")
        return note
