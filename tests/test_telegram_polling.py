from pathlib import Path

from gizmo.control.telegram_control import TelegramControlLayer
from gizmo.orchestrator.orchestrator import GizmoOrchestrator
from gizmo.telegram.bot import TelegramBotRuntime
from gizmo.telegram.config import TelegramConfig
from gizmo.telegram.notifier import TelegramNotification, TelegramNotifier
from gizmo.telegram.router import TelegramCommandRouter
from gizmo.telegram.security import TelegramAuthorizer


class FakeNotifier(TelegramNotifier):
    def __init__(self):
        self.sent = []

    def queue(self, chat_id, text, priority="NORMAL", inline_buttons=None):
        note = TelegramNotification(str(chat_id), text, priority, inline_buttons or [])
        self.sent.append({"mode": "queue", "chat_id": str(chat_id), "text": text, "priority": priority, "inline_buttons": inline_buttons or []})
        return note

    def send(self, chat_id, text, priority="NORMAL", inline_buttons=None, execute=False):
        note = TelegramNotification(str(chat_id), text, priority, inline_buttons or [], status="SENT" if execute else "PLANNED")
        self.sent.append({"mode": "send", "chat_id": str(chat_id), "text": text, "priority": priority, "inline_buttons": inline_buttons or [], "execute": execute})
        return note


def test_poll_once_sends_status_reply_and_acknowledges_offset(tmp_path: Path):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    config = TelegramConfig(bot_token="test-token", admin_ids={"101"}, github_repository="owner/repo", reaper_auth_secret_available=True)
    notifier = FakeNotifier()
    control = TelegramControlLayer(orchestrator, config=config, notifier=notifier)
    router = TelegramCommandRouter(orchestrator.store, TelegramAuthorizer(config.admin_ids), control)
    runtime = TelegramBotRuntime(config, router, notifier)
    calls = []

    def fake_get_updates(offset=None, timeout=30):
        calls.append({"offset": offset, "timeout": timeout})
        if offset is None:
            return {"ok": True, "result": [{"update_id": 50, "message": {"from": {"id": 101}, "chat": {"id": 201}, "text": "/status"}}]}
        return {"ok": True, "result": []}

    runtime.get_updates = fake_get_updates
    result = runtime.poll_once(send_replies=True, acknowledge=True)

    assert result["ok"] is True
    assert result["next_offset"] == 51
    assert calls[-1]["offset"] == 51
    assert any(item["mode"] == "send" and item["chat_id"] == "201" and "GIZMO STATUS" in item["text"] for item in notifier.sent)


def test_poll_once_sends_denial_for_unknown_user(tmp_path: Path):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    config = TelegramConfig(bot_token="test-token", admin_ids={"101"}, github_repository="owner/repo", reaper_auth_secret_available=True)
    notifier = FakeNotifier()
    control = TelegramControlLayer(orchestrator, config=config, notifier=notifier)
    router = TelegramCommandRouter(orchestrator.store, TelegramAuthorizer(config.admin_ids), control)
    runtime = TelegramBotRuntime(config, router, notifier)
    runtime.get_updates = lambda offset=None, timeout=30: {"ok": True, "result": []} if offset else {"ok": True, "result": [{"update_id": 77, "message": {"from": {"id": 999}, "chat": {"id": 999}, "text": "/status"}}]}

    result = runtime.poll_once(send_replies=True, acknowledge=True)

    assert result["ok"] is True
    assert result["results"][0]["ok"] is False
    assert any(item["text"] == "Access denied." and item["priority"] == "SECURITY" for item in notifier.sent)
