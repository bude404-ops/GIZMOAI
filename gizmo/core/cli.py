"""GIZMO command line interface."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from gizmo.brain.cloud_vault import CloudMemoryVault
from gizmo.orchestrator.orchestrator import GizmoOrchestrator
from gizmo.security.security_system import SecuritySystem
from gizmo.core.store import JsonStore
from gizmo.control.telegram_control import TelegramControlLayer
from gizmo.control.autonomous_learning import TelegramAutonomousKnowledgeRunner
from gizmo.control.cloud_brain import CloudAutonomousBrainRunner
from gizmo.apps.factory import KnowledgeAppFactory
from gizmo.apps.prototyper import SafeMiniAppPrototyper
from gizmo.ideas.autonomous_thinker import AutonomousThinker
from gizmo.knowledge.universal_sources import KnowledgeSource, UniversalKnowledgeIngestor
from gizmo.telegram.bot import TelegramBotRuntime
from gizmo.telegram.config import TelegramConfig
from gizmo.telegram.router import TelegramCommandRouter
from gizmo.telegram.security import TelegramAuthorizer


def emit(data: dict) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description="GIZMO — Autonomous Intelligence & Development Organization")
    parser.add_argument("command", choices=["bootstrap", "self-test", "github-demo", "github-api-demo", "policy-demo", "second-brain-demo", "brain-init", "brain-phase2", "brain-phase3", "brain-phase4", "telegram-demo", "telegram-autonomous-cycle", "telegram-poll-once", "telegram-poll-loop", "cloud-brain-cycle", "super-brain-cycle", "universal-route", "universal-execute", "universal-run", "universal-recover", "universal-cancel", "universal-health", "universal-approve", "universal-acceptance", "universal-learn", "app-factory-cycle", "autonomous-think", "prototype-cycle", "cloud-vault-sync", "status", "stop"])
    parser.add_argument("--workspace", default=str(Path(".gizmo_runtime")))
    parser.add_argument("--comment", default="/gizmo status")
    parser.add_argument("--user-id", default="1")
    parser.add_argument("--chat-id", default="1")
    parser.add_argument("--text", default="/status")
    parser.add_argument("--duration-seconds", type=int, default=3300)
    parser.add_argument("--poll-timeout", type=int, default=25)
    parser.add_argument("--max-idle-cycles", type=int, default=0)
    parser.add_argument("--domain", default="general")
    parser.add_argument("--source-kind", default="text")
    parser.add_argument("--execution-id", default=None)
    parser.add_argument("--approval-id", default=None)
    parser.add_argument("--approval-code", default=None)
    parser.add_argument("--run-after-approval", action="store_true")
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument("--stale-after-minutes", type=int, default=60)
    parser.add_argument("--reason", default="operator cancelled")
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
    elif args.command == "telegram-autonomous-cycle":
        config = TelegramConfig.from_env()
        control = TelegramControlLayer(orchestrator, config=config)
        if args.text.lower() in {"enable", "on", "true"}:
            control.autonomous_learning.enable(chat_id=args.chat_id, source="cli")
        cycle = control.autonomous_learning.run_cycle(chat_id=args.chat_id)
        emit(cycle.to_dict())
    elif args.command in {"cloud-brain-cycle", "super-brain-cycle"}:
        config = TelegramConfig.from_env()
        control = TelegramControlLayer(orchestrator, config=config)
        runner = CloudAutonomousBrainRunner(orchestrator, notifier=control.notifier)
        if args.text.lower() in {"enable", "on", "true"}:
            runner.enable(chat_id=args.chat_id, source="cli")
        cycle = runner.run_cycle(chat_id=args.chat_id)
        emit(cycle.to_dict())
    elif args.command == "universal-route":
        emit(orchestrator.universal_route(args.text, project=args.domain or "Gizmo", execute=False))
    elif args.command == "universal-execute":
        emit(orchestrator.universal_route(args.text, project=args.domain or "Gizmo", execute=True))
    elif args.command == "universal-run":
        emit(orchestrator.run_universal_execution(args.execution_id, max_steps=args.max_steps))
    elif args.command == "universal-recover":
        emit(orchestrator.recover_universal_execution(args.execution_id, max_tasks=args.max_steps))
    elif args.command == "universal-cancel":
        emit(orchestrator.cancel_universal_execution(args.execution_id, reason=args.reason))
    elif args.command == "universal-health":
        emit(orchestrator.universal_health_report(stale_after_minutes=args.stale_after_minutes))
    elif args.command == "universal-approve":
        if not args.approval_id or not args.approval_code:
            emit({"ready": False, "status": "MISSING_APPROVAL", "message": "Provide --approval-id and --approval-code."})
        else:
            emit(orchestrator.approve_universal_execution(args.approval_id, args.approval_code, run=args.run_after_approval))
    elif args.command == "universal-acceptance":
        emit(orchestrator.universal_acceptance_demo())
    elif args.command == "universal-learn":
        source = None
        if args.text and args.text != "/status":
            source = [KnowledgeSource(kind=args.source_kind, locator=args.text, title=f"Operator source: {args.domain}", domain=args.domain, trust=0.72)]
        report = UniversalKnowledgeIngestor(orchestrator.brain_core, orchestrator.store).ingest(source, domain=args.domain)
        emit(report.to_dict())
    elif args.command == "app-factory-cycle":
        report = KnowledgeAppFactory(orchestrator.brain_core, orchestrator.store).run(domain=args.domain)
        emit(report.to_dict())
    elif args.command == "autonomous-think":
        topics = [part.strip() for part in (args.text or "").split(",") if part.strip() and part.strip() != "/status"]
        report = AutonomousThinker(orchestrator.brain_core, orchestrator.store).think(cycle_id="cli", topics=topics)
        emit(report.to_dict())
    elif args.command == "prototype-cycle":
        report = SafeMiniAppPrototyper(orchestrator.brain_core, orchestrator.store).run(limit=3, allow_publish=False)
        emit(report.to_dict())
    elif args.command == "cloud-vault-sync":
        report = CloudMemoryVault(orchestrator.brain_core, orchestrator.store).sync()
        emit(report.to_dict())
    elif args.command == "telegram-poll-once":
        config = TelegramConfig.from_env()
        control = TelegramControlLayer(orchestrator, config=config)
        router = TelegramCommandRouter(orchestrator.store, TelegramAuthorizer(config.admin_ids), control)
        runtime = TelegramBotRuntime(config, router, control.notifier)
        emit(runtime.poll_once(send_replies=True, acknowledge=True, timeout=args.poll_timeout))
    elif args.command == "telegram-poll-loop":
        config = TelegramConfig.from_env()
        control = TelegramControlLayer(orchestrator, config=config)
        router = TelegramCommandRouter(orchestrator.store, TelegramAuthorizer(config.admin_ids), control)
        runtime = TelegramBotRuntime(config, router, control.notifier)
        max_idle = args.max_idle_cycles if args.max_idle_cycles > 0 else None
        emit(runtime.poll_loop(duration_seconds=args.duration_seconds, timeout=args.poll_timeout, send_replies=True, acknowledge=True, max_idle_cycles=max_idle))
    elif args.command == "status":
        emit(orchestrator.status())
    elif args.command == "stop":
        SecuritySystem(JsonStore(args.workspace)).emergency_stop()
        emit({"mode": "EMERGENCY", "stopped": True})


if __name__ == "__main__":
    main()
