"""Approval-gated GitHub API adapter.

The adapter supports real GitHub REST calls when explicitly enabled, but it is
safe by default: write operations return auditable pending-approval plans unless
policy and credentials allow execution.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol
from uuid import uuid4

from gizmo.core.models import Task, now_iso
from gizmo.core.store import JsonStore
from gizmo.monitoring.logger import AuditLogger
from gizmo.security.security_system import SecuritySystem


class HttpClient(Protocol):
    def request(self, method: str, url: str, headers: dict[str, str], body: dict[str, Any] | None = None) -> dict[str, Any]: ...


class UrllibGitHubHttpClient:
    def request(self, method: str, url: str, headers: dict[str, str], body: dict[str, Any] | None = None) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                raw = response.read().decode("utf-8")
                parsed = json.loads(raw) if raw else {}
                return {"ok": True, "status": response.status, "data": parsed}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="ignore")
            return {"ok": False, "status": exc.code, "error": raw}
        except urllib.error.URLError as exc:
            return {"ok": False, "status": 0, "error": str(exc)}


@dataclass
class GitHubApiAction:
    id: str
    action_type: str
    owner: str
    repo: str
    payload: dict[str, Any]
    status: str
    result: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GitHubApiAdapter:
    def __init__(
        self,
        store: JsonStore,
        security: SecuritySystem,
        audit: AuditLogger,
        http: HttpClient | None = None,
        token_env: str = "GITHUB_TOKEN",
        api_base: str = "https://api.github.com",
    ) -> None:
        self.store = store
        self.security = security
        self.audit = audit
        self.http = http or UrllibGitHubHttpClient()
        self.token_env = token_env
        self.api_base = api_base.rstrip("/")

    def credential_status(self) -> dict[str, Any]:
        token = os.environ.get(self.token_env, "")
        return {"env": self.token_env, "available": bool(token), "source": "environment" if token else "missing"}

    def create_issue_from_task(self, owner: str, repo: str, task: Task, labels: list[str] | None = None, execute: bool = False) -> GitHubApiAction:
        payload = {
            "title": f"GIZMO task: {task.objective[:80]}",
            "body": self._issue_body(task),
            "labels": labels or ["gizmo", "task", task.assigned_agent],
        }
        return self._maybe_execute("create_issue", owner, repo, payload, execute, "POST", f"/repos/{owner}/{repo}/issues")

    def open_pull_request_from_plan(self, owner: str, repo: str, pr_plan: dict[str, Any], execute: bool = False) -> GitHubApiAction:
        payload = {
            "title": pr_plan["title"],
            "head": pr_plan["branch"],
            "base": pr_plan["base_branch"],
            "body": pr_plan["body"],
            "maintainer_can_modify": True,
        }
        return self._maybe_execute("open_pull_request", owner, repo, payload, execute, "POST", f"/repos/{owner}/{repo}/pulls")

    def read_workflow_runs(self, owner: str, repo: str, branch: str | None = None, execute: bool = True) -> GitHubApiAction:
        path = f"/repos/{owner}/{repo}/actions/runs"
        if branch:
            path += f"?branch={branch}"
        return self._maybe_execute("read_workflow_runs", owner, repo, {"branch": branch}, execute, "GET", path, read_only=True)

    def sync_issue_status(self, owner: str, repo: str, issue_number: int, status_note: str, execute: bool = False) -> GitHubApiAction:
        payload = {"body": f"GIZMO status update: {status_note}"}
        return self._maybe_execute("sync_issue_status", owner, repo, payload, execute, "POST", f"/repos/{owner}/{repo}/issues/{issue_number}/comments")

    def _maybe_execute(
        self,
        action_type: str,
        owner: str,
        repo: str,
        payload: dict[str, Any],
        execute: bool,
        method: str,
        path: str,
        read_only: bool = False,
    ) -> GitHubApiAction:
        action = GitHubApiAction(
            id=f"github-api-{uuid4().hex[:12]}",
            action_type=action_type,
            owner=owner,
            repo=repo,
            payload=payload,
            status="PLANNED",
        )
        needs_approval = (not read_only) and self.security.require_approval("github_write")
        credentials = self.credential_status()
        if not execute:
            action.status = "PLANNED_NOT_EXECUTED"
            action.result = {"reason": "execute=false", "credentials": credentials}
        elif needs_approval:
            action.status = "WAITING_FOR_APPROVAL"
            action.result = {"reason": "policy requires approval", "credentials": credentials}
        elif not credentials["available"]:
            action.status = "BLOCKED_NO_CREDENTIAL"
            action.result = {"reason": f"missing {self.token_env}", "credentials": credentials}
        else:
            action.status = "EXECUTING"
            token = os.environ[self.token_env]
            headers = {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "GIZMO-Autonomous-Organization",
            }
            result = self.http.request(method, f"{self.api_base}{path}", headers, None if method == "GET" else payload)
            action.status = "COMPLETED" if result.get("ok") else "FAILED"
            action.result = self._redact_result(result)
        self.store.write(action.to_dict(), "github", "api_actions", f"{action.id}.json")
        self.audit.log("agent-10", None, f"github.api.{action_type}", action.status, api_action=action.to_dict())
        return action

    def _issue_body(self, task: Task) -> str:
        return (
            f"## Objective\n{task.objective}\n\n"
            f"## Assigned agent\n{task.assigned_agent}\n\n"
            f"## Priority\n{task.priority}\n\n"
            f"## Dependencies\n{', '.join(task.dependencies) if task.dependencies else 'None'}\n\n"
            "## Safety\nGenerated by GIZMO. Destructive or production actions require human approval."
        )

    def _redact_result(self, result: dict[str, Any]) -> dict[str, Any]:
        text = json.dumps(result)
        token = os.environ.get(self.token_env)
        if token:
            text = text.replace(token, "[REDACTED]")
        return json.loads(text)

    def export_status(self) -> dict[str, Any]:
        folder = self.store.path("github", "api_actions")
        actions = [json.loads(path.read_text()) for path in folder.glob("*.json")] if folder.exists() else []
        by_status: dict[str, int] = {}
        for action in actions:
            by_status[action["status"]] = by_status.get(action["status"], 0) + 1
        return {"api_actions": len(actions), "by_status": by_status, "credentials": self.credential_status()}
