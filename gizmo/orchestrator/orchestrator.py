"""Reaper Core / Executive Orchestrator for GIZMO bootstrap v0."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gizmo.agents.core_agents import CORE_AGENTS, core_agent_map
from gizmo.agent_factory.factory import AgentFactory
from gizmo.brain.bootstrap import BrainBootstrapper
from gizmo.brain.memory_api import SecondBrain
from gizmo.communication.message_bus import MessageBus
from gizmo.core.models import MemoryKind, OperatingMode, StructuredMessage, Task, TaskStatus
from gizmo.core.store import JsonStore
from gizmo.github.api_adapter import GitHubApiAdapter
from gizmo.github.workspace import GitHubWorkspaceLoop
from gizmo.memory.memory_system import MemorySystem
from gizmo.monitoring.cost_manager import CostManager
from gizmo.monitoring.logger import AuditLogger
from gizmo.projects.project_generator import ProjectGenerator
from gizmo.security.approval_policy import ApprovalPolicyEngine
from gizmo.security.security_system import SecuritySystem
from gizmo.second_brain.command_router import SecondBrainCommandRouter
from gizmo.second_brain.context_indexer import RepoContextIndexer
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
        self.github_api = GitHubApiAdapter(self.store, self.security, self.audit)
        self.policy = ApprovalPolicyEngine(self.store, self.audit)
        self.context_indexer = RepoContextIndexer(Path.cwd())
        self.second_brain = SecondBrainCommandRouter(self.memory, self.tasks, self.context_indexer)
        self.brain_core = SecondBrain(self.workspace / "second_brain")

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

    def policy_demo(self, project_name: str = "gizmo-policy-demo") -> dict[str, Any]:
        """Exercise approval gates without authorizing production/destructive work."""
        self.policy.set_project_mode(project_name, OperatingMode.ASSISTED)
        safe = self.policy.evaluate_action(project_name, "plan", "agent-01")
        merge = self.policy.gate_merge(project_name, {"tests": True, "secret_scan": True, "review": True})
        deploy_block = self.policy.gate_deploy(project_name, {"tests": True, "secret_scan": True, "security_review": False, "quality_review": True})
        status = self.policy.export_status()
        return {
            "safe_decision": safe.to_dict(),
            "merge_decision": merge.to_dict(),
            "deploy_decision": deploy_block.to_dict(),
            "policy_status": status,
        }

    def brain_initialization_demo(self) -> dict[str, Any]:
        """Initialize the persistent shared Second Brain from verified repo data."""
        self.bootstrap()
        bootstrapper = BrainBootstrapper(self.brain_core, Path.cwd())
        report = bootstrapper.initialize_from_repository()
        recall = self.brain_core.recall("approval GitHub second brain", limit=5)
        semantic = self.brain_core.semantic_search("autonomous learning memory retrieval", limit=5)
        result = {
            "ready": report["health"]["memories"] >= 40 and len(recall) > 0 and len(semantic) > 0,
            "report": report,
            "recall_count": len(recall),
            "semantic_count": len(semantic),
            "sample_recall": [memory.to_dict() for memory in recall[:3]],
        }
        self.store.write(result, "brain", "initialization_report.json")
        self.audit.log("agent-01", None, "brain.initialization", "passed" if result["ready"] else "failed", report=result)
        return result

    def brain_phase2_demo(self) -> dict[str, Any]:
        """Exercise intelligent recall, context building, and knowledge-gap detection."""
        init = self.brain_initialization_demo()
        self.brain_core.record_procedure(
            "Hybrid retrieval procedure",
            "Before significant work, retrieve project state, decisions, lessons, procedures, warnings, and related memories using hybrid scoring.",
            source="phase-2",
            source_agent="agent-26",
            importance=8,
            confidence=0.88,
            tags=["procedure", "retrieval", "context"],
            entities=["Second Brain", "Learning Core"],
        )
        context = self.brain_core.build_context("Build GitHub deployment learning with workflow failure detection", project="Gizmo")
        hybrid = self.brain_core.hybrid_search("Creator approval policy GitHub workflow", project="Gizmo", include_trace=True, limit=5)
        result = {
            "ready": len(hybrid) > 0 and len(context.useful_context) > 0 and len(context.retrieval_trace) > 0,
            "initialization": init["ready"],
            "hybrid_results": len(hybrid),
            "context_ready": context.ready,
            "context": context.to_dict(),
            "top_trace": hybrid[0][0].to_dict() if hybrid else None,
        }
        self.store.write(result, "brain", "phase2_report.json")
        self.audit.log("agent-26", None, "brain.phase2", "passed" if result["ready"] else "failed", report=result)
        return result

    def second_brain_demo(self) -> dict[str, Any]:
        """Exercise GitHub-side second brain command flow."""
        self.bootstrap()
        commands = [
            "/gizmo status",
            "/gizmo context approval policy github",
            "/gizmo remember GitHub issues are the project nervous system; keep decisions and lessons close to code.",
            "/gizmo recall GitHub issues nervous system",
            "/gizmo plan Make GIZMO answer repository questions from issue comments",
        ]
        results = [self.second_brain.route(command, actor="owner").to_dict() for command in commands]
        self.store.write(results, "second_brain", "demo_results.json")
        self.audit.log("agent-01", None, "second_brain.demo", "completed", commands=len(commands))
        return {
            "ready": all(result["status"] in {"OK", "IGNORED"} for result in results),
            "commands": len(results),
            "indexed_files": results[0]["artifacts"]["index"]["file_count"],
            "memory_result": results[2]["status"],
            "plan_tasks": len(results[4]["artifacts"].get("tasks", [])),
            "results": results,
        }

    def github_api_demo(self, project_name: str = "gizmo-github-api-demo", execute: bool = False) -> dict[str, Any]:
        """Prepare GitHub issue/PR/API sync actions with approval gates."""
        self.security.set_mode(OperatingMode.ASSISTED)
        workspace = self.github_workspace_demo(project_name=project_name, execute_git=False)
        repo = workspace["repository"]
        task = self.tasks.load(workspace["task"]["id"])
        pr_plan = workspace["workspace_run"]["pr_plan"]
        if not repo.get("owner") or not repo.get("repo"):
            return {"blocked": True, "reason": "GitHub remote not detected", "workspace": workspace}
        issue_action = self.github_api.create_issue_from_task(repo["owner"], repo["repo"], task, execute=execute)
        pr_action = self.github_api.open_pull_request_from_plan(repo["owner"], repo["repo"], pr_plan, execute=execute)
        ci_action = self.github_api.read_workflow_runs(repo["owner"], repo["repo"], branch=pr_plan["branch"], execute=execute)
        status = self.github_api.export_status()
        return {
            "workspace": workspace,
            "issue_action": issue_action.to_dict(),
            "pr_action": pr_action.to_dict(),
            "ci_action": ci_action.to_dict(),
            "api_status": status,
        }

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
        github_api_demo = self.github_api_demo(project_name="gizmo-github-api-self-test", execute=False)
        policy_demo = self.policy_demo(project_name="gizmo-policy-self-test")
        second_brain_demo = self.second_brain_demo()
        memories = self.memory.search("dependency-free testable web app", limit=10)
        github_memories = self.memory.search("GitHub task workflow", limit=5)
        result = {
            "bootstrap": boot,
            "first_demo": first,
            "second_demo": second,
            "github_demo": github_demo,
            "github_api_demo": github_api_demo,
            "policy_demo": policy_demo,
            "second_brain_demo": second_brain_demo,
            "memory_matches": len(memories),
            "github_memory_matches": len(github_memories),
            "passed": boot["agents"] == 27 and len(memories) >= 2 and len(github_memories) >= 1 and github_api_demo["api_status"]["api_actions"] >= 3 and policy_demo["policy_status"]["pending_approvals"] >= 1 and second_brain_demo["ready"],
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
            "github_api": self.github_api.export_status(),
            "policy": self.policy.export_status(),
            "second_brain": {"indexed_files": self.context_indexer.build_index()["file_count"]},
            "brain_core": self.brain_core.export_health(),
            "capabilities": self.store.read("config", "capabilities.json", default={}),
        }
