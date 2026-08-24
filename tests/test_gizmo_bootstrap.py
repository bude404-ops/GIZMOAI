from pathlib import Path

from gizmo.agents.core_agents import CORE_AGENTS
from gizmo.agent_factory.factory import AgentFactory
from gizmo.core.models import MemoryKind, OperatingMode, Task, TaskStatus
from gizmo.core.store import JsonStore
from gizmo.memory.memory_system import MemorySystem
from gizmo.orchestrator.orchestrator import GizmoOrchestrator
from gizmo.security.security_system import SecuritySystem
from gizmo.tasks.task_engine import TaskEngine
from gizmo.tools.tool_registry import ToolRegistry
from gizmo.unreal.unreal_detector import UnrealDetector


def test_registers_exactly_27_core_agents():
    assert len(CORE_AGENTS) == 27
    assert CORE_AGENTS[0].name == "Executive Architect"
    assert CORE_AGENTS[-1].name == "Quality/Synthesis Agent"
    assert len({agent.id for agent in CORE_AGENTS}) == 27
    assert all(agent.memory_namespace for agent in CORE_AGENTS)


def test_memory_is_persistent_and_searchable(tmp_path: Path):
    memory = MemorySystem(JsonStore(tmp_path))
    memory.add(MemoryKind.PROCEDURAL, "org", "When generating small web apps, keep them dependency-free and testable.", ["web", "lesson"])
    matches = memory.search("dependency-free testable")
    assert len(matches) == 1
    assert matches[0]["namespace"] == "org"


def test_task_engine_tracks_required_fields_and_status(tmp_path: Path):
    engine = TaskEngine(JsonStore(tmp_path))
    task = engine.create_task(Task(project="demo", objective="test objective", assigned_agent="agent-11"))
    updated = engine.transition(task.id, TaskStatus.TESTING, "entering tests")
    assert updated.status == TaskStatus.TESTING
    assert updated.execution_history
    reloaded = engine.load(task.id)
    assert reloaded.project == "demo"


def test_security_modes_and_emergency_stop(tmp_path: Path):
    security = SecuritySystem(JsonStore(tmp_path))
    security.set_mode(OperatingMode.AUTONOMOUS)
    assert security.require_approval("delete_repo") is True
    assert security.require_approval("plan") is False
    security.emergency_stop()
    assert security.mode() == OperatingMode.EMERGENCY
    assert security.require_approval("plan") is True


def test_tool_registry_is_least_privilege():
    registry = ToolRegistry()
    github_tools = {tool.name for tool in registry.allowed_for("agent-10")}
    frontend_tools = {tool.name for tool in registry.allowed_for("agent-07")}
    assert "github.pr" in github_tools
    assert "github.pr" not in frontend_tools
    assert "memory.search" in frontend_tools


def test_agent_factory_creates_sandbox_agent_only():
    agent = AgentFactory().propose_specialist("Physics", "Need repeated physics simulation expertise")
    assert agent.trusted is False
    assert agent.sandbox_required is True
    assert "sandbox.run" in agent.allowed_tools


def test_unreal_detector_reports_truthfully():
    result = UnrealDetector().detect()
    assert "available" in result
    if not result["available"]:
        assert "unavailable" in result["limitation"].lower()


def test_orchestrator_bootstrap_and_self_test(tmp_path: Path):
    orchestrator = GizmoOrchestrator(tmp_path)
    report = orchestrator.self_test()
    assert report["passed"] is True
    status = orchestrator.status()
    assert status["agents"] == 27
    assert status["completed_tasks"] >= 6
    first = Path(report["first_demo"]["artifact"]["root"])
    second = Path(report["second_demo"]["artifact"]["root"])
    assert (first / "index.html").exists()
    assert (second / "index.html").exists()
    assert "Memory applied" in (second / "index.html").read_text()
