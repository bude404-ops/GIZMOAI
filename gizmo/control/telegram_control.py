"""Telegram control layer that delegates to the existing Gizmo orchestrator."""
from __future__ import annotations

from typing import Any

from gizmo.agents.core_agents import CORE_AGENTS, core_agent_map
from gizmo.agents.registry import AgentRegistry
from gizmo.apps.factory import KnowledgeAppFactory
from gizmo.apps.prototyper import SafeMiniAppPrototyper
from gizmo.brain.cloud_vault import CloudMemoryVault
from gizmo.brain.models import BrainMemoryType
from gizmo.control.autonomous_learning import TelegramAutonomousKnowledgeRunner
from gizmo.control.cloud_brain import CloudAutonomousBrainRunner
from gizmo.ideas.autonomous_thinker import AutonomousThinker
from gizmo.knowledge.universal_sources import KnowledgeSource, UniversalKnowledgeIngestor
from gizmo.core.models import OperatingMode, Task, TaskStatus, now_iso
from gizmo.github.api_adapter import GitHubApiAdapter
from gizmo.telegram.config import TelegramConfig
from gizmo.telegram.intents import TelegramIntent
from gizmo.telegram.notifier import TelegramNotifier
from gizmo.telegram.important_events import ImportantTelegramEventReporter
from gizmo.telegram.alert_preferences import TelegramAlertPreferenceStore
from gizmo.telegram.router import TelegramTaskEnvelope


