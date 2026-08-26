"""GIZMO command line interface."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from gizmo.orchestrator.orchestrator import GizmoOrchestrator
from gizmo.security.security_system import SecuritySystem
from gizmo.core.store import JsonStore
from gizmo.control.telegram_control import TelegramControlLayer
from gizmo.telegram.config import TelegramConfig
from gizmo.telegram.router import TelegramCommandRouter
from gizmo.telegram.security import TelegramAuthorizer


def emit(data: dict) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description="GIZMO — Autonomous Intelligence & Development Organization")
    parser.add_argument("command", choices=["bootstrap", "self-test", "github-demo", "github-api-demo", "policy-demo", "second-brain-demo", "brain-init", "brain-phase2", "brain-phase3", "brain-phase4", "telegram-demo", "status", "stop"])
    parser.add_argument("--workspace", default=str(Path(".gizmo_runtime")))
    parser.add_argument("--comment", default="/gizmo status")
    parser.add_argument("--user-id", default="1")
    parser.add_argument("--chat-id", default="1")
    parser.add_argument("--text", default="/status")
    args = parser.parse_args()
    orchestrator = GizmoOrchestrator(args.workspace)
    if args.command == "bootstrap":
        emit(orchestrator.bootstrap())
    elif args.command == "self-test":
        emit(orchestrator.self_test())
    elif args.command == "github-demo":
        emit(orchestrator.github_workspace_demo(execute_git=False))
    elif args.command == "github-api-demo":
        emit(orchestrator.github_api_demo(execute=False))
    elif args.command == "policy-demo":
        emit(orchestrator.policy_demo())
    elif args.command == "second-brain-demo":
        if args.comment != "/gizmo status":
            emit(orchestrator.second_brain.route(args.comment, actor="cli").to_dict())
        else:
            emit(orchestrator.second_brain_demo())
    elif args.command == "brain-init":
        emit(orchestrator.brain_initialization_demo())
    elif args.command == "brain-phase2":
        emit(orchestrator.brain_phase2_demo())
    elif args.command == "brain-phase3":
        emit(orchestrator.brain_phase3_demo())
    elif args.command == "brain-phase4":
        emit(orchestrator.brain_phase4_demo())
    elif args.command == "telegram-demo":
        config = TelegramConfig.from_env()
        if not config.admin_ids:
            config.admin_ids = {str(args.user_id)}
        control = TelegramControlLayer(orchestrator, config=config)
        router = TelegramCommandRouter(orchestrator.store, TelegramAuthorizer(config.admin_ids), control)
        emit(router.route_text(args.user_id, args.chat_id, args.text).to_dict())
    elif args.command == "status":
        emit(orchestrator.status())
    elif args.command == "stop":
        SecuritySystem(JsonStore(args.workspace)).emergency_stop()
        emit({"mode": "EMERGENCY", "stopped": True})


if __name__ == "__main__":
    main()
