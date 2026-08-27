from pathlib import Path

from gizmo.apps.factory import KnowledgeAppFactory
from gizmo.ideas.autonomous_thinker import AutonomousThinker
from gizmo.knowledge.universal_sources import KnowledgeSource, UniversalKnowledgeIngestor
from gizmo.orchestrator.orchestrator import GizmoOrchestrator
from gizmo.control.telegram_control import TelegramControlLayer
from gizmo.telegram.config import TelegramConfig
from gizmo.telegram.router import TelegramCommandRouter
from gizmo.telegram.security import TelegramAuthorizer


def _seed_app_backlog(orchestrator: GizmoOrchestrator) -> None:
    ingestor = UniversalKnowledgeIngestor(orchestrator.brain_core, orchestrator.store)
    ingestor.ingest([
        KnowledgeSource(
            kind="text",
            locator="Creators need fast app generators that turn rough ideas into mobile dashboards, checklists, and learning tools.",
            title="Creator app source",
            domain="creator tools",
            trust=0.82,
        )
    ], domain="creator tools")
    KnowledgeAppFactory(orchestrator.brain_core, orchestrator.store).run(domain="creator tools")


def test_autonomous_thinker_generates_ranked_ideas_and_upgrade_queue(tmp_path: Path):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    _seed_app_backlog(orchestrator)

    report = AutonomousThinker(orchestrator.brain_core, orchestrator.store).think(
        cycle_id="test-cycle",
        topics=["self improvement", "app ideas", "operator friction"],
    )

    assert report.ideas
    assert report.upgrades
    assert report.chosen_next
    assert report.memories_created
    scores = [item["score"] for item in report.ideas]
    assert scores == sorted(scores, reverse=True)
    assert (tmp_path / "ideas" / "latest_thinking.json").exists()
    assert (tmp_path / "ideas" / "upgrade_queue.json").exists()
    assert (tmp_path / "ideas" / "chosen_next.json").exists()


def test_telegram_can_tell_gizmo_to_think_for_itself(tmp_path: Path):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    _seed_app_backlog(orchestrator)
    config = TelegramConfig(bot_token="", admin_ids={"101"}, github_repository="owner/repo", reaper_auth_secret_available=True)
    control = TelegramControlLayer(orchestrator, config=config)
    router = TelegramCommandRouter(orchestrator.store, TelegramAuthorizer(config.admin_ids), control)

    result = router.route_text("101", "201", "think for yourself")

    assert result.ok is True
    assert result.intent["intent"] == "autonomous_think"
    assert "AUTONOMOUS THINKING COMPLETE" in result.message
    assert (tmp_path / "ideas" / "latest_thinking.json").exists()
