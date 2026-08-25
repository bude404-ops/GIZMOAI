"""Approval and policy engine for GIZMO Phase 3."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from gizmo.core.models import OperatingMode, now_iso
from gizmo.core.store import JsonStore
from gizmo.monitoring.logger import AuditLogger


HIGH_RISK_ACTIONS = {
    "github_write",
    "merge",
    "deploy",
    "external_write",
    "delete_repo",
    "force_push",
    "modify_secrets",
    "change_owner_permissions",
}


@dataclass
class ApprovalRequest:
    id: str
    project: str
    action: str
    requester_agent: str
    summary: str
    risk_level: str
    status: str = "PENDING"
    approval_code: str = field(default_factory=lambda: f"approve-{uuid4().hex[:10]}")
    created_at: str = field(default_factory=now_iso)
    decided_at: str | None = None
    decision_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PolicyDecision:
    allowed: bool
    requires_approval: bool
    reason: str
    approval_request_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ApprovalPolicyEngine:
    """Per-project operating modes, approval records, and action gates."""

    def __init__(self, store: JsonStore, audit: AuditLogger) -> None:
        self.store = store
        self.audit = audit

    def set_project_mode(self, project: str, mode: OperatingMode) -> None:
        self.store.write({"project": project, "mode": mode.value, "updated_at": now_iso()}, "policy", "projects", f"{project}.json")
        self.audit.log("agent-01", None, "policy.project_mode", f"{project} set to {mode.value}")

    def project_mode(self, project: str) -> OperatingMode:
        data = self.store.read("policy", "projects", f"{project}.json", default={"mode": OperatingMode.MANUAL.value})
        return OperatingMode(data["mode"])

    def evaluate_action(self, project: str, action: str, requester_agent: str, production: bool = False) -> PolicyDecision:
        mode = self.project_mode(project)
        if mode == OperatingMode.EMERGENCY:
            req = self.request_approval(project, action, requester_agent, "Emergency mode blocks all autonomous work.", "critical")
            return PolicyDecision(False, True, "Emergency mode active", req.id)
        if production or action in HIGH_RISK_ACTIONS:
            risk = "critical" if production or action in {"delete_repo", "force_push", "modify_secrets", "change_owner_permissions"} else "high"
            req = self.request_approval(project, action, requester_agent, f"{action} requires human approval under GIZMO policy.", risk)
            return PolicyDecision(False, True, f"{action} requires approval", req.id)
        if mode == OperatingMode.MANUAL and action not in {"read", "plan", "test", "memory_write", "status"}:
            req = self.request_approval(project, action, requester_agent, "Manual mode requires approval for non-routine actions.", "medium")
            return PolicyDecision(False, True, "Manual mode requires approval", req.id)
        return PolicyDecision(True, False, "Allowed by project policy")

    def request_approval(self, project: str, action: str, requester_agent: str, summary: str, risk_level: str) -> ApprovalRequest:
        request = ApprovalRequest(
            id=f"approval-{uuid4().hex[:12]}",
            project=project,
            action=action,
            requester_agent=requester_agent,
            summary=summary,
            risk_level=risk_level,
        )
        self.store.write(request.to_dict(), "policy", "approvals", f"{request.id}.json")
        self.audit.log(requester_agent, None, "policy.approval.request", "Approval requested", approval=request.to_dict())
        return request

    def decide(self, request_id: str, approval_code: str, approved: bool, reason: str) -> ApprovalRequest:
        request = self.get_request(request_id)
        if request.status != "PENDING":
            raise ValueError("Approval request already decided")
        if approval_code != request.approval_code:
            raise ValueError("Approval code mismatch")
        request.status = "APPROVED" if approved else "DENIED"
        request.decided_at = now_iso()
        request.decision_reason = reason
        self.store.write(request.to_dict(), "policy", "approvals", f"{request.id}.json")
        self.audit.log("human-owner", None, "policy.approval.decide", request.status, approval=request.to_dict())
        return request

    def get_request(self, request_id: str) -> ApprovalRequest:
        data = self.store.read("policy", "approvals", f"{request_id}.json", default=None)
        if not data:
            raise KeyError(request_id)
        return ApprovalRequest(**data)

    def gate_merge(self, project: str, checks: dict[str, bool], requester_agent: str = "agent-10") -> PolicyDecision:
        required = ["tests", "secret_scan", "review"]
        missing = [name for name in required if not checks.get(name)]
        if missing:
            return PolicyDecision(False, False, f"Merge blocked: missing {', '.join(missing)}")
        return self.evaluate_action(project, "merge", requester_agent)

    def gate_deploy(self, project: str, checks: dict[str, bool], requester_agent: str = "agent-09") -> PolicyDecision:
        required = ["tests", "secret_scan", "security_review", "quality_review"]
        missing = [name for name in required if not checks.get(name)]
        if missing:
            return PolicyDecision(False, False, f"Deploy blocked: missing {', '.join(missing)}")
        return self.evaluate_action(project, "deploy", requester_agent, production=True)

    def pending(self, project: str | None = None) -> list[dict[str, Any]]:
        folder = self.store.path("policy", "approvals")
        if not folder.exists():
            return []
        records = []
        for path in folder.glob("*.json"):
            data = self.store.read("policy", "approvals", path.name)
            if data["status"] == "PENDING" and (project is None or data["project"] == project):
                records.append(data)
        return sorted(records, key=lambda item: item["created_at"])

    def export_status(self) -> dict[str, Any]:
        pending = self.pending()
        return {"pending_approvals": len(pending), "pending": pending}
