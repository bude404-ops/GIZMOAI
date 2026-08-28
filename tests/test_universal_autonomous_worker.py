from __future__ import annotations

from gizmo.core.models import TaskStatus
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
    assert result["checks"]["execution_ledger"] is True
    assert result["checks"]["approval_release"] is True
    assert result["checks"]["failure_recovery"] is True
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
    assert result["task_status"] == "QUEUED"
    assert result["actions"][0]["data"]["plan"]["classification"]["category"] == "ai_generation"
    assert result["actions"][0]["data"]["execution"]["task_ids"]


def test_universal_execute_creates_traceable_execution_ledger(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    result = orchestrator.universal_route("Build a small verified automation script.", execute=True)
    execution = result["execution"]
    plan = result["plan"]
    assert execution["status"] == "QUEUED"
    assert execution["request_id"] == plan["request_id"]
    assert execution["task_ids"] == plan["execution_task_ids"]
    assert len(execution["steps"]) == len(plan["decomposition"])
    assert all(step["task_id"] for step in execution["steps"])
    first_task = orchestrator.tasks.load(execution["task_ids"][0])
    assert first_task.execution_history[-1]["action"] == "created"
    refreshed = orchestrator.universal_execution.refresh(execution["execution_id"]).to_dict()
    assert refreshed["status"] == "QUEUED"


def test_universal_execute_blocks_approval_required_without_tasks(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    result = orchestrator.universal_route("Deploy the production app now.", execute=True)
    execution = result["execution"]
    assert result["plan"]["approval_required"] is True
    assert execution["status"] == "WAITING_APPROVAL"
    assert execution["task_ids"] == []
    assert all(step.get("blocked_reason") == "approval required" for step in execution["steps"])


def test_universal_runner_advances_ready_steps_in_dependency_order(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    result = orchestrator.universal_route("Build a small verified automation script.", execute=True)
    execution_id = result["execution"]["execution_id"]

    first_run = orchestrator.run_universal_execution(execution_id, max_steps=1)["execution"]
    assert first_run["evidence"]["runner"]["ran"] == 1
    assert first_run["steps"][0]["status"] == "COMPLETED"
    assert first_run["steps"][1]["status"] == "QUEUED"

    final_run = orchestrator.run_universal_execution(execution_id)["execution"]
    assert final_run["status"] == "COMPLETED"
    assert all(step["status"] == "COMPLETED" for step in final_run["steps"])
    assert final_run["evidence"]["runner"]["ran"] >= 1


def test_universal_runner_refuses_approval_required_execution(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    result = orchestrator.universal_route("Deploy the production app now.", execute=True)
    run = orchestrator.run_universal_execution(result["execution"]["execution_id"])["execution"]
    assert run["status"] == "WAITING_APPROVAL"
    assert run["evidence"]["runner"]["ran"] == 0
    assert run["evidence"]["runner"]["blocked"] == "approval required"


def test_universal_approval_release_creates_task_chain(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    result = orchestrator.universal_route("Deploy the production app now.", execute=True)
    approval = result["execution"]["evidence"]["approval_request"]

    released = orchestrator.approve_universal_execution(approval["id"], approval["approval_code"])["execution"]
    assert released["status"] == "QUEUED"
    assert released["evidence"]["approval_decision"] == "APPROVED"
    assert released["evidence"]["release"]["released"] is True
    assert len(released["task_ids"]) == len(released["steps"])
    assert all(step["task_id"] and step["blocked_reason"] is None for step in released["steps"])


def test_universal_approval_release_can_run_after_approval(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    result = orchestrator.universal_route("Deploy the production app now.", execute=True)
    approval = result["execution"]["evidence"]["approval_request"]
    released = orchestrator.approve_universal_execution(approval["id"], approval["approval_code"], run=True)
    assert released["execution"]["status"] == "QUEUED"
    assert released["run"]["execution"]["status"] == "COMPLETED"


def test_universal_recovery_requeues_failed_task(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    result = orchestrator.universal_route("Build a small verified automation script.", execute=True)
    execution = result["execution"]
    task = orchestrator.tasks.load(execution["task_ids"][0])
    task.status = TaskStatus.FAILED
    task.result = "simulated failure"
    orchestrator.tasks.save(task)

    recovered = orchestrator.recover_universal_execution(execution["execution_id"])["execution"]
    retried = orchestrator.tasks.load(execution["task_ids"][0])
    assert recovered["status"] == "QUEUED"
    assert recovered["evidence"]["recovery"]["requeued"][0]["task_id"] == retried.id
    assert retried.status == TaskStatus.QUEUED
    assert retried.retry_count == 1
    assert retried.result == ""


def test_universal_recovery_escalates_exhausted_retry_budget(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    result = orchestrator.universal_route("Build a small verified automation script.", execute=True)
    execution = result["execution"]
    task = orchestrator.tasks.load(execution["task_ids"][0])
    task.status = TaskStatus.FAILED
    task.retry_count = task.max_retries
    task.result = "still broken"
    orchestrator.tasks.save(task)

    recovered = orchestrator.recover_universal_execution(execution["execution_id"])["execution"]
    escalated = orchestrator.tasks.load(execution["task_ids"][0])
    assert recovered["status"] == "ESCALATED"
    assert recovered["evidence"]["recovery"]["escalated"][0]["task_id"] == escalated.id
    assert escalated.status == TaskStatus.ESCALATED
