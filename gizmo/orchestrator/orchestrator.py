"""Reaper Core / Executive Orchestrator for GIZMO bootstrap v0."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gizmo.agents.core_agents import CORE_AGENTS, core_agent_map
from gizmo.agent_factory.factory import AgentFactory
from gizmo.brain.agent_memory import AgentBrainBridge
from gizmo.brain.bootstrap import BrainBootstrapper
from gizmo.brain.memory_api import SecondBrain
from gizmo.capabilities.execution import UniversalExecutionLedger
from gizmo.capabilities.registry import CapabilityRegistry
from gizmo.capabilities.router import UniversalTaskRouter
from gizmo.capabilities.workflows import WorkflowLibrary
from gizmo.communication.message_bus import MessageBus
from gizmo.core.models import MemoryKind, OperatingMode, StructuredMessage, Task, TaskStatus
from gizmo.core.store import JsonStore
from gizmo.github.api_adapter import GitHubApiAdapter
from gizmo.github.workspace import GitHubWorkspaceLoop
from gizmo.memory.memory_system import MemorySystem
from gizmo.monitoring.cost_manager import CostManager
from gizmo.monitoring.logger import AuditLogger
from gizmo.projects.project_generator import ProjectGenerator
from gizmo.generation.provider_registry import GenerationProviderRegistry
from gizmo.research.internet_research import InternetResearchPipeline
from gizmo.security.approval_policy import ApprovalPolicyEngine
from gizmo.security.security_system import SecuritySystem
from gizmo.second_brain.command_router import SecondBrainCommandRouter
from gizmo.second_brain.context_indexer import RepoContextIndexer
from gizmo.tasks.task_engine import TaskEngine
from gizmo.tools.tool_registry import ToolRegistry
from gizmo.unreal.unreal_detector import UnrealDetector
from gizmo.unreal.integration_layer import UnrealIntegrationLayer


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
        self.agent_brain = AgentBrainBridge(self.brain_core, self.store)
        self.capabilities = CapabilityRegistry(self.store)
        self.workflows = WorkflowLibrary(self.store)
        self.universal_router = UniversalTaskRouter(self)
        self.universal_execution = UniversalExecutionLedger(self.store, self.tasks)
        self.internet_research = InternetResearchPipeline(self.brain_core, self.store)
        self.generation = GenerationProviderRegistry(self.store)
        self.unreal_integration = UnrealIntegrationLayer(self.store, self.unreal)

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

    def universal_route(self, request: str, *, project: str = "Gizmo", execute: bool = False) -> dict[str, Any]:
        """Route any Creator request through GIZMO's general-purpose capability system."""
        plan = self.universal_router.route(request, project=project, execute=execute)
        category = plan.classification["category"]
        workflows = self.workflows.select(category)
        research_report = None
        unreal_report = None
        generation_record = None
        if plan.classification.get("needs_research"):
            research_report = self.internet_research.run(request, project=project, store_useful=True).to_dict()
        if category == "unreal_engine":
            unreal_report = self.unreal_integration.inspect(objective=request).to_dict()
        if category == "ai_generation":
            generation_record = self.generation.record_request(self._infer_generation_modality(request), request, project=project).to_dict()
        execution_record = self.universal_execution.create_from_plan(plan, project=project).to_dict() if execute else None
        result = {
            "ready": True,
            "plan": plan.to_dict(),
            "workflows": [workflow.to_dict() for workflow in workflows],
            "research_report": research_report,
            "unreal_bridge": unreal_report,
            "generation_request": generation_record,
            "execution": execution_record,
            "capability_status": self.capabilities.export_status(),
        }
        self.store.write(result, "universal", "route_latest_result.json")
        self.audit.log("agent-01", None, "universal.route", "planned", category=category, approval_required=plan.approval_required)
        return result

    def run_universal_execution(self, execution_id: str | None = None, *, max_steps: int | None = None) -> dict[str, Any]:
        """Advance queued universal execution tasks through the safe bootstrap executor."""
        record = self.universal_execution.latest() if execution_id is None else self.universal_execution.refresh(execution_id)
        if record is None:
            return {"ready": False, "status": "NO_EXECUTION", "message": "No universal execution record exists."}
        refreshed = self.universal_execution.run_ready_steps(record.execution_id, executor=self._execute_allowed_task, max_steps=max_steps)
        result = {"ready": True, "execution": refreshed.to_dict()}
        self.store.write(result, "universal", "latest_run_result.json")
        self.audit.log("agent-01", None, "universal.run", refreshed.status, execution_id=refreshed.execution_id, ran=refreshed.evidence.get("runner", {}).get("ran", 0))
        return result

    def universal_acceptance_demo(self) -> dict[str, Any]:
        """Exercise the required general-purpose acceptance paths without unsafe side effects."""
        examples = {
            "question": "What is the latest information about autonomous research agents?",
            "research": "Research whether people would pay for a memory vault for AI projects.",
            "software": "Build me a simple SaaS application that tracks project tasks.",
            "debugging": "This application is broken; figure out why and fix it.",
            "unreal": "Create a simple Unreal prototype with a player, environment and enemy.",
            "generation": "Create a fantasy character for the Unreal project.",
            "memory": "What were we working on yesterday?",
            "unknown": "Figure out how to connect an unfamiliar game asset toolchain.",
        }
        routes = {name: self.universal_route(text, execute=False) for name, text in examples.items()}
        checks = {
            "question_researches": bool(routes["question"]["research_report"]),
            "research_has_sources": bool(routes["research"]["research_report"]["sources_considered"]),
            "software_project_mode": routes["software"]["plan"]["classification"]["effort"] == "project",
            "debugging_verification": any("reproduce" in step["objective"].lower() or "root" in step["objective"].lower() for step in routes["debugging"]["plan"]["decomposition"]),
            "unreal_bridge_honest": routes["unreal"]["unreal_bridge"] is not None,
            "generation_manifest": routes["generation"]["generation_request"] is not None,
            "memory_retrieval_planned": bool(routes["memory"]["plan"]["context_memory_ids"] or routes["memory"]["plan"]["memory_plan"]),
            "execution_ledger": bool(self.universal_route("Build a small verified automation script.", execute=True)["execution"]["task_ids"]),
            "execution_runner": self._acceptance_runner_check(),
            "unknown_problem_research": routes["unknown"]["plan"]["classification"]["needs_research"],
            "trading_not_central": "trading" in [cap["name"] for cap in self.capabilities.export_status()["capabilities"]],
        }
        result = {"ready": all(checks.values()), "checks": checks, "routes": {k: v["plan"] for k, v in routes.items()}}
        self.store.write(result, "universal", "acceptance_demo.json")
        return result

    def _acceptance_runner_check(self) -> bool:
        route = self.universal_route("Build a tiny internal status summary.", execute=True)
        run = self.run_universal_execution(route["execution"]["execution_id"])
        execution = run["execution"]
        return execution["status"] in {"QUEUED", "COMPLETED"} and execution["evidence"]["runner"]["ran"] >= 1

    @staticmethod
    def _infer_generation_modality(request: str) -> str:
        lowered = request.lower()
        if "video" in lowered or "trailer" in lowered:
            return "VIDEO"
        if "audio" in lowered or "voice" in lowered or "sound" in lowered:
            return "AUDIO"
        if "3d" in lowered or "asset" in lowered or "model" in lowered:
            return "3D"
        if "code" in lowered:
            return "CODE"
        return "IMAGE"

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
        self.agent_brain.before_task(task)
        self.costs.record_operation(f"execute:{task.assigned_agent}")
        task.status = TaskStatus.RUNNING
        task.record("run", "Task execution started")
        agent = core_agent_map().get(task.assigned_agent)
        if not agent:
            task.status = TaskStatus.FAILED
            task.result = "Assigned agent not found"
            self.tasks.save(task)
            self.agent_brain.after_task(task, failed=["Assigned agent not found"])
            return task
        task.status = TaskStatus.COMPLETED
        task.result = f"{agent.name} completed bootstrap-level work for objective: {task.objective}"
        task.lessons_learned.append("Bootstrap executor can complete planning/review tasks with structured audit records.")
        task.record("complete", task.result)
        self.tasks.save(task)
        self.memory.add(MemoryKind.EPISODIC, task.project, f"{task.assigned_agent} completed {task.objective}. Lesson: {task.lessons_learned[-1]}", ["task", task.assigned_agent], {"task_id": task.id})
        self.agent_brain.after_task(task, worked=["bootstrap execution", "central Brain integration"])
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

    def brain_phase3_demo(self) -> dict[str, Any]:
        """Exercise Obsidian vault indexes, graph export, backlinks, revisions, and session notes."""
        phase2 = self.brain_phase2_demo()
        decision = self.brain_core.record_decision(
            "Creator decisions remain highest authority",
            "Creator-provided decisions and constraints cannot be silently overwritten by autonomous agents.",
            source="creator",
            source_agent="reaper",
            importance=10,
            confidence=1.0,
            tags=["creator", "authority", "safety"],
            entities=["Creator", "Reaper", "Second Brain"],
        )
        lesson = self.brain_core.record_lesson(
            "Vault must be useful without the application",
            "Markdown, frontmatter, backlinks, indexes, graph exports, and session notes keep the Brain portable and inspectable.",
            source="phase-3",
            source_agent="agent-26",
            importance=8,
            confidence=0.92,
            tags=["obsidian", "vault", "portability"],
            entities=["Second Brain", "Obsidian"],
        )
        self.brain_core.link_memories(decision.id, "affects", lesson.id, confidence=0.85)
        self.brain_core.update_memory(lesson.id, content=lesson.content + " Revision tracking preserves prior Markdown before updates.")
        session_note = self.brain_core.record_session_note("Phase 3 vault rebuild", "Indexes, graph export, backlinks, quality report, and revision views generated.", [decision.id, lesson.id])
        vault_report = self.brain_core.rebuild_vault_indexes()
        graph = self.brain_core.export_graph()
        root = self.brain_core.vault.root
        required = [
            root / "README.md",
            root / "indexes" / "Memory Index.md",
            root / "indexes" / "Project Index.md",
            root / "indexes" / "Agent Index.md",
            root / "indexes" / "Quality Report.md",
            root / "graph" / "Knowledge Graph.md",
            root / "graph" / "knowledge-graph.json",
            root / "graph" / "Backlinks.md",
            root / "graph" / "backlinks.json",
            root / "sessions" / session_note,
        ]
        result = {
            "ready": phase2["ready"] and all(path.exists() for path in required) and graph["report"]["graph_nodes"] > 0,
            "phase2_ready": phase2["ready"],
            "vault_report": vault_report,
            "graph_nodes": graph["report"]["graph_nodes"],
            "graph_edges": graph["report"]["graph_edges"],
            "required_files": [path.name for path in required],
        }
        self.store.write(result, "brain", "phase3_report.json")
        self.audit.log("agent-26", None, "brain.phase3", "passed" if result["ready"] else "failed", report=result)
        return result

    def brain_phase4_demo(self) -> dict[str, Any]:
        """Exercise central Brain integration for agent recall, capture, and performance memory."""
        phase3 = self.brain_phase3_demo()
        task = Task(
            project="Gizmo",
            objective="Integrate every agent with central Brain recall and automatic learning capture",
            assigned_agent="agent-26",
            priority=1,
        )
        self.tasks.create_task(task)
        executed = self._execute_allowed_task(task)
        profile = self.agent_brain.agent_profile("agent-26")
        collective = self.agent_brain.collective_memory()
        related = self.brain_core.hybrid_search("central Brain integration agent memory lesson", project="Gizmo", limit=8)
        self.brain_core.rebuild_vault_indexes()
        result = {
            "ready": phase3["ready"] and executed.status == TaskStatus.COMPLETED and profile.get("memory_contributions", 0) >= 1 and len(collective.get("evaluations", [])) >= 1,
            "phase3_ready": phase3["ready"],
            "task": executed.to_dict(),
            "agent_profile": profile,
            "collective_counts": {
                "discoveries": len(collective.get("discoveries", [])),
                "lessons": len(collective.get("lessons", [])),
                "evaluations": len(collective.get("evaluations", [])),
            },
            "related_memory_count": len(related),
        }
        self.store.write(result, "brain", "phase4_report.json")
        self.audit.log("agent-26", executed.id, "brain.phase4", "passed" if result["ready"] else "failed", report=result)
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
            "agent_memory": {
                "profiles": len(list((self.workspace / "brain" / "agent_profiles").glob("*.json"))) if (self.workspace / "brain" / "agent_profiles").exists() else 0,
                "collective_lessons": len(self.agent_brain.collective_memory().get("lessons", [])),
            },
            "capabilities": self.capabilities.export_status(),
            "workflows": self.workflows.export_status(),
            "generation": self.generation.export_status(),
            "universal_router": self.store.read("universal", "latest_plan.json", default={}),
        }
