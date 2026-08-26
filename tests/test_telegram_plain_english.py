from pathlib import Path

from gizmo.control.telegram_control import TelegramControlLayer
from gizmo.orchestrator.orchestrator import GizmoOrchestrator
from gizmo.telegram.config import TelegramConfig
from gizmo.telegram.router import TelegramCommandRouter
from gizmo.telegram.security import TelegramAuthorizer


def make_router(tmp_path: Path):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    config = TelegramConfig(bot_token="", admin_ids={"101"}, github_repository="owner/repo", reaper_auth_secret_available=True)
    control = TelegramControlLayer(orchestrator, config=config)
    router = TelegramCommandRouter(orchestrator.store, TelegramAuthorizer(config.admin_ids), control)
    return orchestrator, control, router


def test_plain_english_status_help_agents_and_tasks(tmp_path: Path):
    _, _, router = make_router(tmp_path)
    cases = {
        "status": "GIZMO STATUS",
        "help": "Commands",
        "agents": "AGENTS",
        "tasks": "TASKS",
        "what is running?": "GIZMO STATUS",
    }
    for text, expected in cases.items():
        result = router.route_text("101", "201", text)
        assert result.ok is True
        assert expected in result.message
        assert result.intent["command"] == "english"


def test_plain_english_learning_and_memory_phrases(tmp_path: Path):
    _, control, router = make_router(tmp_path)
    control.autonomous_learning.enable(chat_id="201")
    learn = router.route_text("101", "201", "begin learning")
    assert learn.ok is True
    assert learn.intent["intent"] == "learn"
    assert "AUTONOMOUS LEARNING COMPLETE" in learn.message

    memory = router.route_text("101", "201", "what did you learn?")
    assert memory.ok is True
    assert memory.intent["intent"] == "memory"
    assert "MEMORY" in memory.message


def test_plain_english_enable_learning_still_requires_approval(tmp_path: Path):
    _, _, router = make_router(tmp_path)
    result = router.route_text("101", "201", "turn on learning")
    assert result.ok is True
    assert result.intent["intent"] == "autonomous"
    assert result.priority == "APPROVAL_REQUIRED"
    assert result.inline_buttons


def test_plain_english_remember_and_search_memory(tmp_path: Path):
    _, _, router = make_router(tmp_path)
    remembered = router.route_text("101", "201", "remember that Telegram should answer simple English terms")
    assert remembered.ok is True
    assert remembered.intent["intent"] == "remember"
    found = router.route_text("101", "201", "search memory for simple English terms")
    assert found.ok is True
    assert "Telegram memory" in found.message or "simple English" in found.message


def test_plain_english_stop_remains_sensitive(tmp_path: Path):
    _, _, router = make_router(tmp_path)
    result = router.route_text("101", "201", "stop")
    assert result.intent["intent"] == "emergency_stop"
    assert result.authorization["sensitive"] is True
    assert result.priority == "URGENT"


def test_plain_english_unauthorized_user_still_denied(tmp_path: Path):
    _, _, router = make_router(tmp_path)
    result = router.route_text("999", "999", "status")
    assert result.ok is False
    assert result.message == "Access denied."
    assert result.intent["command"] == "english"
