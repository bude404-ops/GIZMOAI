import subprocess
from pathlib import Path

from gizmo.core.models import OperatingMode
from gizmo.core.store import JsonStore
from gizmo.github.workspace import GitHubWorkspaceLoop, LocalGitAdapter
from gizmo.memory.memory_system import MemorySystem
from gizmo.monitoring.logger import AuditLogger
from gizmo.security.security_system import SecuritySystem
from gizmo.tasks.task_engine import TaskEngine


def init_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "remote", "add", "origin", "https://github.com/bude404-ops/GIZMOAI.git"], cwd=path, check=True)
    (path / "README.md").write_text("# test repo\n")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "init"], cwd=path, check=True, capture_output=True, text=True)


def build_loop(tmp_path: Path):
    store = JsonStore(tmp_path / "state")
    tasks = TaskEngine(store)
    memory = MemorySystem(store)
    security = SecuritySystem(store)
    audit = AuditLogger(store)
    repo = tmp_path / "repo"
    init_git_repo(repo)
    loop = GitHubWorkspaceLoop(store, tasks, memory, security, audit, repo_path=repo, git=LocalGitAdapter(repo))
    return loop, security, tasks, memory, repo


def test_github_workspace_inspects_remote_and_parses_repo(tmp_path: Path):
    loop, _, _, _, _ = build_loop(tmp_path)
    info = loop.inspect_repository()
    assert info["owner"] == "bude404-ops"
    assert info["repo"] == "GIZMOAI"
    assert info["current_branch"] == "main"


def test_github_workspace_creates_task_pr_plan_and_memory_without_branch_checkout(tmp_path: Path):
    loop, security, tasks, memory, repo = build_loop(tmp_path)
    security.set_mode(OperatingMode.ASSISTED)
    task = loop.create_workspace_task("gizmo", "Add branch per task workflow")
    run = loop.start_branch_for_task(task.id, base_branch="main", execute_git=False)
    reviewed = loop.complete_task_review(task.id, True, "checks passed")

    assert run.status == "BRANCH_READY"
    assert run.pr_plan is not None
    assert run.pr_plan.base_branch == "main"
    assert "python -m pytest -q" in run.pr_plan.checks
    assert LocalGitAdapter(repo).current_branch() == "main"
    assert reviewed.status.value == "REVIEW"
    assert memory.search("GitHub task workflow", namespace="gizmo")
    assert tasks.load(task.id).artifacts


def test_manual_mode_blocks_branch_creation_until_approval(tmp_path: Path):
    loop, security, tasks, _, _ = build_loop(tmp_path)
    security.set_mode(OperatingMode.MANUAL)
    task = loop.create_workspace_task("gizmo", "Manual mode protected branch")
    run = loop.start_branch_for_task(task.id, base_branch="main", execute_git=True)
    blocked = tasks.load(task.id)
    assert run.status == "WAITING_FOR_APPROVAL"
    assert blocked.status.value == "WAITING"


def test_assisted_mode_can_create_local_task_branch_when_explicitly_enabled(tmp_path: Path):
    loop, security, _, _, repo = build_loop(tmp_path)
    security.set_mode(OperatingMode.ASSISTED)
    task = loop.create_workspace_task("gizmo", "Create explicit local branch")
    run = loop.start_branch_for_task(task.id, base_branch="main", execute_git=True)
    assert run.status == "BRANCH_READY"
    assert LocalGitAdapter(repo).current_branch().startswith("gizmo/task-")
