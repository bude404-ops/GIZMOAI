from pathlib import Path

from gizmo.apps.factory import KnowledgeAppFactory
from gizmo.knowledge.universal_sources import KnowledgeSource, UniversalKnowledgeIngestor
from gizmo.orchestrator.orchestrator import GizmoOrchestrator
from gizmo.control.telegram_control import TelegramControlLayer
from gizmo.telegram.config import TelegramConfig
from gizmo.telegram.router import TelegramCommandRouter
from gizmo.telegram.security import TelegramAuthorizer


def test_universal_ingestor_turns_any_domain_source_into_memory_and_app_opportunities(tmp_path: Path):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    ingestor = UniversalKnowledgeIngestor(orchestrator.brain_core, orchestrator.store)
    report = ingestor.ingest([
        KnowledgeSource(
            kind="text",
            locator="Garden planning users need seasonal calendars, plant compatibility checks, watering reminders, and simple harvest projections.",
            title="Garden planning source",
            domain="gardening",
            trust=0.82,
        )
    ], domain="gardening")

    assert report.sources_seen == 1
    assert len(report.memories_created) == 1
    assert report.app_opportunities
    assert report.app_opportunities[0]["domain"] == "gardening"
    assert (tmp_path / "knowledge" / "latest_ingestion.json").exists()


def test_app_factory_creates_blueprints_from_learned_knowledge(tmp_path: Path):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    ingestor = UniversalKnowledgeIngestor(orchestrator.brain_core, orchestrator.store)
    ingestor.ingest([
        KnowledgeSource(kind="text", locator="Language learners need spaced repetition, pronunciation drills, and daily streak feedback.", title="Language learning source", domain="education", trust=0.8)
    ], domain="education")
    factory = KnowledgeAppFactory(orchestrator.brain_core, orchestrator.store)
    report = factory.run(domain="education")

    assert report.blueprints_created
    assert report.backlog_size >= 1
    first = report.top_blueprints[0]
    assert first["domain"] == "education"
    assert "core_features" in first
    assert (tmp_path / "apps" / "latest_factory_report.json").exists()
    assert (tmp_path / "apps" / "blueprint_backlog.json").exists()


def test_telegram_can_learn_any_topic_and_create_app_ideas(tmp_path: Path):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    config = TelegramConfig(bot_token="", admin_ids={"101"}, github_repository="owner/repo", reaper_auth_secret_available=True)
    control = TelegramControlLayer(orchestrator, config=config)
    router = TelegramCommandRouter(orchestrator.store, TelegramAuthorizer(config.admin_ids), control)

    learn = router.route_text("101", "201", "learn about cooking meal prep apps")
    factory = router.route_text("101", "201", "create app ideas from cooking meal prep apps")

    assert learn.ok is True
    assert learn.intent["intent"] == "universal_learn"
    assert "UNIVERSAL LEARNING COMPLETE" in learn.message
    assert factory.ok is True
    assert factory.intent["intent"] == "app_factory"
    assert "APP FACTORY COMPLETE" in factory.message
