"""GitHub workspace loop foundations.

This module does not hide writes behind magic. It plans branch/task/PR work,
executes local git operations only when policy allows, and represents pull
requests as auditable plans unless a later adapter explicitly performs the
network call.
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from gizmo.core.models import MemoryKind, Task, TaskStatus, now_iso
from gizmo.core.store import JsonStore
from gizmo.memory.memory_system import MemorySystem
from gizmo.monitoring.logger import AuditLogger
from gizmo.security.security_system import SecuritySystem
from gizmo.tasks.task_engine import TaskEngine


@dataclass
class PullRequestPlan:
    id: str
    task_id: str
    branch: str
    base_branch: str
    title: str
    body: str
    checks: list[str]
    status: str = "PLANNED"
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WorkspaceRun:
    id: str
    task_id: str
    branch: str
    base_branch: str
    status: str
    steps: list[dict[str, Any]]
    pr_plan: PullRequestPlan | None
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["pr_plan"] = self.pr_plan.to_dict() if self.pr_plan else None
        return data


class LocalGitAdapter:
    """Small subprocess wrapper for local git operations."""

    def __init__(self, repo_path: str | Path) -> None:
        self.repo_path = Path(repo_path)

    def run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.repo_path,
            text=True,
            capture_output=True,
            check=check,
        )

    def current_branch(self) -> str:
        return self.run("branch", "--show-current").stdout.strip()

    def remote_url(self) -> str:
        result = self.run("remote", "get-url", "origin", check=False)
        return result.stdout.strip() if result.returncode == 0 else ""

    def has_changes(self) -> bool:
        return bool(self.run("status", "--short").stdout.strip())

    def create_branch(self, branch: str) -> None:
        self.run("checkout", "-B", branch)

    def checkout(self, branch: str) -> None:
        self.run("checkout", branch)

    def changed_files(self) -> list[str]:
        out = self.run("diff", "--name-only", "HEAD").stdout.strip()
        return [line for line in out.splitlines() if line]


class GitHubWorkspaceLoop:
    """Branch-per-task workflow with PR planning and policy gates."""

    def __init__(
        self,
        store: JsonStore,
        task_engine: TaskEngine,
        memory: MemorySystem,
        security: SecuritySystem,
        audit: AuditLogger,
        repo_path: str | Path = ".",
        git: LocalGitAdapter | None = None,
    ) -> None:
        self.store = store
        self.tasks = task_engine
        self.memory = memory
        self.security = security
        self.audit = audit
        self.git = git or LocalGitAdapter(repo_path)

    def inspect_repository(self) -> dict[str, Any]:
        url = self.git.remote_url()
        owner, repo = self._parse_github_remote(url)
        info = {
            "remote_url_present": bool(url),
            "owner": owner,
            "repo": repo,
            "current_branch": self.git.current_branch(),
            "has_uncommitted_changes": self.git.has_changes(),
        }
        self.store.write(info, "github", "repository.json")
        self.audit.log("agent-10", None, "github.inspect", "Repository inspected", repository=info)
        return info

    def create_workspace_task(self, project: str, objective: str, assigned_agent: str = "agent-10") -> Task:
        relevant = self.memory.search(objective, namespace=project, limit=3)
        task = Task(project=project, objective=objective, assigned_agent=assigned_agent, priority=2)
        task.record("memory_retrieval", f"Retrieved {len(relevant)} project memories before GitHub planning")
        self.tasks.create_task(task)
        self.audit.log(assigned_agent, task.id, "github.task.create", "Created GitHub workspace task")
        return task

    def branch_name_for(self, task: Task) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", task.objective.lower()).strip("-")[:48] or "task"
        return f"gizmo/{task.id}-{slug}"

    def plan_pull_request(self, task: Task, branch: str, base_branch: str = "main", checks: list[str] | None = None) -> PullRequestPlan:
        checks = checks or ["python -m pytest -q", "python scripts/scan_secrets.py"]
        plan = PullRequestPlan(
            id=f"pr-plan-{uuid4().hex[:12]}",
            task_id=task.id,
            branch=branch,
            base_branch=base_branch,
            title=f"GIZMO task: {task.objective[:72]}",
            body=(
                f"## Objective\n{task.objective}\n\n"
                f"## Assigned agent\n{task.assigned_agent}\n\n"
                "## Required checks\n" + "\n".join(f"- `{check}`" for check in checks) + "\n\n"
                "## Policy\nHuman approval is required before merge or production deployment."
            ),
            checks=checks,
        )
        self.store.write(plan.to_dict(), "github", "pr_plans", f"{plan.id}.json")
        self.audit.log("agent-10", task.id, "github.pr.plan", "Created pull request plan", pr_plan=plan.to_dict())
        return plan

    def start_branch_for_task(self, task_id: str, base_branch: str | None = None, execute_git: bool = True) -> WorkspaceRun:
        task = self.tasks.load(task_id)
        base = base_branch or self.git.current_branch() or "main"
        branch = self.branch_name_for(task)
        steps: list[dict[str, Any]] = []
        task.status = TaskStatus.PLANNING
        task.record("github_workspace", f"Preparing branch {branch} from {base}")

        needs_approval = self.security.require_approval("git_branch")
        if needs_approval:
            task.status = TaskStatus.WAITING
            task.record("approval", "Branch creation requires approval under current mode")
            self.tasks.save(task)
            run = WorkspaceRun(f"workspace-{uuid4().hex[:12]}", task.id, branch, base, "WAITING_FOR_APPROVAL", steps, None)
            self.store.write(run.to_dict(), "github", "runs", f"{run.id}.json")
            return run

        if execute_git:
            self.git.create_branch(branch)
            steps.append({"timestamp": now_iso(), "action": "git.checkout_branch", "result": branch})
        pr_plan = self.plan_pull_request(task, branch, base)
        task.status = TaskStatus.RUNNING
        task.artifacts.append(f"github/pr_plans/{pr_plan.id}.json")
        task.record("github_workspace", "Branch workspace started", branch=branch, pr_plan=pr_plan.id)
        self.tasks.save(task)
        self.memory.add(MemoryKind.PROCEDURAL, task.project, "GitHub task workflow: create isolated branch, implement, run tests, security scan, then prepare PR for human-reviewed merge.", ["github", "branch", "pr", "workflow"], {"task_id": task.id})
        run = WorkspaceRun(f"workspace-{uuid4().hex[:12]}", task.id, branch, base, "BRANCH_READY", steps, pr_plan)
        self.store.write(run.to_dict(), "github", "runs", f"{run.id}.json")
        self.audit.log("agent-10", task.id, "github.branch.start", "Branch workspace ready", run=run.to_dict())
        return run

    def complete_task_review(self, task_id: str, checks_passed: bool, summary: str) -> Task:
        task = self.tasks.load(task_id)
        task.status = TaskStatus.REVIEW if checks_passed else TaskStatus.FAILED
        task.result = summary
        task.tests.append("checks_passed" if checks_passed else "checks_failed")
        task.record("review", summary, checks_passed=checks_passed)
        if checks_passed:
            task.lessons_learned.append("Validated GitHub workspace tasks should preserve isolated branches and PR plans before merge.")
            self.memory.add(MemoryKind.EPISODIC, task.project, task.lessons_learned[-1], ["github", "lesson"], {"task_id": task.id})
        self.tasks.save(task)
        self.audit.log("agent-27", task.id, "github.review", "review complete", checks_passed=checks_passed)
        return task

    def _parse_github_remote(self, url: str) -> tuple[str | None, str | None]:
        if not url:
            return None, None
        match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$", url)
        if not match:
            return None, None
        return match.group("owner"), match.group("repo")

    def export_status(self) -> dict[str, Any]:
        runs = [json.loads(path.read_text()) for path in self.store.path("github", "runs").glob("*.json")] if self.store.path("github", "runs").exists() else []
        plans = [json.loads(path.read_text()) for path in self.store.path("github", "pr_plans").glob("*.json")] if self.store.path("github", "pr_plans").exists() else []
        return {"repository": self.store.read("github", "repository.json", default={}), "runs": len(runs), "pr_plans": len(plans)}
