from pathlib import Path

from gizmo.brain.agent_memory import AgentBrainBridge
from gizmo.brain.memory_api import SecondBrain
from gizmo.brain.models import BrainMemoryType
from gizmo.core.models import Task, TaskStatus
from gizmo.core.store import JsonStore
from gizmo.orchestrator.orchestrator import GizmoOrchestrator


def test_agent_preflight_uses_central_brain_context(tmp_path: Path):
    brain = SecondBrain(tmp_path / "brain_core")
    brain.record_decision("Use central Brain", "All agents use the shared Brain before meaningful work.", confidence=1.0, importance=10)
    store = JsonStore(tmp_path / "runtime")
    bridge = AgentBrainBridge(brain, store)
    task = Task(project="Gizmo", objective="Use central Brain for agent recall", assigned_agent="agent-26")
    preflight = bridge.before_task(task)
    assert preflight.agent_id == "agent-26"
    assert preflight.recalled_memory_ids
    assert task.execution_history[-1]["action"] == "brain_preflight"
    assert store.path("brain", "agent_preflights", f"{task.id}.json").exists()


def test_agent_evaluation_captures_experience_lesson_and_evaluation(tmp_path: Path):
    brain = SecondBrain(tmp_path / "brain_core")
    store = JsonStore(tmp_path / "runtime")
    bridge = AgentBrainBridge(brain, store)
    task = Task(project="Gizmo", objective="Capture learning after work", assigned_agent="agent-11")
    task.status = TaskStatus.COMPLETED
    task.result = "Work completed with tests."
    task.lessons_learned.append("Agent memory capture should happen after meaningful work.")
    evaluation = bridge.after_task(task, worked=["tests", "memory capture"])
    assert evaluation.achieved is True
    assert len(evaluation.captured_memory_ids) == 3
    captured = [brain.get(memory_id) for memory_id in evaluation.captured_memory_ids]
    assert {memory.type for memory in captured} == {BrainMemoryType.EXPERIENCE, BrainMemoryType.LESSON, BrainMemoryType.EVALUATION}
    collective = bridge.collective_memory()
    assert collective["lessons"]
    assert collective["evaluations"]


def test_agent_profile_tracks_performance_and_contributions(tmp_path: Path):
    brain = SecondBrain(tmp_path / "brain_core")
    store = JsonStore(tmp_path / "runtime")
    bridge = AgentBrainBridge(brain, store)
    task = Task(project="Gizmo", objective="Track agent performance", assigned_agent="agent-27")
    bridge.before_task(task)
    task.status = TaskStatus.COMPLETED
    task.result = "Evaluation completed."
    task.lessons_learned.append("Performance memory should influence future assignment.")
    bridge.after_task(task, worked=["evaluation"])
    profile = bridge.agent_profile("agent-27")
    assert profile["tasks_seen"] == 1
    assert profile["tasks_completed"] == 1
    assert profile["memory_contributions"] >= 1
    assert profile["average_evaluation"] > 0


def test_orchestrator_execution_runs_brain_preflight_and_capture(tmp_path: Path):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    task = Task(project="Gizmo", objective="Verify central Brain agent bridge", assigned_agent="agent-26")
    orchestrator.tasks.create_task(task)
    executed = orchestrator._execute_allowed_task(task)
    assert executed.status == TaskStatus.COMPLETED
    assert any(item["action"] == "brain_preflight" for item in executed.execution_history)
    profile = orchestrator.agent_brain.agent_profile("agent-26")
    assert profile["tasks_completed"] >= 1
    assert orchestrator.agent_brain.collective_memory()["evaluations"]


def test_orchestrator_brain_phase4_demo(tmp_path: Path):
    result = GizmoOrchestrator(tmp_path).brain_phase4_demo()
    assert result["ready"] is True
    assert result["phase3_ready"] is True
    assert result["agent_profile"]["memory_contributions"] >= 1
    assert result["collective_counts"]["evaluations"] >= 1
