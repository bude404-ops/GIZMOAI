"""Always-on cloud learning runner for GIZMO.

This module keeps autonomous learning state portable across cloud runs by writing
append-only snapshots, agent work packets, and Second Brain vault exports into the
configured workspace.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from gizmo.apps.factory import KnowledgeAppFactory
from gizmo.brain.models import BrainMemoryType
from gizmo.brain.semantic_index import DurableSemanticMemoryIndex
from gizmo.control.agent_body import AlwaysOnAgentBody
from gizmo.core.models import now_iso
from gizmo.ideas.autonomous_thinker import AutonomousThinker
from gizmo.knowledge.universal_sources import UniversalKnowledgeIngestor


SWARM_AGENTS = [
    ("agent-02", "research", "Find fresh public knowledge and summarize what matters."),
    ("agent-08", "database", "Preserve state, schemas, and storage lessons."),
    ("agent-09", "devops", "Improve cloud runtime, renewal, and failure recovery."),
    ("agent-13", "ai", "Improve agent reasoning, prompts, and coordination."),
    ("agent-20", "data", "Structure observations into datasets and signals."),
    ("agent-23", "docs", "Convert findings into operator-readable knowledge."),
    ("agent-26", "evolution", "Identify how GIZMO should improve itself next."),
    ("agent-27", "quality", "Synthesize results and reject weak learning."),
]

CLOUD_TOPICS = [
    "autonomous idea generation",
    "self-upgrade proposal ranking",
    "general public knowledge ingestion",
    "cross-domain source synthesis",
    "knowledge-to-app blueprint creation",
    "always-on Telegram reliability",
    "persistent Second Brain storage",
    "multi-agent autonomous coordination",
    "knowledge gap closure",
    "safe cloud learning cadence",
    "operator-visible summaries",
]


@dataclass
class CloudBrainCycle:
    cycle_id: str
    status: str
    started_at: str
    ended_at: str | None = None
    topics: list[str] = field(default_factory=list)
    agents: list[dict[str, Any]] = field(default_factory=list)
    memories_created: list[str] = field(default_factory=list)
    tasks_executed: list[str] = field(default_factory=list)
    gaps: list[dict[str, Any]] = field(default_factory=list)
    vault_report: dict[str, Any] = field(default_factory=dict)
    snapshot: dict[str, Any] = field(default_factory=dict)
    semantic_index: dict[str, Any] = field(default_factory=dict)
    supervisor_plan: dict[str, Any] = field(default_factory=dict)
    body_scorecard: dict[str, Any] = field(default_factory=dict)
    reasoning: list[dict[str, Any]] = field(default_factory=list)
    app_factory: dict[str, Any] = field(default_factory=dict)
    universal_knowledge: dict[str, Any] = field(default_factory=dict)
    autonomous_thinking: dict[str, Any] = field(default_factory=dict)
    notification: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CloudAutonomousBrainRunner:
    """Runs GIZMO's cloud brain as a policy-aware multi-agent learning swarm."""

    def __init__(self, orchestrator: Any, notifier: Any | None = None) -> None:
        self.orchestrator = orchestrator
        self.notifier = notifier
        self.store = orchestrator.store
        self.brain = orchestrator.brain_core
        self.semantic_index = DurableSemanticMemoryIndex(self.brain)
        self.body = AlwaysOnAgentBody(orchestrator)
        self.knowledge_ingestor = UniversalKnowledgeIngestor(self.brain, self.store)
        self.app_factory = KnowledgeAppFactory(self.brain, self.store)
        self.thinker = AutonomousThinker(self.brain, self.store)

    def enable(self, *, chat_id: str = "", source: str = "cloud") -> dict[str, Any]:
        state = {
            "enabled": True,
            "paused": False,
            "emergency": False,
            "updated_at": now_iso(),
            "source": source,
            "chat_id": str(chat_id),
            "mode": "cloud-autonomous-brain",
            "cadence": "continuous-renewed-cloud-loop",
            "storage": ["workspace-json", "second-brain-vault", "workflow-cache", "workflow-artifact"],
            "swarm_agents": [agent_id for agent_id, _, _ in SWARM_AGENTS],
            "boundaries": ["admin-only-telegram", "approval-gated-sensitive-actions", "no-secret-memory", "public-knowledge-only"],
        }
        self.store.write(state, "control", "cloud_brain_mode.json")
        self.store.write(state, "control", "autonomous_mode.json")
        return state

    def state(self) -> dict[str, Any]:
        return self.store.read("control", "cloud_brain_mode.json", default={"enabled": False, "paused": False, "emergency": False})

    def run_cycle(self, *, chat_id: str | None = None, topics: list[str] | None = None, execute_agents: bool = True) -> CloudBrainCycle:
        state = self.state()
        cycle = CloudBrainCycle(
            cycle_id=f"cloud-brain-{now_iso().replace(':', '').replace('.', '').replace('-', '')}",
            status="SKIPPED",
            started_at=now_iso(),
            topics=topics or CLOUD_TOPICS,
        )
        if not state.get("enabled") or state.get("paused") or state.get("emergency"):
            cycle.notification = self._format_skip(state)
            self._persist(cycle)
            return cycle

        cycle.status = "RUNNING"
        goal = self.brain.record_goal(
            "Always-on cloud brain learning",
            "Run a renewed cloud learning cycle that uses specialist agents, persists storage snapshots, and improves GIZMO without bypassing approvals.",
            source="cloud-brain",
            source_agent="agent-26",
            project="Gizmo",
            importance=9,
            confidence=0.92,
            tags=["cloud", "autonomous", "multi-agent", "learning"],
            metadata={"cycle_id": cycle.cycle_id},
        )
        cycle.memories_created.append(goal.id)

        ingestion = self.knowledge_ingestor.ingest(domain="general", limit=8)
        cycle.universal_knowledge = ingestion.to_dict()
        cycle.memories_created.extend(ingestion.memories_created)
        factory_report = self.app_factory.run(domain="general", limit=6)
        cycle.app_factory = factory_report.to_dict()
        thinking = self.thinker.think(cycle_id=cycle.cycle_id, topics=cycle.topics, limit=8)
        cycle.autonomous_thinking = thinking.to_dict()
        cycle.memories_created.extend(thinking.memories_created)

        cycle.supervisor_plan = self.body.supervisor_plan(topics=cycle.topics)
        priority_topics = cycle.supervisor_plan.get("priority_topics") or cycle.topics
        for index, (agent_id, lane, instruction) in enumerate(SWARM_AGENTS):
            topic = priority_topics[index % len(priority_topics)]
            semantic_matches = self.semantic_index.search(topic, project="Gizmo", limit=5)
            context = self.brain.build_context(topic, project="Gizmo", limit=8)
            gaps = self.brain.detect_knowledge_gaps(topic, project="Gizmo")
            cycle.gaps.extend(gaps[:2])
            action = self.body.execute_lane(agent_id=agent_id, lane=lane, topic=topic, instruction=instruction, context=context, execute=execute_agents)
            reasoning_memory = self.brain.record_research(
                f"Model reasoning {lane}: {topic}",
                self._agent_learning_summary(agent_id, lane, topic, instruction, context, gaps, semantic_matches, action),
                source="model-reasoner",
                source_agent=agent_id,
                project="Gizmo",
                importance=8,
                confidence=action.reasoning_confidence,
                tags=["model-backed", "semantic-search", "swarm", lane],
                metadata={"cycle_id": cycle.cycle_id, "agent_id": agent_id, "topic": topic, "task_id": action.task_id, "score": action.score},
            )
            lesson = self.brain.record_lesson(
                f"{lane.title()} body lesson: {topic}",
                f"{agent_id} used model-backed reasoning plus semantic memory before acting. Score {action.score}. Next actions: {'; '.join(action.next_actions)}",
                source="agent-body",
                source_agent=agent_id,
                project="Gizmo",
                importance=8,
                confidence=max(0.7, action.score),
                tags=["agent-body", "lesson", lane],
                metadata={"cycle_id": cycle.cycle_id, "reasoning_memory": reasoning_memory.id},
            )
            self.brain.link_memories(reasoning_memory.id, "produced_lesson", lesson.id, 0.88)
            cycle.memories_created.extend([reasoning_memory.id, lesson.id])
            cycle.tasks_executed.append(action.task_id)
            cycle.reasoning.append({"agent_id": agent_id, "lane": lane, "provider": action.reasoning_provider, "confidence": action.reasoning_confidence, "score": action.score})
            cycle.agents.append(action.to_dict())

        evaluation = self.brain.record_evaluation(
            "Cloud brain swarm evaluation",
            f"Cycle {cycle.cycle_id} ran {len(SWARM_AGENTS)} agent lanes, created {len(cycle.memories_created)} memories, executed {len(cycle.tasks_executed)} tasks, and tracked {len(cycle.gaps)} knowledge gaps.",
            source="cloud-brain",
            source_agent="agent-27",
            project="Gizmo",
            importance=8,
            confidence=0.9,
            tags=["cloud", "evaluation", "swarm"],
            metadata={"cycle_id": cycle.cycle_id},
        )
        cycle.memories_created.append(evaluation.id)
        cycle.vault_report = self.brain.rebuild_vault_indexes()
        cycle.semantic_index = self.semantic_index.rebuild(project="Gizmo").to_dict()
        cycle.body_scorecard = self.body.scorecard()
        cycle.ended_at = now_iso()
        cycle.status = "COMPLETED"
        cycle.snapshot = self._snapshot(cycle)
        cycle.notification = self._format_complete(cycle)
        self._persist(cycle)
        if chat_id and self.notifier:
            self.notifier.queue(chat_id, cycle.notification, "IMPORTANT")
        return cycle

    def latest_cycle(self) -> dict[str, Any] | None:
        return self.store.read("cloud", "brain_latest.json", default=None)

    def _snapshot(self, cycle: CloudBrainCycle) -> dict[str, Any]:
        registry = getattr(self.orchestrator, "agent_brain", None)
        collective = registry.collective_memory() if registry else {}
        snapshot = {
            "cycle_id": cycle.cycle_id,
            "generated_at": now_iso(),
            "status": cycle.status,
            "agent_count": len(cycle.agents),
            "memories_created": len(cycle.memories_created),
            "tasks_executed": len(cycle.tasks_executed),
            "gaps_tracked": len(cycle.gaps),
            "reasoning_events": len(cycle.reasoning),
            "reasoning_providers": sorted({item.get("provider", "unknown") for item in cycle.reasoning}),
            "semantic_indexed_memories": cycle.semantic_index.get("indexed_memories", 0),
            "body_actions_scored": cycle.body_scorecard.get("actions", 0),
            "universal_sources_seen": cycle.universal_knowledge.get("sources_seen", 0),
            "app_blueprints_created": len(cycle.app_factory.get("blueprints_created", [])),
            "app_backlog_size": cycle.app_factory.get("backlog_size", 0),
            "autonomous_ideas_created": len(cycle.autonomous_thinking.get("ideas", [])),
            "upgrade_proposals_created": len(cycle.autonomous_thinking.get("upgrades", [])),
            "chosen_next_actions": len(cycle.autonomous_thinking.get("chosen_next", [])),
            "vault_report": cycle.vault_report,
            "collective_counts": {k: len(v) if isinstance(v, list) else v for k, v in collective.items()},
        }
        self.store.write(snapshot, "cloud", "brain_snapshot.json")
        self.store.append_list(snapshot, "cloud", "brain_snapshots.json")
        return snapshot

    def _persist(self, cycle: CloudBrainCycle) -> None:
        self.store.write(cycle.to_dict(), "cloud", "brain_latest.json")
        self.store.write(cycle.to_dict(), "cloud", "brain_cycles", f"{cycle.cycle_id}.json")
        self.store.append_list(cycle.to_dict(), "cloud", "brain_history.json")

    def _agent_learning_summary(self, agent_id: str, lane: str, topic: str, instruction: str, context: Any, gaps: list[dict[str, Any]], semantic_matches: list[dict[str, Any]], action: Any) -> str:
        memories = getattr(context, "memories", []) or []
        gap_names = [gap.get("topic") or gap.get("requirement", "unknown") for gap in gaps[:3]]
        match_titles = [item.get("title", "unknown") for item in semantic_matches[:3]]
        return (
            f"{agent_id} handled the {lane} lane for {topic}. Directive: {instruction} "
            f"Context memories inspected: {len(memories)}. Semantic matches: {', '.join(match_titles) if match_titles else 'none'}. "
            f"Gaps: {', '.join(gap_names) if gap_names else 'none detected'}. "
            f"Reasoning provider: {action.reasoning_provider}; confidence {action.reasoning_confidence}; body score {action.score}. "
            "Outcome is stored as public, non-secret operational knowledge for future cycles."
        )

    def _format_skip(self, state: dict[str, Any]) -> str:
        return (
            "☁️ CLOUD BRAIN SKIPPED\n"
            f"Enabled: {state.get('enabled', False)}\n"
            f"Paused: {state.get('paused', False)}\n"
            f"Emergency: {state.get('emergency', False)}"
        )

    def _format_complete(self, cycle: CloudBrainCycle) -> str:
        return (
            "☁️ CLOUD BRAIN CYCLE COMPLETE\n"
            f"Cycle: {cycle.cycle_id}\n"
            f"Agents: {len(cycle.agents)}\n"
            f"Memories: {len(cycle.memories_created)}\n"
            f"Tasks executed: {len(cycle.tasks_executed)}\n"
            f"Gaps tracked: {len(cycle.gaps)}\n"
            f"Universal sources: {cycle.universal_knowledge.get('sources_seen', 0)}\n"
            f"App blueprints: {len(cycle.app_factory.get('blueprints_created', []))}\n"
            f"Ideas generated: {len(cycle.autonomous_thinking.get('ideas', []))}\n"
            f"Upgrade proposals: {len(cycle.autonomous_thinking.get('upgrades', []))}\n"
            "Storage: persisted + snapshotted"
        )
