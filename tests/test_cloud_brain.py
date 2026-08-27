from pathlib import Path

from gizmo.control.cloud_brain import CloudAutonomousBrainRunner, SWARM_AGENTS
from gizmo.control.telegram_control import TelegramControlLayer
from gizmo.orchestrator.orchestrator import GizmoOrchestrator
from gizmo.telegram.config import TelegramConfig
from gizmo.telegram.router import TelegramCommandRouter
from gizmo.telegram.security import TelegramAuthorizer


def test_cloud_brain_cycle_executes_swarm_and_persists_snapshot(tmp_path: Path):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    runner = CloudAutonomousBrainRunner(orchestrator)
    runner.enable(chat_id="201")
    cycle = runner.run_cycle(chat_id="201")

    assert cycle.status == "COMPLETED"
    assert len(cycle.agents) == len(SWARM_AGENTS)
    assert len(cycle.tasks_executed) == len(SWARM_AGENTS)
    assert len(cycle.memories_created) >= (len(SWARM_AGENTS) * 2) + 2
    assert cycle.snapshot["agent_count"] == len(SWARM_AGENTS)
    assert len(cycle.reasoning) == len(SWARM_AGENTS)
    assert cycle.semantic_index["indexed_memories"] >= len(cycle.memories_created)
    assert cycle.body_scorecard["actions"] == len(SWARM_AGENTS)
    assert cycle.snapshot["reasoning_events"] == len(SWARM_AGENTS)
    assert "local" in cycle.snapshot["reasoning_providers"]
    assert cycle.snapshot["body_actions_scored"] == len(SWARM_AGENTS)
    assert cycle.universal_knowledge["sources_seen"] >= 1
    assert len(cycle.app_factory["blueprints_created"]) >= 1
    assert cycle.snapshot["app_blueprints_created"] >= 1
    assert cycle.autonomous_thinking["ideas"]
    assert cycle.autonomous_thinking["upgrades"]
    assert cycle.snapshot["autonomous_ideas_created"] >= 1
    assert cycle.snapshot["upgrade_proposals_created"] >= 1
    assert (tmp_path / "cloud" / "brain_snapshot.json").exists()
    assert (tmp_path / "second_brain" / "structured" / "semantic" / "index_report.json").exists()
    assert (tmp_path / "body" / "scorecard.json").exists()
    assert (tmp_path / "body" / "next_queue.json").exists()
    assert (tmp_path / "cloud" / "brain_history.json").exists()
    assert (tmp_path / "second_brain" / "brain" / "indexes" / "Memory Index.md").exists()


def test_cloud_brain_skips_when_disabled(tmp_path: Path):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    runner = CloudAutonomousBrainRunner(orchestrator)
    cycle = runner.run_cycle()
    assert cycle.status == "SKIPPED"
    assert "Enabled: False" in cycle.notification


def test_telegram_plain_english_can_start_cloud_brain(tmp_path: Path):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    config = TelegramConfig(bot_token="", admin_ids={"101"}, github_repository="owner/repo", reaper_auth_secret_available=True)
    control = TelegramControlLayer(orchestrator, config=config)
    router = TelegramCommandRouter(orchestrator.store, TelegramAuthorizer(config.admin_ids), control)

    result = router.route_text("101", "201", "become smarter")

    assert result.ok is True
    assert result.intent["intent"] == "cloud_brain"
    assert "CLOUD BRAIN CYCLE COMPLETE" in result.message
    latest = control.cloud_brain.latest_cycle()
    assert latest["status"] == "COMPLETED"
    assert len(latest["agents"]) == len(SWARM_AGENTS)
