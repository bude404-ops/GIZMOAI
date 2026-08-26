from pathlib import Path

from gizmo.control.autonomous_learning import TelegramAutonomousKnowledgeRunner
from gizmo.control.telegram_control import TelegramControlLayer
from gizmo.orchestrator.orchestrator import GizmoOrchestrator
from gizmo.telegram.config import TelegramConfig
from gizmo.telegram.router import TelegramCommandRouter
from gizmo.telegram.security import TelegramAuthorizer


def make_control(tmp_path: Path):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    config = TelegramConfig(bot_token="", admin_ids={"7257834686"}, github_repository="bude404-ops/GIZMOAI", reaper_auth_secret_available=True)
    control = TelegramControlLayer(orchestrator, config=config)
    router = TelegramCommandRouter(orchestrator.store, TelegramAuthorizer(config.admin_ids), control)
    return orchestrator, control, router


def test_autonomous_learning_skips_when_disabled(tmp_path: Path):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    runner = TelegramAutonomousKnowledgeRunner(orchestrator)
    cycle = runner.run_cycle(chat_id="7257834686")
    assert cycle.status == "SKIPPED"
    assert "SKIPPED" in cycle.notification
    assert not cycle.memories_created


def test_enabled_autonomous_learning_creates_memory_tasks_and_vault_indexes(tmp_path: Path):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    runner = TelegramAutonomousKnowledgeRunner(orchestrator)
    runner.enable(chat_id="7257834686")
    cycle = runner.run_cycle(chat_id="7257834686", topics=["Telegram autonomous knowledge"])
    assert cycle.status == "COMPLETED"
    assert len(cycle.memories_created) >= 3
    assert len(cycle.tasks_created) == 1
    assert cycle.vault_report["memories"] >= 3
    memory_titles = [m.title for m in orchestrator.brain_core.hybrid_search("Telegram autonomous knowledge", project="Gizmo", limit=10)]
    assert any("Autonomous scan" in title for title in memory_titles)


def test_telegram_learn_autonomous_cycle_runs_when_enabled(tmp_path: Path):
    orchestrator, control, router = make_control(tmp_path)
    control.autonomous_learning.enable(chat_id="7257834686")
    result = router.route_text("7257834686", "7257834686", "/learn autonomous cycle")
    assert result.ok is True
    assert result.priority == "IMPORTANT"
    assert result.actions[0]["type"] == "autonomous_learning_cycle"
    assert result.actions[0]["data"]["status"] == "COMPLETED"
    assert "AUTONOMOUS LEARNING COMPLETE" in result.message
    latest = control.autonomous_learning.latest_cycle()
    assert latest["status"] == "COMPLETED"


def test_status_reports_latest_knowledge_cycle(tmp_path: Path):
    _, control, router = make_control(tmp_path)
    control.autonomous_learning.enable(chat_id="7257834686")
    control.autonomous_learning.run_cycle(chat_id="7257834686", topics=["approval gate ergonomics"])
    status = router.route_text("7257834686", "7257834686", "/status")
    assert status.ok is True
    assert "Knowledge Cycle: COMPLETED" in status.message
