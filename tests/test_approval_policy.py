from pathlib import Path

import pytest

from gizmo.core.models import OperatingMode
from gizmo.core.store import JsonStore
from gizmo.monitoring.logger import AuditLogger
from gizmo.security.approval_policy import ApprovalPolicyEngine


def build_engine(tmp_path: Path):
    store = JsonStore(tmp_path)
    audit = AuditLogger(store)
    return ApprovalPolicyEngine(store, audit)


def test_project_modes_default_manual_and_can_be_set(tmp_path: Path):
    engine = build_engine(tmp_path)
    assert engine.project_mode("gizmo") == OperatingMode.MANUAL
    engine.set_project_mode("gizmo", OperatingMode.ASSISTED)
    assert engine.project_mode("gizmo") == OperatingMode.ASSISTED


def test_safe_action_allowed_in_assisted_mode(tmp_path: Path):
    engine = build_engine(tmp_path)
    engine.set_project_mode("gizmo", OperatingMode.ASSISTED)
    decision = engine.evaluate_action("gizmo", "plan", "agent-01")
    assert decision.allowed is True
    assert decision.requires_approval is False


def test_high_risk_action_creates_pending_approval(tmp_path: Path):
    engine = build_engine(tmp_path)
    engine.set_project_mode("gizmo", OperatingMode.ASSISTED)
    decision = engine.evaluate_action("gizmo", "github_write", "agent-10")
    assert decision.allowed is False
    assert decision.requires_approval is True
    assert decision.approval_request_id
    pending = engine.pending("gizmo")
    assert len(pending) == 1
    assert pending[0]["action"] == "github_write"


def test_approval_decision_requires_matching_code(tmp_path: Path):
    engine = build_engine(tmp_path)
    request = engine.request_approval("gizmo", "merge", "agent-10", "Merge protected branch", "high")
    with pytest.raises(ValueError):
        engine.decide(request.id, "wrong-code", True, "bad")
    approved = engine.decide(request.id, request.approval_code, True, "Approved after review")
    assert approved.status == "APPROVED"
    assert engine.pending("gizmo") == []


def test_merge_and_deploy_gates_block_missing_checks(tmp_path: Path):
    engine = build_engine(tmp_path)
    engine.set_project_mode("gizmo", OperatingMode.ASSISTED)
    merge = engine.gate_merge("gizmo", {"tests": True, "secret_scan": False, "review": True})
    deploy = engine.gate_deploy("gizmo", {"tests": True, "secret_scan": True, "security_review": False, "quality_review": True})
    assert merge.allowed is False
    assert "secret_scan" in merge.reason
    assert deploy.allowed is False
    assert "security_review" in deploy.reason


def test_merge_gate_requires_approval_when_checks_pass(tmp_path: Path):
    engine = build_engine(tmp_path)
    engine.set_project_mode("gizmo", OperatingMode.ASSISTED)
    decision = engine.gate_merge("gizmo", {"tests": True, "secret_scan": True, "review": True})
    assert decision.requires_approval is True
    assert engine.pending("gizmo")[0]["action"] == "merge"
