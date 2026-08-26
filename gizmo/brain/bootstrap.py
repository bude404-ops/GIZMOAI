"""Initial repository-to-brain bootstrap importer."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from gizmo.agents.core_agents import CORE_AGENTS
from gizmo.brain.memory_api import SecondBrain
from gizmo.brain.models import BrainMemoryType


class BrainBootstrapper:
    def __init__(self, brain: SecondBrain, repo_path: str | Path) -> None:
        self.brain = brain
        self.repo_path = Path(repo_path)

    def initialize_from_repository(self) -> dict[str, Any]:
        created = []
        created.append(self._record_project_state())
        created.extend(self._record_agents())
        created.extend(self._record_documentation())
        created.extend(self._record_git_history())
        goals = self._record_initial_goals()
        gaps = self._record_initial_curiosity_queue()
        report = self.brain.remember(
            BrainMemoryType.EVALUATION,
            "Brain Initialization Report",
            "Initialized the persistent Second Brain from current repository structure, agents, documentation, and git history. Uncertainty remains around production database configuration until credentials are supplied.",
            summary="Initial Second Brain bootstrap completed from verified local repository data.",
            source="bootstrap",
            source_agent="reaper",
            importance=9,
            confidence=0.9,
            tags=["brain", "initialization", "report"],
            entities=["Gizmo", "Reaper", "Second Brain"],
            metadata={"created_memories_before_report": len(created), "goals": len(goals), "knowledge_gaps": len(gaps)},
        )
        return {"created": len(created) + len(goals) + len(gaps) + 1, "report_id": report.id, "health": self.brain.export_health()}

    def _record_project_state(self):
        files = [p.as_posix() for p in self.repo_path.rglob("*") if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts]
        return self.brain.remember(
            BrainMemoryType.PROJECT_STATE,
            "Gizmo Repository State",
            f"Repository contains {len(files)} tracked or local files across Gizmo source, tests, documentation, GitHub workflows, and support scripts.",
            source="repository-inspection",
            source_agent="reaper",
            importance=8,
            confidence=0.95,
            tags=["project-state", "repository"],
            entities=["Gizmo", "GitHub"],
            metadata={"file_count": len(files), "sample_files": files[:40]},
        )

    def _record_agents(self):
        records = []
        for agent in CORE_AGENTS:
            records.append(self.brain.remember(
                BrainMemoryType.AGENT_MEMORY,
                f"{agent.id} {agent.name}",
                f"Role: {agent.role}\nObjectives: {', '.join(agent.objectives)}\nTask types: {', '.join(agent.task_types)}",
                summary=f"{agent.name}: {agent.role}",
                source="agent-registry",
                source_agent="reaper",
                importance=7,
                confidence=1.0,
                tags=["agent", *agent.task_types],
                entities=[agent.id, agent.name, "Agent Network"],
                metadata=agent.to_dict(),
            ))
        return records

    def _record_documentation(self):
        records = []
        docs = [self.repo_path / "README.md", *sorted((self.repo_path / "gizmo" / "documentation").glob("*.md"))]
        for doc in docs:
            if not doc.exists():
                continue
            text = doc.read_text(errors="ignore")
            records.append(self.brain.remember(
                BrainMemoryType.FACT,
                f"Documentation: {doc.name}",
                text[:2500],
                summary=f"Imported project documentation from {doc.name}.",
                source="documentation-import",
                source_agent="reaper",
                importance=6,
                confidence=0.95,
                tags=["documentation", "import"],
                entities=["Gizmo", doc.stem],
                metadata={"path": doc.relative_to(self.repo_path).as_posix(), "characters_imported": min(len(text), 2500), "characters_total": len(text)},
            ))
        return records

    def _record_git_history(self):
        output = subprocess.run(["git", "log", "--oneline", "-12"], cwd=self.repo_path, text=True, capture_output=True, check=True).stdout.strip()
        return [self.brain.remember(
            BrainMemoryType.FACT,
            "Recent Git History",
            output,
            summary="Imported recent verified Git commit history.",
            source="git-log",
            source_agent="reaper",
            importance=7,
            confidence=1.0,
            tags=["git", "history"],
            entities=["GitHub", "Gizmo"],
        )]

    def _record_initial_goals(self):
        goals = [
            ("Improve Gizmo autonomy", "Build persistent memory, retrieval, curiosity, research, experiments, evaluations, skills, goals, and continuous learning loops."),
            ("Keep Creator control", "Require explicit Creator approval for security, destructive, credential, spending, and major architecture changes."),
            ("Make learning evidence-driven", "Prefer experiments, evaluations, and verified experience over assumptions."),
        ]
        return [self.brain.record_goal(title, body, source="creator-objective", source_agent="reaper", importance=9, confidence=1.0, tags=["goal", "autonomy"], entities=["Creator", "Gizmo"]) for title, body in goals]

    def _record_initial_curiosity_queue(self):
        items = [
            ("HIGH", "Which memory retrieval strategy works best for Gizmo repository questions?"),
            ("HIGH", "What failures repeat across GitHub workflows and deployments?"),
            ("MEDIUM", "Would a hosted vector database improve recall without increasing fragility?"),
            ("LOW", "Which Obsidian graph conventions produce the clearest project map?"),
        ]
        return [self.brain.remember(BrainMemoryType.HYPOTHESIS, f"Curiosity {priority}: {question}", question, source="curiosity-bootstrap", source_agent="agent-26", importance={"HIGH": 9, "MEDIUM": 6, "LOW": 3}[priority], confidence=0.65, tags=["curiosity", priority.lower()], entities=["Learning Core", "Curiosity Engine"]) for priority, question in items]
