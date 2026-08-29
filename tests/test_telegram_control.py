import os
from pathlib import Path

from gizmo.control.telegram_control import TelegramControlLayer
from gizmo.orchestrator.orchestrator import GizmoOrchestrator
from gizmo.telegram.config import TelegramConfig
from gizmo.telegram.router import TelegramCommandRouter
from gizmo.telegram.security import TelegramAuthorizer


def make_router(tmp_path: Path, admin: str = "101"):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    config = TelegramConfig(bot_token="", admin_ids={admin}, github_repository="owner/repo", reaper_auth_secret_available=True)
    control = TelegramControlLayer(orchestrator, config=config)
    router = TelegramCommandRouter(orchestrator.store, TelegramAuthorizer(config.admin_ids), control)
    return orchestrator, router


def test_telegram_authorization_rejects_unknown_user(tmp_path: Path):
    _, router = make_router(tmp_path)
    result = router.route_text("999", "999", "/status")
    assert result.ok is False
    assert result.message == "Access denied."
    assert result.priority == "SECURITY"


def test_status_command_returns_mobile_summary(tmp_path: Path):
    _, router = make_router(tmp_path)
    result = router.route_text("101", "201", "/status")
    assert result.ok is True
    assert "GIZMO STATUS" in result.message
    assert result.task["source"] == "telegram"
    assert result.task["status"] == "QUEUED"


def test_natural_language_build_becomes_structured_task_and_github_dispatch_plan(tmp_path: Path):
    orchestrator, router = make_router(tmp_path)
    result = router.route_text("101", "201", "Build a new autonomous research agent that learns from previous research.")
    assert result.ok is True
    assert result.intent["intent"] == "universal_task"
    assert result.task["objective"].startswith("Build a new autonomous research agent")
    assert result.actions[0]["type"] == "universal_route"
    plan = result.actions[0]["data"]["plan"]
    execution = result.actions[0]["data"]["execution"]
    assert plan["classification"]["category"] in {"software_development", "web_research"}
    assert "agent-02" in plan["selected_agents"]
    assert plan["verification_plan"]
    assert execution["task_ids"]


def test_approval_buttons_are_bound_to_unique_action_id(tmp_path: Path):
    _, router = make_router(tmp_path)
    result = router.route_text("101", "201", "/deploy latest")
    assert result.priority == "APPROVAL_REQUIRED"
    assert "APPROVAL REQUIRED" in result.message
    button_data = result.inline_buttons[0][0]["callback_data"]
    assert button_data.startswith("/approve approval-")
    assert "approve-" in button_data


def test_telegram_approval_releases_universal_execution(tmp_path: Path):
    _, router = make_router(tmp_path)
    gated = router.route_text("101", "201", "Build a production release automation script now.")
    execution = gated.actions[0]["data"]["execution"]
    approval = execution["evidence"]["approval_request"]

    approved = router.route_text("101", "201", f"/approve {approval['id']} {approval['approval_code']}")
    assert approved.ok is True
    assert "UNIVERSAL EXECUTION APPROVED" in approved.message
    released = approved.actions[0]["data"]
    assert released["status"] == "QUEUED"
    assert released["task_ids"]


def test_explicit_memory_rejects_secret_like_text(tmp_path: Path):
    _, router = make_router(tmp_path)
    result = router.route_text("101", "201", "/remember my token is abc")
    assert result.ok is False
    assert result.priority == "SECURITY"


def test_explicit_memory_and_query_use_second_brain(tmp_path: Path):
    _, router = make_router(tmp_path)
    remembered = router.route_text("101", "201", "/remember Always test production deployments before release.")
    assert remembered.ok is True
    memory = router.route_text("101", "201", "/memory production deployments")
    assert memory.ok is True
    assert "Telegram memory" in memory.message or "production" in memory.message.lower()


def test_pause_resume_stop_autonomous_controls(tmp_path: Path):
    orchestrator, router = make_router(tmp_path)
    pause = router.route_text("101", "201", "/pause")
    assert pause.ok is True
    assert orchestrator.store.read("control", "autonomous_mode.json")["paused"] is True
    resume = router.route_text("101", "201", "/resume")
    assert resume.ok is True
    assert orchestrator.store.read("control", "autonomous_mode.json")["paused"] is False
    stop = router.route_text("101", "201", "/stop")
    assert stop.priority == "URGENT"
    assert orchestrator.store.read("control", "autonomous_mode.json")["emergency"] is True


