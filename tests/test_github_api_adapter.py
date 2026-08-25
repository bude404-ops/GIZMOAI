import os
from pathlib import Path

from gizmo.core.models import OperatingMode, Task
from gizmo.core.store import JsonStore
from gizmo.github.api_adapter import GitHubApiAdapter
from gizmo.memory.memory_system import MemorySystem
from gizmo.monitoring.logger import AuditLogger
from gizmo.security.security_system import SecuritySystem
from gizmo.tasks.task_engine import TaskEngine


class FakeHttp:
    def __init__(self):
        self.calls = []

    def request(self, method, url, headers, body=None):
        self.calls.append({"method": method, "url": url, "headers": headers, "body": body})
        return {"ok": True, "status": 201, "data": {"html_url": "https://example.invalid/pr/1"}}


def build_adapter(tmp_path: Path, http=None):
    store = JsonStore(tmp_path)
    security = SecuritySystem(store)
    audit = AuditLogger(store)
    adapter = GitHubApiAdapter(store, security, audit, http=http or FakeHttp())
    return adapter, security, store


def test_issue_creation_is_planned_without_execution(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    adapter, security, _ = build_adapter(tmp_path)
    security.set_mode(OperatingMode.ASSISTED)
    task = Task(project="gizmo", objective="Sync task to issue", assigned_agent="agent-10")
    action = adapter.create_issue_from_task("bude404-ops", "GIZMOAI", task, execute=False)
    assert action.status == "PLANNED_NOT_EXECUTED"
    assert action.payload["title"].startswith("GIZMO task")
    assert action.result["credentials"]["available"] is False


def test_write_action_waits_for_approval_in_manual_mode_even_with_token(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "dummy-token-value")
    adapter, security, _ = build_adapter(tmp_path)
    security.set_mode(OperatingMode.MANUAL)
    task = Task(project="gizmo", objective="Protected issue", assigned_agent="agent-10")
    action = adapter.create_issue_from_task("bude404-ops", "GIZMOAI", task, execute=True)
    assert action.status == "WAITING_FOR_APPROVAL"


def test_read_workflow_runs_blocks_without_credentials_when_executing(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    adapter, security, _ = build_adapter(tmp_path)
    security.set_mode(OperatingMode.ASSISTED)
    action = adapter.read_workflow_runs("bude404-ops", "GIZMOAI", branch="main", execute=True)
    assert action.status == "BLOCKED_NO_CREDENTIAL"


def test_adapter_executes_with_token_and_redacts_result(tmp_path: Path, monkeypatch):
    fake = FakeHttp()
    monkeypatch.setenv("GITHUB_TOKEN", "dummy-token-value")
    adapter, security, _ = build_adapter(tmp_path, fake)
    security.set_mode(OperatingMode.ASSISTED)
    task = Task(project="gizmo", objective="Create real issue", assigned_agent="agent-10")
    action = adapter.create_issue_from_task("bude404-ops", "GIZMOAI", task, execute=True)
    assert action.status == "COMPLETED"
    assert fake.calls[0]["method"] == "POST"
    assert fake.calls[0]["headers"]["Authorization"] == "Bearer dummy-token-value"
    assert "dummy-token-value" not in str(action.result)


def test_api_status_counts_actions(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    adapter, security, _ = build_adapter(tmp_path)
    security.set_mode(OperatingMode.ASSISTED)
    task = Task(project="gizmo", objective="Count actions", assigned_agent="agent-10")
    adapter.create_issue_from_task("bude404-ops", "GIZMOAI", task, execute=False)
    adapter.read_workflow_runs("bude404-ops", "GIZMOAI", execute=False)
    status = adapter.export_status()
    assert status["api_actions"] == 2
    assert status["by_status"]["PLANNED_NOT_EXECUTED"] == 2
