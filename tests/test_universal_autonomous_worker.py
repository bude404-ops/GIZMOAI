from __future__ import annotations

from gizmo.orchestrator.orchestrator import GizmoOrchestrator
from gizmo.research.internet_research import InternetResearchPipeline, ResearchSource


def test_universal_acceptance_paths(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    result = orchestrator.universal_acceptance_demo()
    assert result["ready"] is True
    assert result["checks"]["question_researches"] is True
    assert result["checks"]["research_has_sources"] is True
    assert result["checks"]["software_project_mode"] is True
    assert result["checks"]["debugging_verification"] is True
    assert result["checks"]["unreal_bridge_honest"] is True
    assert result["checks"]["generation_manifest"] is True
    assert result["checks"]["memory_retrieval_planned"] is True
    assert result["checks"]["unknown_problem_research"] is True
    assert result["checks"]["trading_not_central"] is True


def test_trading_is_one_capability_not_router_default(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    build = orchestrator.universal_route("Build me a simple SaaS application that tracks project tasks.")
    assert build["plan"]["classification"]["category"] == "software_development"
    assert build["plan"]["capabilities"][0]["name"] == "software_development"
    capability_names = [cap["name"] for cap in build["capability_status"]["capabilities"]]
    assert "trading" in capability_names


def test_research_pipeline_separates_claim_types_and_sources(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    pipeline = InternetResearchPipeline(orchestrator.brain_core, orchestrator.store)
    sources = [
        ResearchSource(
            "Official docs",
            "https://docs.example.com/product",
            "Published in 2026. Product teams use memory vaults to preserve decisions. This suggests teams may pay for searchable project continuity.",
        ),
        ResearchSource(
            "Market note",
            "https://research.example.com/memory-vaults",
            "Updated 2026. Some buyers are uncertain because budgets may decrease when tools overlap.",
        ),
    ]
    report = pipeline.run("would people pay for memory vaults", sources, store_useful=True)
    assert report.ready is True
    assert report.citations
    assert report.facts
    assert report.inferences or report.hypotheses or report.uncertainties
    assert report.memories_created


def test_telegram_natural_language_routes_to_universal(tmp_path):
    from gizmo.control.telegram_control import TelegramControlLayer
    from gizmo.telegram.config import TelegramConfig
    from gizmo.telegram.intents import IntentDetector
    from gizmo.telegram.router import TelegramTaskEnvelope

    orchestrator = GizmoOrchestrator(tmp_path)
    control = TelegramControlLayer(orchestrator, TelegramConfig(bot_token="", admin_ids={"1"}, github_repository="owner/repo"))
    intent = IntentDetector().detect("Create a fantasy character for the Unreal project")
    assert intent.intent == "universal_task"
    envelope = TelegramTaskEnvelope(
        task_id="task-test",
        source="telegram",
        user_id="1",
        chat_id="1",
        command=intent.command,
        objective=intent.objective,
        priority=intent.priority,
        status="QUEUED",
        created_at="2026-01-01T00:00:00+00:00",
    )
    result = control.handle_telegram_task(envelope, intent)
    assert result["ok"] is True
    assert result["task_status"] == "PLANNED"
    assert result["actions"][0]["data"]["plan"]["classification"]["category"] == "ai_generation"
