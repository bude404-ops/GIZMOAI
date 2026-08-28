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
    assert result["checks"]["health_report"] is True
    assert result["checks"]["cancellation"] is True
    assert result["checks"]["pause_resume"] is True
    assert result["checks"]["checkpoint_rollback"] is True
    assert result["checks"]["outcome_evaluator"] is True
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


def test_universal_health_report_summarizes_clean_completed_chain(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    result = orchestrator.universal_route("Build a small verified automation script.", execute=True)
    orchestrator.run_universal_execution(result["execution"]["execution_id"])

    report = orchestrator.universal_health_report()
    assert report["ready"] is True
    assert report["risk"] == "LOW"
    assert report["counts"]["COMPLETED"] >= 1
    assert report["step_counts"]["completed"] >= len(result["execution"]["steps"])
    assert report["next_actions"] == ["No intervention needed"]


def test_universal_health_report_flags_failed_and_approval_work(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    failed_route = orchestrator.universal_route("Build a small verified automation script.", execute=True)
    task = orchestrator.tasks.load(failed_route["execution"]["task_ids"][0])
    task.status = TaskStatus.FAILED
    task.result = "health simulated failure"
    orchestrator.tasks.save(task)
    waiting_route = orchestrator.universal_route("Deploy the production app now.", execute=True)

    report = orchestrator.universal_health_report(stale_after_minutes=0)
    assert report["risk"] == "HIGH"
    assert report["counts"]["FAILED"] >= 1
    assert report["counts"]["WAITING_APPROVAL"] >= 1
    assert report["failed"][0]["task_id"] == task.id
    assert report["waiting_approval"][0]["approval_id"] == waiting_route["execution"]["evidence"]["approval_request"]["id"]
    assert "Run universal-recover on failed executions" in report["next_actions"]
    assert "Approve or reject waiting universal executions" in report["next_actions"]


def test_universal_cancel_stops_queued_chain_and_blocks_runner(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    result = orchestrator.universal_route("Build a small verified automation script.", execute=True)
    execution_id = result["execution"]["execution_id"]

    cancelled = orchestrator.cancel_universal_execution(execution_id, reason="operator changed priority")["execution"]
    assert cancelled["status"] == "CANCELLED"
    assert cancelled["evidence"]["cancellation"]["cancelled"] is True
    assert cancelled["evidence"]["cancellation"]["reason"] == "operator changed priority"
    assert all(orchestrator.tasks.load(task_id).status == TaskStatus.CANCELLED for task_id in result["execution"]["task_ids"])

    run = orchestrator.run_universal_execution(execution_id)["execution"]
    assert run["status"] == "CANCELLED"
    assert run["evidence"]["runner"]["blocked"] == "execution cancelled"


def test_universal_cancel_stops_waiting_approval_without_releasing_tasks(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    result = orchestrator.universal_route("Deploy the production app now.", execute=True)
    execution_id = result["execution"]["execution_id"]

    cancelled = orchestrator.cancel_universal_execution(execution_id, reason="deployment window closed")["execution"]
    assert cancelled["status"] == "CANCELLED"
    assert cancelled["task_ids"] == []
    assert all(step["status"] == TaskStatus.CANCELLED.value for step in cancelled["steps"])
    refreshed = orchestrator.universal_execution.refresh(execution_id).to_dict()
    assert refreshed["status"] == "CANCELLED"
    assert refreshed["evidence"]["cancellation"]["reason"] == "deployment window closed"


def test_universal_cancel_preserves_completed_execution(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    result = orchestrator.universal_route("Build a small verified automation script.", execute=True)
    execution_id = result["execution"]["execution_id"]
    orchestrator.run_universal_execution(execution_id)

    cancelled = orchestrator.cancel_universal_execution(execution_id)["execution"]
    assert cancelled["status"] == "COMPLETED"
    assert cancelled["evidence"]["cancellation"]["cancelled"] is False
    assert cancelled["evidence"]["cancellation"]["reason"] == "execution already completed"


def test_universal_pause_blocks_runner_and_resume_requeues_chain(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    result = orchestrator.universal_route("Build a small verified automation script.", execute=True)
    execution_id = result["execution"]["execution_id"]

    paused = orchestrator.pause_universal_execution(execution_id, reason="wait for better window")["execution"]
    assert paused["status"] == "PAUSED"
    assert paused["evidence"]["pause"]["paused"] is True
    assert all(orchestrator.tasks.load(task_id).status == TaskStatus.PAUSED for task_id in result["execution"]["task_ids"])

    blocked = orchestrator.run_universal_execution(execution_id)["execution"]
    assert blocked["status"] == "PAUSED"
    assert blocked["evidence"]["runner"]["blocked"] == "execution paused"

    resumed = orchestrator.resume_universal_execution(execution_id, reason="window reopened")["execution"]
    assert resumed["status"] == "QUEUED"
    assert resumed["evidence"]["pause"]["paused"] is False
    assert resumed["evidence"]["resume"]["resumed"] is True
    assert all(orchestrator.tasks.load(task_id).status == TaskStatus.QUEUED for task_id in result["execution"]["task_ids"])


def test_universal_pause_resume_waiting_approval_without_releasing_tasks(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    result = orchestrator.universal_route("Deploy the production app now.", execute=True)
    execution_id = result["execution"]["execution_id"]

    paused = orchestrator.pause_universal_execution(execution_id, reason="approval window paused")["execution"]
    assert paused["status"] == "PAUSED"
    assert paused["task_ids"] == []
    assert all(step["status"] == TaskStatus.PAUSED.value for step in paused["steps"])
    health = orchestrator.universal_health_report(stale_after_minutes=0)
    assert health["counts"]["PAUSED"] >= 1
    assert health["step_counts"]["paused"] >= len(paused["steps"])
    assert "Resume or cancel paused universal executions" in health["next_actions"]

    resumed = orchestrator.resume_universal_execution(execution_id, reason="approval window reopened")["execution"]
    assert resumed["status"] == "WAITING_APPROVAL"
    assert resumed["task_ids"] == []
    assert all(step["blocked_reason"] == "approval required" for step in resumed["steps"])


def test_universal_pause_preserves_completed_execution(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    result = orchestrator.universal_route("Build a small verified automation script.", execute=True)
    execution_id = result["execution"]["execution_id"]
    orchestrator.run_universal_execution(execution_id)

    paused = orchestrator.pause_universal_execution(execution_id)["execution"]
    assert paused["status"] == "COMPLETED"
    assert paused["evidence"]["pause"]["paused"] is False
    assert paused["evidence"]["pause"]["reason"] == "execution already completed"



def test_universal_checkpoint_and_rollback_restore_failed_task(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    result = orchestrator.universal_route("Build a small verified automation script.", execute=True)
    execution_id = result["execution"]["execution_id"]
    task_id = result["execution"]["task_ids"][0]

    checkpoint = orchestrator.checkpoint_universal_execution(execution_id, label="before risky run", reason="safe point")["checkpoint"]
    damaged = orchestrator.tasks.load(task_id)
    damaged.status = TaskStatus.FAILED
    damaged.result = "bad mutation"
    orchestrator.tasks.save(damaged)

    rolled = orchestrator.rollback_universal_execution(execution_id, checkpoint_id=checkpoint["checkpoint_id"], reason="restore safe point")["execution"]
    restored = orchestrator.tasks.load(task_id)
    assert rolled["status"] == "QUEUED"
    assert rolled["evidence"]["rollback"]["rolled_back"] is True
    assert rolled["evidence"]["rollback"]["checkpoint_id"] == checkpoint["checkpoint_id"]
    assert restored.status == TaskStatus.QUEUED
    assert restored.result == ""
    assert restored.execution_history[-1]["action"] == "rollback"


def test_universal_rollback_requires_force_for_terminal_execution(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    result = orchestrator.universal_route("Build a small verified automation script.", execute=True)
    execution_id = result["execution"]["execution_id"]
    checkpoint = orchestrator.checkpoint_universal_execution(execution_id, label="terminal guard")["checkpoint"]
    orchestrator.cancel_universal_execution(execution_id, reason="terminal test")

    blocked = orchestrator.rollback_universal_execution(execution_id, checkpoint_id=checkpoint["checkpoint_id"])["execution"]
    assert blocked["status"] == "CANCELLED"
    assert blocked["evidence"]["rollback"]["rolled_back"] is False

    forced = orchestrator.rollback_universal_execution(execution_id, checkpoint_id=checkpoint["checkpoint_id"], force=True, reason="force restore")["execution"]
    assert forced["status"] == "QUEUED"
    assert forced["evidence"]["rollback"]["rolled_back"] is True
    assert forced["evidence"]["rollback"]["force"] is True


def test_universal_health_reports_checkpoint_availability(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    result = orchestrator.universal_route("Build a small verified automation script.", execute=True)
    checkpoint = orchestrator.checkpoint_universal_execution(result["execution"]["execution_id"], label="health visible")["checkpoint"]

    health = orchestrator.universal_health_report()
    assert any(item["checkpoint_id"] == checkpoint["checkpoint_id"] for item in health["checkpointed"])


def test_universal_outcome_evaluator_marks_unsolved_then_solved(tmp_path):
    orchestrator = GizmoOrchestrator(tmp_path)
    result = orchestrator.universal_route("Build a small verified automation script.", execute=True)
    execution_id = result["execution"]["execution_id"]

    before = orchestrator.evaluate_universal_outcome(execution_id)
    assert before["verdict"] == "NOT_SOLVED"
    assert before["blockers"]

    orchestrator.run_universal_execution(execution_id)
    after = orchestrator.evaluate_universal_outcome(execution_id)
    assert after["verdict"] == "SOLVED"
    assert after["confidence"] >= 0.85
    assert after["next_actions"] == ["No intervention needed"]


def test_universal_checkpoint_rollback_and_evaluate_cli(tmp_path):
    import json
    import subprocess
    import sys

    workspace = str(tmp_path / "cli")
    route = subprocess.run(
        [sys.executable, "-m", "gizmo.core.cli", "universal-execute", "--workspace", workspace, "--text", "Build a small verified automation script."],
        check=True,
        text=True,
        capture_output=True,
    )
    execution_id = json.loads(route.stdout)["execution"]["execution_id"]
    checkpoint = subprocess.run(
        [sys.executable, "-m", "gizmo.core.cli", "universal-checkpoint", "--workspace", workspace, "--execution-id", execution_id, "--label", "cli safe"],
        check=True,
        text=True,
        capture_output=True,
    )
    checkpoint_id = json.loads(checkpoint.stdout)["checkpoint"]["checkpoint_id"]
    evaluation = subprocess.run(
        [sys.executable, "-m", "gizmo.core.cli", "universal-evaluate", "--workspace", workspace, "--execution-id", execution_id],
        check=True,
        text=True,
        capture_output=True,
    )
    assert json.loads(evaluation.stdout)["verdict"] == "NOT_SOLVED"
    rollback = subprocess.run(
        [sys.executable, "-m", "gizmo.core.cli", "universal-rollback", "--workspace", workspace, "--execution-id", execution_id, "--checkpoint-id", checkpoint_id, "--reason", "cli restore"],
        check=True,
        text=True,
        capture_output=True,
    )
    assert json.loads(rollback.stdout)["execution"]["evidence"]["rollback"]["rolled_back"] is True
