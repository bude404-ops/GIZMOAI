"""Telegram bot runtime without hard-coded credentials."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from gizmo.telegram.config import TelegramConfig
from gizmo.telegram.notifier import TelegramNotifier
from gizmo.telegram.router import TelegramCommandRouter


class TelegramBotRuntime:
    def __init__(self, config: TelegramConfig, router: TelegramCommandRouter, notifier: TelegramNotifier | None = None) -> None:
        self.config = config
        self.router = router
        self.notifier = notifier

    def handle_update(self, update: dict[str, Any]) -> dict[str, Any]:
        return self.router.route_update(update).to_dict()

    def get_updates(self, offset: int | None = None, timeout: int = 30) -> dict[str, Any]:
        if not self.config.bot_token:
            return {"ok": False, "error": "missing TELEGRAM_BOT_TOKEN"}
        query = {"timeout": timeout}
        if offset is not None:
            query["offset"] = offset
        url = f"https://api.telegram.org/bot{self.config.bot_token}/getUpdates?{urllib.parse.urlencode(query)}"
        with urllib.request.urlopen(url, timeout=timeout + 5) as response:
            return json.loads(response.read().decode("utf-8"))

    def poll_once(self, offset: int | None = None, *, send_replies: bool = False, acknowledge: bool = True) -> dict[str, Any]:
        updates = self.get_updates(offset=offset)
        if not updates.get("ok"):
            return updates
        results = []
        for update in updates.get("result", []):
            routed = self.handle_update(update)
            if send_replies:
                self._send_route_reply(update, routed)
            results.append(routed)
        next_offset = None
        if updates.get("result"):
            next_offset = max(item["update_id"] for item in updates["result"]) + 1
            if acknowledge:
                self.get_updates(offset=next_offset, timeout=1)
        return {"ok": True, "next_offset": next_offset, "results": results, "replies_sent": send_replies}

    def _send_route_reply(self, update: dict[str, Any], routed: dict[str, Any]) -> None:
        if not self.notifier:
            return
        message = update.get("message") or update.get("callback_query", {}).get("message") or {}
        chat = message.get("chat", {})
        chat_id = chat.get("id") or routed.get("task", {}).get("chat_id")
        if not chat_id:
            return
        self.notifier.send(str(chat_id), routed.get("message", "Command accepted."), routed.get("priority", "NORMAL"), routed.get("inline_buttons", []), execute=True)