class TelegramControlLayer:
    def __init__(self, orchestrator: Any, config: TelegramConfig | None = None, notifier: TelegramNotifier | None = None) -> None:
        self.orchestrator = orchestrator
        self.config = config or TelegramConfig.from_env()
        self.notifier = notifier or TelegramNotifier(orchestrator.store, self.config.bot_token, self.config.notification_min_priority)
        self.github = GitHubApiAdapter(orchestrator.store, orchestrator.security, orchestrator.audit)
        self.registry = AgentRegistry(orchestrator.store, getattr(orchestrator, "agent_brain", None))
        self.autonomous_learning = TelegramAutonomousKnowledgeRunner(orchestrator, self.notifier)
        self.cloud_brain = CloudAutonomousBrainRunner(orchestrator, self.notifier)
        self.universal_ingestor = UniversalKnowledgeIngestor(orchestrator.brain_core, orchestrator.store)
        self.app_factory = KnowledgeAppFactory(orchestrator.brain_core, orchestrator.store)
        self.thinker = AutonomousThinker(orchestrator.brain_core, orchestrator.store)
        self.prototyper = SafeMiniAppPrototyper(orchestrator.brain_core, orchestrator.store)
        self.cloud_vault = CloudMemoryVault(orchestrator.brain_core, orchestrator.store)
        self.important_events = ImportantTelegramEventReporter(orchestrator.store, self.notifier)
        self.alert_preferences = TelegramAlertPreferenceStore(orchestrator.store)

    def handle_telegram_task(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        handlers = {
            "start": self._start,
            "help": self._help,
            "status": self._status,
            "agents": self._agents,
            "projects": self._projects,
            "tasks": self._tasks,
            "task_detail": self._task_detail,
            "run": self._run,
            "emergency_stop": self._stop,
            "pause": self._pause,
            "resume": self._resume,
            "autonomous": self._autonomous,
            "learn": self._learn,
            "cloud_brain": self._cloud_brain,
            "universal_learn": self._universal_learn,
            "app_factory": self._app_factory,
            "autonomous_think": self._autonomous_think,
            "prototype": self._prototype,
            "cloud_vault": self._cloud_vault,
            "important_events": self._important_events,
            "alert_preferences": self._alert_preferences,
            "memory": self._memory,
            "remember": self._remember,
            "logs": self._logs,
            "build": self._build,
            "universal_task": self._universal_task,
            "test": self._test,
            "deploy": self._deploy,
            "approve": self._approve,
            "deny": self._deny,
            "restart": self._restart,
            "natural_task": self._universal_task,
        }
        result = handlers.get(intent.intent, self._universal_task)(envelope, intent)
        self.orchestrator.store.write({**envelope.to_dict(), "status": result.get("task_status", envelope.status), "result": result}, "telegram", "task_results", f"{envelope.task_id}.json")
        if result.get("notify", True):
            self.notifier.queue(envelope.chat_id, result.get("message", "Command accepted."), result.get("priority", "NORMAL"), result.get("inline_buttons", []))
        return result

    def _start(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        return {"ok": True, "message": "🧠 GIZMO ONLINE\nTelegram Control Center is ready. Use /help or tell me what to build.", "task_status": "COMPLETED"}

    def _help(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        commands = "/status /agents /projects /tasks /task /run /pause /resume /stop /autonomous /learn /memory /remember /logs /build /test /deploy /approve /deny /restart /important /alerts"
        return {"ok": True, "message": f"🧠 Commands\n{commands}\n\nNatural language works too: Build a new research agent that learns from previous research.", "task_status": "COMPLETED"}

    def _status(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        status = self.orchestrator.status()
        registry = self.registry.export_status()
        tasks = self._list_tasks()
        current = next((task for task in tasks if task.get("status") in {"RUNNING", "PLANNING", "TESTING", "REVIEW"}), None)
        latest_cycle = self.autonomous_learning.latest_cycle() or {}
        latest_cloud = self.cloud_brain.latest_cycle() or {}
        factory = self.app_factory.latest()
        thinking = self.thinker.latest()
        prototypes = self.prototyper.latest()
        vault = self.cloud_vault.latest()
        message = (
            "🧠 GIZMO STATUS\n"
            "System: 🟢 ONLINE\n"
            "Reaper: 🟢 ACTIVE\n"
            f"Agents: {registry['counts']['total']} registered / {registry['counts']['running']} active\n"
            f"Current Task: {current['objective'][:90] if current else 'None active'}\n"
            f"Tasks: {len(tasks)} tracked\n"
            f"Approvals: {status.get('policy', {}).get('pending_approvals', 0)} pending\n"
            f"Autonomous Mode: {'🟢 ENABLED' if self._autonomous_state().get('enabled') else '⚪ DISABLED'}\n"
            f"Knowledge Cycle: {latest_cycle.get('status', 'not run')}\n"
            f"Cloud Brain: {latest_cloud.get('status', 'not run')}\n"
            f"Super Brain: reasoning {len(latest_cloud.get('reasoning', []))} / indexed {latest_cloud.get('semantic_index', {}).get('indexed_memories', 0)} / body actions {latest_cloud.get('body_scorecard', {}).get('actions', 0)}\n"
            f"Universal Knowledge: sources {latest_cloud.get('universal_knowledge', {}).get('sources_seen', 0)} / app backlog {factory.get('backlog_size', 0)}\n"
            f"Autonomous Thinking: ideas {len(thinking.get('ideas', []))} / upgrades {len(thinking.get('upgrades', []))}\n"
            f"Prototype Queue: drafts {len(prototypes.get('prototypes_created', []))} / review {prototypes.get('review_queue_size', 0)}\n"
            f"Cloud Vault: notes {vault.get('markdown_notes', 0)} / restore-ready {vault.get('restore_ready', False)}"
        )
        return {"ok": True, "message": message, "task_status": "COMPLETED", "actions": [{"type": "status", "data": status}]}

    def _agents(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        rows = []
        for record in self.registry.list_agents():
            rows.append(f"🟢 {record.name} — {record.status} / {record.health} / {record.profile.get('memory_contributions', 0)} memories")
        return {"ok": True, "message": "🤖 AGENTS\n" + "\n".join(rows[:27]), "task_status": "COMPLETED"}

    def _projects(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        projects = sorted({task.get("project", "Gizmo") for task in self._list_tasks()} | {"Gizmo"})
        return {"ok": True, "message": "📁 PROJECTS\n" + "\n".join(f"• {p}" for p in projects), "task_status": "COMPLETED"}

    def _tasks(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        tasks = self._list_tasks()[-10:]
        if not tasks:
            return {"ok": True, "message": "📋 TASKS\nNo tasks yet.", "task_status": "COMPLETED"}
        lines = [f"• {t['id']}: {t['status']} — {t['objective'][:70]}" for t in tasks]
        return {"ok": True, "message": "📋 TASKS\n" + "\n".join(lines), "task_status": "COMPLETED"}

    def _task_detail(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        task_id = intent.objective.strip()
        try:
            task = self.orchestrator.tasks.load(task_id)
            return {"ok": True, "message": f"📌 {task.id}\nStatus: {task.status.value}\nAgent: {task.assigned_agent}\nObjective: {task.objective}\nResult: {task.result or 'Pending'}", "task_status": "COMPLETED"}
        except Exception:
            return {"ok": False, "message": "Task not found.", "task_status": "FAILED", "priority": "FAILURE"}

    def _run(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        objective = intent.objective if intent.objective != "Run queued task" else "Run requested Telegram task"
        task = self._create_gizmo_task(objective, self._select_agent(objective))
        executed = self.orchestrator._execute_allowed_task(task)
        return {"ok": executed.status == TaskStatus.COMPLETED, "message": f"▶️ RUN COMPLETE\nTask: {executed.id}\nAgent: {executed.assigned_agent}\nStatus: {executed.status.value}", "task_status": executed.status.value}

    def _stop(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        self.orchestrator.security.set_mode(OperatingMode.EMERGENCY)
        self._set_autonomous(False, paused=True, emergency=True)
        return {"ok": True, "message": "🛑 EMERGENCY STOP ACTIVE\nNew autonomous work is halted. Approval is required before resuming.", "task_status": "COMPLETED", "priority": "URGENT"}

    def _pause(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        self._set_autonomous(False, paused=True, emergency=False)
        return {"ok": True, "message": "⏸️ GIZMO PAUSED\nNew autonomous tasks are blocked. Approved active work may finish.", "task_status": "COMPLETED", "priority": "IMPORTANT"}

    def _resume(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        self._set_autonomous(self._autonomous_state().get("enabled", False), paused=False, emergency=False)
        self.orchestrator.security.set_mode(OperatingMode.MANUAL)
        return {"ok": True, "message": "▶️ GIZMO RESUMED\nManual control is active. Autonomous mode remains permission-bound.", "task_status": "COMPLETED"}

    def _autonomous(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        arg = intent.args.get("raw_args", "").lower().strip()
        if arg in {"on", "enable", "enabled"}:
            req = self.orchestrator.policy.request_approval("Gizmo", "autonomous_enable", "human-owner", "Enable permission-bound autonomous mode from Telegram.", "high")
            return self._approval_message(req, "Autonomous mode enable requires approval.")
        if arg in {"off", "disable", "disabled"}:
            self._set_autonomous(False, paused=False, emergency=False)
            return {"ok": True, "message": "⚪ Autonomous mode disabled.", "task_status": "COMPLETED"}
        state = self._autonomous_state()
        return {"ok": True, "message": f"Autonomous Mode: {'ON' if state.get('enabled') else 'OFF'}\nPaused: {state.get('paused', False)}\nEmergency: {state.get('emergency', False)}", "task_status": "COMPLETED"}

    def _learn(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        objective = intent.objective or "Run Telegram autonomous learning cycle"
        if "cycle" in objective.lower() or "autonomous" in objective.lower() or objective.lower().strip() in {"", "now", "run"}:
            cycle = self.autonomous_learning.run_cycle(chat_id=envelope.chat_id)
            return {"ok": cycle.status == "COMPLETED", "message": cycle.notification, "task_status": cycle.status, "priority": "IMPORTANT", "actions": [{"type": "autonomous_learning_cycle", "data": cycle.to_dict()}]}
        task = self._create_gizmo_task(objective, "agent-26")
        task.lessons_learned.append("Telegram learning request should become central Brain context.")
        executed = self.orchestrator._execute_allowed_task(task)
        memory = self.orchestrator.brain_core.record_lesson("Telegram learning request", objective, source="telegram-control", source_agent="agent-26", project="Gizmo", tags=["telegram", "learning"])
        return {"ok": True, "message": f"🧠 LEARNING CYCLE RECORDED\nTask: {executed.id}\nMemory: {memory.id}", "task_status": "COMPLETED"}

    def _cloud_brain(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        objective = (intent.objective or "run").lower().strip()
        if any(word in objective for word in ["on", "enable", "start", "smarter", "work", "run", "agents", "cloud"]):
            self.cloud_brain.enable(chat_id=envelope.chat_id, source="telegram")
            cycle = self.cloud_brain.run_cycle(chat_id=envelope.chat_id)
            return {"ok": cycle.status == "COMPLETED", "message": cycle.notification, "task_status": cycle.status, "priority": "IMPORTANT", "actions": [{"type": "cloud_brain_cycle", "data": cycle.to_dict()}]}
        latest = self.cloud_brain.latest_cycle() or {}
        state = self.cloud_brain.state()
        return {"ok": True, "message": f"☁️ CLOUD BRAIN\nEnabled: {state.get('enabled', False)}\nLatest: {latest.get('status', 'not run')}\nAgents: {len(latest.get('agents', []))}", "task_status": "COMPLETED"}

    def _universal_learn(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        domain = intent.args.get("domain") or intent.objective or "general"
        text = intent.args.get("raw_args") or intent.objective or domain
        source = None
        if text and text.lower().strip() not in {"general", "learn anything", "learn from all sources"}:
            source = [KnowledgeSource(kind="text", locator=text, title=f"Telegram learning source: {domain}", domain=domain, trust=0.72)]
        report = self.universal_ingestor.ingest(source, domain=domain, limit=8)
        return {
            "ok": True,
            "message": f"🌐 UNIVERSAL LEARNING COMPLETE\nDomain: {domain}\nSources: {report.sources_seen}\nMemories: {len(report.memories_created)}\nApp opportunities: {len(report.app_opportunities)}",
            "task_status": "COMPLETED",
            "priority": "IMPORTANT",
            "actions": [{"type": "universal_learning", "data": report.to_dict()}],
        }

    def _app_factory(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        domain = intent.args.get("domain") or intent.objective or "general"
        report = self.app_factory.run(domain=domain)
        titles = [item.get("title", "Untitled") for item in report.top_blueprints[:3]]
        return {
            "ok": True,
            "message": f"🧩 APP FACTORY COMPLETE\nDomain: {domain}\nBlueprints: {len(report.blueprints_created)}\nBacklog: {report.backlog_size}\nTop: " + ("; ".join(titles) if titles else "None yet"),
            "task_status": "COMPLETED",
            "priority": "IMPORTANT",
            "actions": [{"type": "app_factory", "data": report.to_dict()}],
        }

    def _autonomous_think(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        raw = intent.args.get("raw_args") or intent.objective or "self improvement, app ideas, upgrades"
        topics = [part.strip() for part in raw.replace(" and ", ",").split(",") if part.strip()]
        report = self.thinker.think(cycle_id=f"telegram-{envelope.task_id}", topics=topics)
        top = [item.get("title", "Untitled") for item in report.chosen_next[:3]]
        return {
            "ok": True,
            "message": f"🧠 AUTONOMOUS THINKING COMPLETE\nIdeas: {len(report.ideas)}\nUpgrade proposals: {len(report.upgrades)}\nChosen next: " + ("; ".join(top) if top else "None yet"),
            "task_status": "COMPLETED",
            "priority": "IMPORTANT",
            "actions": [{"type": "autonomous_thinking", "data": report.to_dict()}],
        }

    def _prototype(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        report = self.prototyper.run(limit=3, allow_publish=False)
        titles = [item.get("title", "Untitled") for item in report.top_prototypes[:3]]
        return {
            "ok": True,
            "message": f"🛠️ PROTOTYPES READY FOR REVIEW\nDrafts: {len(report.prototypes_created)}\nReview queue: {report.review_queue_size}\nTop: " + ("; ".join(titles) if titles else "None yet") + "\nPublishing remains approval-gated.",
            "task_status": "COMPLETED",
            "priority": "IMPORTANT",
            "actions": [{"type": "prototype", "data": report.to_dict()}],
        }

    def _cloud_vault(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        report = self.cloud_vault.sync()
        return {
            "ok": True,
            "message": f"🗂️ CLOUD MEMORY VAULT SYNCED\nMarkdown notes: {report.markdown_notes}\nGraph files: {report.graph_files}\nArchive bytes: {report.archive_bytes}\nRestore-ready: {report.restore_ready}",
            "task_status": "COMPLETED",
            "priority": "IMPORTANT",
            "actions": [{"type": "cloud_vault", "data": report.to_dict()}],
        }



    def _alert_preferences(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        raw = intent.args.get("raw_args") or intent.objective or "show"
        prefs, changes = self.alert_preferences.update_from_text(raw)
        status = "ON" if prefs.enabled else "OFF"
        quiet = f"ON {prefs.quiet_hours_start}:00-{prefs.quiet_hours_end}:00" if prefs.quiet_hours_enabled else "OFF"
        message = (
            "🔔 TELEGRAM ALERTS\n"
            f"Status: {status}\n"
            f"Minimum priority: {prefs.min_priority}\n"
            f"Categories: {', '.join(prefs.categories)}\n"
            f"Quiet hours: {quiet}\n"
            f"Quiet allow: {', '.join(prefs.quiet_hours_allow)}"
        )
        if changes:
            message += "\nUpdated: " + "; ".join(changes)
        message += "\nUse /alerts on|off, /alerts min URGENT, /alerts only approval campaign, /alerts quiet 23-7, or /alerts reset."
        return {"ok": True, "message": message, "task_status": "COMPLETED", "priority": "IMPORTANT", "actions": [{"type": "alert_preferences", "data": prefs.to_dict()}]}

    def _important_events(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        raw = (intent.args.get("raw_args") or intent.objective or "").lower()
        force = "force" in raw or "again" in raw
        execute = "send" in raw or "now" in raw or "force" in raw
        report = self.important_events.report(chat_id=envelope.chat_id, execute=execute, force=force)
        if not report.events:
            message = "⚪ IMPORTANT EVENTS\nNo high-signal autonomous events are waiting."
        else:
            lines = [f"• {item['priority']}: {item['title']}" for item in report.events[:6]]
            message = "⚠️ IMPORTANT EVENTS\n" + "\n".join(lines) + f"\nQueued: {len(report.queued)} / Skipped: {len(report.skipped)}"
        return {"ok": True, "message": message, "task_status": "COMPLETED", "priority": "IMPORTANT" if report.events else "NORMAL", "actions": [{"type": "important_events", "data": report.to_dict()}]}

    def _memory(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        query = intent.args.get("query") or intent.objective or "Gizmo"
        memories = self.orchestrator.brain_core.hybrid_search(query, project="Gizmo", limit=5)
        if not memories:
            return {"ok": True, "message": "🧠 MEMORY\nNo strong match yet.", "task_status": "COMPLETED"}
        lines = [f"• {m.type.value}: {m.title}" for m in memories]
        return {"ok": True, "message": "🧠 MEMORY\n" + "\n".join(lines), "task_status": "COMPLETED"}

    def _remember(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        text = intent.objective.strip()
        if any(secret in text.lower() for secret in ["token", "secret", "password", "private key", "api key"]):
            return {"ok": False, "message": "I will not store secrets in memory.", "task_status": "FAILED", "priority": "SECURITY"}
        memory = self.orchestrator.brain_core.remember(BrainMemoryType.PREFERENCE, "Telegram memory", text, source="telegram", source_agent="human-owner", project="Gizmo", tags=["telegram", "explicit-memory"])
        return {"ok": True, "message": f"🧠 Remembered.\nMemory: {memory.id}", "task_status": "COMPLETED"}

    def _logs(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        logs = self.orchestrator.store.read("monitoring", "audit_log.json", default=[])[-8:]
        if not logs:
            return {"ok": True, "message": "📜 LOGS\nNo audit entries yet.", "task_status": "COMPLETED"}
        lines = [f"• {log.get('action')} — {log.get('result')}" for log in logs]
        return {"ok": True, "message": "📜 LOGS\n" + "\n".join(lines), "task_status": "COMPLETED"}

    def _build(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        objective = intent.objective
        agent_id = self._select_agent(objective)
        task = self._create_gizmo_task(objective, agent_id)
        owner, repo = self._repo_parts()
        workflow = self.github.dispatch_workflow(owner, repo, "agent-runner.yml", {"task_id": task.id, "agent": agent_id, "objective": objective, "priority": intent.priority, "autonomous": "false", "project": task.project}, execute=False)
        return {"ok": True, "message": f"🧱 TASK QUEUED\nTask: {task.id}\nAgent: {agent_id}\nGitHub dispatch: {workflow.status}", "task_status": "QUEUED", "actions": [workflow.to_dict()]}

    def _universal_task(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        objective = intent.objective or intent.args.get("raw_args") or "General Creator request"
        result = self.orchestrator.universal_route(objective, project="Gizmo", execute=True)
        plan = result["plan"]
        execution = result.get("execution") or {}
        cap_names = [cap["name"] for cap in plan["capabilities"][:4]]
        agents = plan["selected_agents"][:6]
        task_count = len(execution.get("task_ids", []))
        message = (
            "🧭 UNIVERSAL ROUTE QUEUED\n"
            f"Intent: {plan['classification']['category']}\n"
            f"Effort: {plan['classification']['effort']}\n"
            f"Capabilities: {', '.join(cap_names)}\n"
            f"Agents: {', '.join(agents)}\n"
            f"Approval: {'required' if plan['approval_required'] else plan['permission_mode']}\n"
            f"Steps: {len(plan['decomposition'])}\n"
            f"Tasks: {task_count}\n"
            f"Execution: {execution.get('execution_id', 'planned')}\n"
            f"Verify: {plan['verification_plan'][0]}"
        )
        status = "HUMAN_REVIEW" if plan["approval_required"] else (execution.get("status") or "QUEUED")
        return {"ok": True, "message": message, "task_status": status, "priority": "IMPORTANT", "actions": [{"type": "universal_route", "data": result}]}

    def _test(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        task = self._create_gizmo_task(intent.objective or "Run tests", "agent-11")
        owner, repo = self._repo_parts()
        workflow = self.github.dispatch_workflow(owner, repo, "testing-agent.yml", {"task_id": task.id, "agent": "agent-11", "objective": task.objective, "priority": "normal", "autonomous": "false", "project": "Gizmo"}, execute=False)
        return {"ok": True, "message": f"🧪 TEST TASK QUEUED\nTask: {task.id}\nWorkflow: {workflow.status}", "task_status": "QUEUED", "actions": [workflow.to_dict()]}

    def _deploy(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        req = self.orchestrator.policy.request_approval("Gizmo", "deploy", "agent-09", f"Deploy requested from Telegram: {intent.objective}", "critical")
        return self._approval_message(req, "Deploy requires approval.")

    def _approve(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        parts = intent.objective.split()
        if len(parts) < 2:
            return {"ok": False, "message": "Use /approve <approval_id> <approval_code>", "task_status": "FAILED", "priority": "FAILURE"}
        try:
            decided = self.orchestrator.policy.decide(parts[0], parts[1], True, "Approved from Telegram")
            if decided.action == "autonomous_enable":
                self.autonomous_learning.enable(chat_id=envelope.chat_id, source="telegram-approval")
            universal_record = self.orchestrator.universal_execution.find_by_approval(decided.id)
            if universal_record is not None and decided.action == "universal_execute":
                released = self.orchestrator.universal_execution.release_after_approval(universal_record.execution_id, approval=decided, task_creator=self.orchestrator._create_universal_task_from_step)
                return {
                    "ok": True,
                    "message": f"✅ UNIVERSAL EXECUTION APPROVED\nApproval: {decided.id}\nExecution: {released.execution_id}\nTasks released: {len(released.task_ids)}\nStatus: {released.status}",
                    "task_status": released.status,
                    "priority": "IMPORTANT",
                    "actions": [{"type": "universal_approval_release", "data": released.to_dict()}],
                }
            return {"ok": True, "message": f"✅ APPROVED\n{decided.id}\nAction: {decided.action}", "task_status": "COMPLETED", "priority": "IMPORTANT"}
        except Exception:
            return {"ok": False, "message": "Approval failed. Verify the approval ID and code.", "task_status": "FAILED", "priority": "SECURITY"}

    def _deny(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        parts = intent.objective.split()
        if len(parts) < 2:
            return {"ok": False, "message": "Use /deny <approval_id> <approval_code>", "task_status": "FAILED", "priority": "FAILURE"}
        try:
            decided = self.orchestrator.policy.decide(parts[0], parts[1], False, "Denied from Telegram")
            return {"ok": True, "message": f"❌ DENIED\n{decided.id}\nAction: {decided.action}", "task_status": "COMPLETED", "priority": "IMPORTANT"}
        except Exception:
            return {"ok": False, "message": "Deny failed. Verify the approval ID and code.", "task_status": "FAILED", "priority": "SECURITY"}

    def _restart(self, envelope: TelegramTaskEnvelope, intent: TelegramIntent) -> dict[str, Any]:
        req = self.orchestrator.policy.request_approval("Gizmo", "restart", "human-owner", "Restart orchestration layer from Telegram.", "high")
        return self._approval_message(req, "Restart requires approval.")

    def _approval_message(self, req: Any, message: str) -> dict[str, Any]:
        buttons = [[{"text": "✅ APPROVE", "callback_data": f"/approve {req.id} {req.approval_code}"}, {"text": "❌ DENY", "callback_data": f"/deny {req.id} {req.approval_code}"}]]
        return {"ok": True, "message": f"⚠️ APPROVAL REQUIRED\n{message}\nAction: {req.action}\nID: {req.id}", "task_status": "HUMAN_REVIEW", "priority": "APPROVAL_REQUIRED", "inline_buttons": buttons}

    def _create_gizmo_task(self, objective: str, agent_id: str) -> Task:
        task = Task(project="Gizmo", objective=objective, assigned_agent=agent_id, priority=3)
        task.record("telegram_create", "Task created from Telegram control center")
        self.orchestrator.tasks.create_task(task)
        return task

    def _select_agent(self, objective: str) -> str:
        lowered = objective.lower()
        if "research" in lowered or "news" in lowered:
            return "agent-02"
        if "test" in lowered or "qa" in lowered:
            return "agent-11"
        if "security" in lowered or "audit" in lowered:
            return "agent-12"
        if "deploy" in lowered or "workflow" in lowered:
            return "agent-09"
        if "memory" in lowered or "learn" in lowered:
            return "agent-26"
        if "frontend" in lowered or "dashboard" in lowered:
            return "agent-07"
        if "database" in lowered:
            return "agent-08"
        return "agent-01"

    def _repo_parts(self) -> tuple[str, str]:
        repo = self.config.github_repository
        if "/" not in repo:
            return "unknown", repo
        owner, name = repo.split("/", 1)
        return owner, name

    def _autonomous_state(self) -> dict[str, Any]:
        return self.orchestrator.store.read("control", "autonomous_mode.json", default={"enabled": False, "paused": False, "emergency": False, "updated_at": now_iso()})

    def _set_autonomous(self, enabled: bool, paused: bool, emergency: bool) -> None:
        self.orchestrator.store.write({"enabled": enabled, "paused": paused, "emergency": emergency, "updated_at": now_iso(), "boundaries": ["approval_required", "policy_gated", "no_secret_memory"]}, "control", "autonomous_mode.json")

    def _list_tasks(self) -> list[dict[str, Any]]:
        try:
            return [task.to_dict() for task in self.orchestrator.tasks.list_tasks()]
        except Exception:
            return []