def test_end_to_end_telegram_reaper_agent_github_memory_result(tmp_path: Path):
    orchestrator, router = make_router(tmp_path)
    result = router.route_text("101", "201", "Build me a new autonomous research agent that learns from previous research.")
    assert result.ok is True
    assert result.task["source"] == "telegram"
    assert result.intent["intent"] == "universal_task"
    plan = result.actions[0]["data"]["plan"]
    execution = result.actions[0]["data"]["execution"]
    assert "web_research" in [cap["name"] for cap in plan["capabilities"]]
    assert "Original request restated and matched to result" in plan["verification_plan"]
    assert execution["status"] == "QUEUED"
    assert orchestrator.store.path("telegram", "task_results", f"{result.task['task_id']}.json").exists()
    assert orchestrator.store.read("telegram", "notifications.json")



def test_important_events_command_reports_high_signal_cycle(tmp_path: Path):
    orchestrator, router = make_router(tmp_path)
    orchestrator.store.write({
        "cycle_id": "cycle-important-test",
        "status": "COMPLETED",
        "progress_evaluation": {
            "evaluation_id": "progress-important-test",
            "verdict": "STALLED",
            "score": 0.31,
            "trend": "DECLINING",
            "next_actions": ["Clear blocked campaign milestone"],
        },
        "campaign_tracking": {
            "tracking_id": "tracking-important-test",
            "campaign_id": "campaign-important-test",
            "verdict": "BLOCKED",
            "score": 0.2,
            "next_objective": "Produce missing evidence",
        },
    }, "cloud", "brain_latest.json")
    result = router.route_text("101", "201", "/important")
    assert result.ok is True
    assert result.priority == "IMPORTANT"
    assert "IMPORTANT EVENTS" in result.message
    assert "Autonomous progress is STALLED" in result.message
    report = result.actions[0]["data"]
    assert report["events"]
    assert report["queued"]
    assert orchestrator.store.read("telegram", "important_event_keys.json")


def test_important_events_are_deduped_unless_forced(tmp_path: Path):
    orchestrator, router = make_router(tmp_path)
    orchestrator.store.write({
        "cycle_id": "cycle-dedupe-test",
        "status": "COMPLETED",
        "progress_evaluation": {
            "evaluation_id": "progress-dedupe-test",
            "verdict": "MIXED_PROGRESS",
            "score": 0.55,
            "trend": "FLAT",
            "next_actions": ["Tighten campaign evidence"],
        },
    }, "cloud", "brain_latest.json")
    first = router.route_text("101", "201", "/important")
    second = router.route_text("101", "201", "/important")
    forced = router.route_text("101", "201", "/important force")
    assert len(first.actions[0]["data"]["queued"]) == 1
    assert len(second.actions[0]["data"]["queued"]) == 0
    assert len(second.actions[0]["data"]["skipped"]) == 1
    assert len(forced.actions[0]["data"]["queued"]) == 1


def test_cloud_brain_cycle_collects_important_events(tmp_path: Path):
    orchestrator, router = make_router(tmp_path)
    result = router.route_text("101", "201", "start cloud brain")
    assert result.ok is True
    cycle = result.actions[0]["data"]
    assert "important_events" in cycle
    assert "Important events:" in result.message


def test_telegram_important_events_cli(tmp_path: Path):
    import json
    import subprocess
    import sys

    workspace = str(tmp_path / "cli-important-events")
    seed = subprocess.run(
        [sys.executable, "-m", "gizmo.core.cli", "autonomous-progress", "--workspace", workspace, "--cycles", "2"],
        check=True,
        text=True,
        capture_output=True,
    )
    assert json.loads(seed.stdout)["ready"] is True
    report = subprocess.run(
        [sys.executable, "-m", "gizmo.core.cli", "telegram-important-events", "--workspace", workspace, "--chat-id", "201"],
        check=True,
        text=True,
        capture_output=True,
    )
    data = json.loads(report.stdout)
    assert data["report_id"].startswith("important-events-")
    assert data["chat_id"] == "201"
    assert isinstance(data["events"], list)
