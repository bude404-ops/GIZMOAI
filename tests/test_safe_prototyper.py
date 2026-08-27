from pathlib import Path

from gizmo.apps.factory import KnowledgeAppFactory
from gizmo.apps.prototyper import SafeMiniAppPrototyper
from gizmo.ideas.autonomous_thinker import AutonomousThinker
from gizmo.knowledge.universal_sources import KnowledgeSource, UniversalKnowledgeIngestor
from gizmo.orchestrator.orchestrator import GizmoOrchestrator
from gizmo.control.telegram_control import TelegramControlLayer
from gizmo.telegram.config import TelegramConfig
from gizmo.telegram.router import TelegramCommandRouter
from gizmo.telegram.security import TelegramAuthorizer


def _seed_chosen_idea(orchestrator: GizmoOrchestrator) -> None:
    ingestor = UniversalKnowledgeIngestor(orchestrator.brain_core, orchestrator.store)
    ingestor.ingest([
        KnowledgeSource(
            kind="text",
            locator="People need tiny mobile tools that convert complex knowledge into checklists, decisions, and next actions.",
            title="Prototype source",
            domain="productivity",
            trust=0.8,
        )
    ], domain="productivity")
    KnowledgeAppFactory(orchestrator.brain_core, orchestrator.store).run(domain="productivity")
    AutonomousThinker(orchestrator.brain_core, orchestrator.store).think(cycle_id="prototype-test", topics=["app ideas", "productivity"])


def test_safe_prototyper_creates_real_html_and_review_queue(tmp_path: Path):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    _seed_chosen_idea(orchestrator)

    report = SafeMiniAppPrototyper(orchestrator.brain_core, orchestrator.store).run(limit=2, allow_publish=False)

    assert report.prototypes_created
    assert report.published is False
    assert report.review_queue_size >= len(report.prototypes_created)
    for item in report.top_prototypes:
        html_path = Path(item["html_path"])
        manifest_path = Path(item["manifest_path"])
        assert html_path.exists()
        assert manifest_path.exists()
        html = html_path.read_text()
        assert "https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4" in html
        assert "print-lol-tokens.js" in html
        assert "font-rajdhani" in html
        assert "READY_FOR_REVIEW" not in html
    assert (tmp_path / "apps" / "latest_prototype_report.json").exists()
    assert (tmp_path / "apps" / "prototype_review_queue.json").exists()


def test_telegram_can_create_prototype_drafts(tmp_path: Path):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    _seed_chosen_idea(orchestrator)
    config = TelegramConfig(bot_token="", admin_ids={"101"}, github_repository="owner/repo", reaper_auth_secret_available=True)
    control = TelegramControlLayer(orchestrator, config=config)
    router = TelegramCommandRouter(orchestrator.store, TelegramAuthorizer(config.admin_ids), control)

    result = router.route_text("101", "201", "prototype your best idea")

    assert result.ok is True
    assert result.intent["intent"] == "prototype"
    assert "PROTOTYPES READY FOR REVIEW" in result.message
    assert (tmp_path / "apps" / "latest_prototype_report.json").exists()
