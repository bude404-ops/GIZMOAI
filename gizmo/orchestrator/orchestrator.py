"""Reaper Core / Executive Orchestrator for GIZMO bootstrap v0."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gizmo.agents.core_agents import CORE_AGENTS, core_agent_map
from gizmo.agent_factory.factory import AgentFactory
from gizmo.communication.message_bus import MessageBus
from gizmo.core.models import MemoryKind, OperatingMode, StructuredMessage, Task, TaskStatus
from gizmo.core.store import JsonStore
from gizmo.github.workspace import GitHubWorkspaceLoop
from gizmo.memory.memory_system import MemorySystem
from gizmo.monitoring.cost_manager import CostManager
from gizmo.monitoring.logger import AuditLogger
from gizmo.projects.project_generator import ProjectGenerator
from gizmo.security.security_system import SecuritySystem
from gizmo.tasks.task_engine import TaskEngine
from gizmo.tools.tool_registry import ToolRegistry
from gizmo.unreal.unreal_detector import UnrealDetector


class GizmoOrchestrator:
    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace)
        self.store = JsonStore(self.workspace)
        self.memory = MemorySystem(self.store)
        self.tasks = TaskEngine(self.store)
        self.bus = MessageBus(self.store)
        self.security = SecuritySystem(self.store)
        self.audit = AuditLogger(self.store)
        self.costs = CostManager(self.store)
        self.tools = ToolRegistry()
        self.agent_factory = AgentFactory()
        self.projects = ProjectGenerator(self.workspace / "projects")
        self.unreal = UnrealDetector()
        self.github = GitHubWorkspaceLoop(
            self.store,
            self.tasks,
            self.memory,
            self.security,
            self.audit,
            repo_path=Path.cwd(),
        )

    def bootstrap(self) -> dict[str, Any]:
        self.security.set_mode(OperatingMode.MANUAL)
        agents = [agent.to_dict() for agent in CORE_AGENTS]
        self.store.write(agents, "agents", "core_agents.json")
        self.store.write([tool.to_dict() for tool in self.tools.tools.values()], "tools", "registry.json")
        capabilities = self.inspect_capabilities()
        self.store.write(capabilities, "config", "capabilities.json")
        self.memory.add(MemoryKind.ORGANIZATIONAL, "organization", "GIZMO bootstrap initialized with 27 core agents and manual safety mode.", ["bootstrap", "agents"])
        self.audit.log("agent-01", None, "bootstrap", "Initialized GIZMO bootstrap v0", agents=len(agents), capabilities=capabilities)
        return {"ready": True, "agents": len(agents), "mode": self.security.mode().value, "capabilities": capabilities}

    def inspect_capabilities(self) -> dict[str, Any]:
        import shutil
        return {
            "python": bool(shutil.which("python") or shutil.which("python3")),
            "git": bool(shutil.which("git")),
            "node": bool(shutil.which("node")),
            "unreal": self.unreal.detect(),
        }

    def plan_objective(self, project: str, objective: str) -> list[Task]:
        relevant_memory = self.memory.search(objective, limit=3)
        architect = Task(project=project, objective=f"Architect plan for: {objective}", assigned_agent="agent-01", priority=1)
        product = Task(project=project, objective=f"Define requirements and acceptance criteria for: {objective}", assigned_agent="agent-03", priority=1, dependencies=[architect.id])
        qa = Task(project=project, objective=f"Verify completed work satisfies: {objective}", assigned_agent="agent-27", priority=1, dependencies=[product.id])
        for task in [architect, product, qa]:
            task.record("memory_retrieval", f"Retrieved {len(relevant_memory)} relevant memories before planning")
            self.tasks.create_task(task)
        self.bus.send(StructuredMessage("agent-01", "agent-03", "TASK_DEPENDENCY", {"depends_on": architect.id, "objective": objective}))
        self.audit.log("agent-01", None, "plan_objective", "Created objective plan", project=project, tasks=[t.id for t in [architect, product, qa]])
        return [architect, product, qa]

    def execute_task(self, task: Task) -> Task:
        if self.security.require_approval("plan"):
            task.status = TaskStatus.WAITING
            task.record("approval", "Waiting for human approval under current mode")
            self.tasks.save(task)
            return task
        return self._execute_allowed_task(task)

    def _execute_allowed_task(self, task: Task) -> Task:
        self.costs.record_operation(f"execute:{task.assigned_agent}")
        task.status = TaskStatus.RUNNING
        task.record("run", "Task execution started")
        agent = core_agent_map().get(task.assigned_agent)
        if not agent:
            task.status = TaskStatus.FAILED
            task.result = "Assigned agent not found"
            self.tasks.save(task)
            return task
        task.status = TaskStatus.COMPLETED
        task.result = f"{agent.name} completed bootstrap-level work for objective: {task.objective}"
        task.lessons_learned.append("Bootstrap executor can complete planning/review tasks with structured audit records.")
        task.record("complete", task.result)
        self.tasks.save(task)
        self.memory.add(MemoryKind.EPISODIC, task.project, f"{task.assigned_agent} completed {task.objective}. Lesson: {task.lessons_learned[-1]}", ["task", task.assigned_agent], {"task_id": task.id})
        self.audit.log(task.assigned_agent, task.id, "execute_task", "completed", task_result=task.result)
        return task

    def github_workspace_demo(self, project_name: str = "gizmo-github-demo", execute_git: bool = False) -> dict[str, Any]:
        """Run a safe GitHub workspace loop demonstration.

        By default it does not modify the current repository branch; it creates the
        task and PR plan and records the branch workflow as an auditable artifact.
        """
        self.security.set_mode(OperatingMode.ASSISTED)
        repository = self.github.inspect_repository()
        task = self.github.create_workspace_task(
            project_name,
            "Create a branch-per-task GitHub workspace plan with tests and human-reviewed merge policy.",
        )
        run = self.github.start_branch_for_task(task.id, base_branch=repository.get("current_branch") or "main", execute_git=execute_git)
        reviewed = self.github.complete_task_review(task.id, checks_passed=True, summary="GitHub workspace loop demo completed with PR plan and policy gates.")
        status = self.github.export_status()
        return {"repository": repository, "task": reviewed.to_dict(), "workspace_run": run.to_dict(), "github_status": status}

    def run_demo_project(self, project_name: str, objective: str) -> dict[str, Any]:
        previous = self.memory.search("dependency-free testable web app", namespace=project_name, limit=1)
        learned_note = previous[0]["content"] if previous else None
        plan = self.plan_objective(project_name, objective)
        self.security.set_mode(OperatingMode.ASSISTED)
        executed = [self._execute_allowed_task(task) for task in plan]
        artifact = self.projects.create_small_web_app(project_name, learned_note)
        self.memory.add(MemoryKind.PROJECT, project_name, "For small web apps, keep the first pass dependency-free, include an interaction test target, and document the lesson.", ["dependency-free", "testable", "web app"], {"artifact": artifact})
        self.audit.log("agent-27", executed[-1].id, "demo_project", "Generated harmless web app artifact", artifact=artifact)
        return {"project": project_name, "tasks": [task.to_dict() for task in executed], "artifact": artifact}

    def self_test(self) -> dict[str, Any]:
        boot = self.bootstrap()
        first = self.run_demo_project("demo-web-app-one", "Build a small web application")
        second = self.run_demo_project("demo-web-app-two", "Build a second small web application using prior lessons")
        github_demo = self.github_workspace_demo(execute_git=False)
        memories = self.memory.search("dependency-free testable web app", limit=10)
        github_memories = self.memory.search("GitHub task workflow", limit=5)
        result = {
            "bootstrap": boot,
            "first_demo": first,
            "second_demo": second,
            "github_demo": github_demo,
            "memory_matches": len(memories),
            "github_memory_matches": len(github_memories),
            "passed": boot["agents"] == 27 and len(memories) >= 2 and len(github_memories) >= 1,
        }
        self.store.write(result, "monitoring", "self_test_report.json")
        self.audit.log("agent-27", None, "self_test", "passed" if result["passed"] else "failed", report=result)
        return result

    def status(self) -> dict[str, Any]:
        agents = self.store.read("agents", "core_agents.json", default=[])
        audit = self.store.read("monitoring", "audit_log.json", default=[])
        tasks = [task.to_dict() for task in self.tasks.list_tasks()] if self.store.path("tasks").exists() else []
        return {
            "mode": self.security.mode().value,
            "agents": len(agents),
            "tasks": len(tasks),
            "completed_tasks": sum(1 for task in tasks if task["status"] == "COMPLETED"),
            "audit_events": len(audit),
            "github": self.github.export_status(),
            "capabilities": self.store.read("config", "capabilities.json", default={}),
        }
