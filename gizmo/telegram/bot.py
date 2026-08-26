"""Telegram bot runtime without hard-coded credentials."""
from __future__ import annotations

import json
import time
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

    def poll_once(self, offset: int | None = None, *, send_replies: bool = False, acknowledge: bool = True, timeout: int = 30) -> dict[str, Any]:
        updates = self.get_updates(offset=offset, timeout=timeout)
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

    def poll_loop(self, *, duration_seconds: int = 3300, timeout: int = 25, send_replies: bool = True, acknowledge: bool = True, max_idle_cycles: int | None = None) -> dict[str, Any]:
        deadline = time.monotonic() + max(1, duration_seconds)
        offset: int | None = None
        cycles = 0
        idle_cycles = 0
        processed = 0
        replies_sent = 0
        errors: list[str] = []
        last_result: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            remaining = int(deadline - time.monotonic())
            if remaining <= 0:
                break
            effective_timeout = max(1, min(timeout, remaining))
            try:
                result = self.poll_once(offset=offset, send_replies=send_replies, acknowledge=acknowledge, timeout=effective_timeout)
            except Exception as exc:
                errors.append(type(exc).__name__)
                time.sleep(min(5, max(1, effective_timeout)))
                continue
            cycles += 1
            last_result = result
            if not result.get("ok"):
                errors.append(str(result.get("error", "poll_failed"))[:120])
                time.sleep(5)
                continue
            if result.get("next_offset") is not None:
                offset = result["next_offset"]
            count = len(result.get("results", []))
            processed += count
            if send_replies:
                replies_sent += count
            if count:
                idle_cycles = 0
            else:
                idle_cycles += 1
                if max_idle_cycles is not None and idle_cycles >= max_idle_cycles:
                    break
            if effective_timeout < 3:
                break
        return {"ok": not errors, "cycles": cycles, "processed": processed, "replies_sent": replies_sent, "last_offset": offset, "errors": errors[-5:], "last_result": last_result}

    def _send_route_reply(self, update: dict[str, Any], routed: dict[str, Any]) -> None:
        if not self.notifier:
            return
        message = update.get("message") or update.get("callback_query", {}).get("message") or {}
        chat = message.get("chat", {})
        chat_id = chat.get("id") or routed.get("task", {}).get("chat_id")
        if not chat_id:
            return
        self.notifier.send(str(chat_id), routed.get("message", "Command accepted."), routed.get("priority", "NORMAL"), routed.get("inline_buttons", []), execute=True)
