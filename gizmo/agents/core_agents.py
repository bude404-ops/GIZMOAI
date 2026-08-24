"""The initial 27 core GIZMO agents."""
from __future__ import annotations

from gizmo.core.models import AgentDefinition

_AGENT_SPECS = [
    ("01", "Executive Architect", "System architecture, dependencies, technical decisions, and project structure.", ["architect", "plan", "review"]),
    ("02", "Research Agent", "Researches technologies, documentation, algorithms, competitors, public information, and resources.", ["research", "summarize"]),
    ("03", "Product Agent", "Converts goals into requirements, milestones, features, and acceptance criteria.", ["requirements", "milestones"]),
    ("04", "Game Director", "Handles game systems, gameplay loops, mechanics, balancing, progression, and game design.", ["game-design", "balance"]),
    ("05", "Unreal Engineer", "Responsible for Unreal project creation, C++, Blueprint architecture, configuration, builds, and automation.", ["unreal", "build"]),
    ("06", "Backend Engineer", "Creates APIs, services, authentication systems, server logic, and backend architecture.", ["backend", "api"]),
    ("07", "Frontend Engineer", "Creates web interfaces, dashboards, mobile-friendly interfaces, and frontend applications.", ["frontend", "ui"]),
    ("08", "Database Engineer", "Designs databases, schemas, migrations, indexes, data relationships, and persistence.", ["database", "migrations"]),
    ("09", "DevOps Engineer", "Handles environments, deployments, CI/CD, containers, automation, infrastructure, and build pipelines.", ["devops", "ci"]),
    ("10", "GitHub Engineer", "Manages repositories, branches, commits, PRs, workflows, Actions, project structures, and version control.", ["git", "github"]),
    ("11", "QA Engineer", "Creates automated tests, integration tests, regression tests, and acceptance testing.", ["test", "qa"]),
    ("12", "Security Engineer", "Audits permissions, dependencies, secrets, authentication, authorization, generated code, and deployment risks.", ["security", "audit"]),
    ("13", "AI Engineer", "Designs AI systems, model pipelines, prompts, agent systems, inference workflows, and integrations.", ["ai", "agents"]),
    ("14", "3D Engineer", "Handles 3D assets, procedural generation, models, environments, geometry, materials, and pipelines.", ["3d", "assets"]),
    ("15", "Art Director", "Maintains visual consistency, style guides, asset requirements, visual quality, and artistic direction.", ["art", "style"]),
    ("16", "Animation Engineer", "Handles animation systems, rigs, animation logic, procedural animation, and integration.", ["animation", "rigs"]),
    ("17", "Audio Engineer", "Handles music systems, sound effects, voice pipelines, audio organization, and implementation.", ["audio", "music"]),
    ("18", "Lore / Narrative Agent", "Creates and maintains worlds, characters, lore, stories, dialogue, histories, and narrative consistency.", ["lore", "narrative"]),
    ("19", "Content Agent", "Generates structured content, missions, items, descriptions, documentation content, and other content.", ["content", "copy"]),
    ("20", "Data Engineer", "Handles data processing, transformation, analysis, pipelines, datasets, validation, and structured information.", ["data", "pipeline"]),
    ("21", "Finance / Economics Agent", "Analyzes costs, resource usage, monetization models, budgets, and economic systems when relevant.", ["finance", "cost"]),
    ("22", "Marketing Agent", "Handles positioning, messaging, launch planning, social content, discoverability, and marketing strategy.", ["marketing", "launch"]),
    ("23", "Documentation Agent", "Creates technical docs, user docs, architecture docs, API docs, and changelogs.", ["docs", "changelog"]),
    ("24", "Performance Engineer", "Profiles systems, identifies bottlenecks, optimizes code/assets/workflows, and monitors resource usage.", ["performance", "profile"]),
    ("25", "Integration Engineer", "Connects external services, APIs, SDKs, databases, automation services, and project systems.", ["integration", "sdk"]),
    ("26", "Evolution Agent", "Analyzes GIZMO itself and identifies improvements to agents, workflows, tools, memory, and processes.", ["evolution", "learning"]),
    ("27", "Quality/Synthesis Agent", "Performs final cross-disciplinary review and determines whether work satisfies the original objective.", ["review", "synthesis"]),
]


CORE_AGENTS: list[AgentDefinition] = [
    AgentDefinition(
        id=f"agent-{number}",
        name=name,
        role=role,
        objectives=[role, "Operate inside policy boundaries", "Record important outcomes to memory"],
        allowed_tools=["memory.search", "memory.add", "task.update", "message.send", "artifact.write"],
        memory_namespace=f"agent-{number}",
        task_types=task_types,
        evaluation_criteria=["Produces verifiable artifacts", "Documents assumptions", "Escalates unsafe or blocked work"],
        trusted=True,
        sandbox_required=False,
    )
    for number, name, role, task_types in _AGENT_SPECS
]


def core_agent_map() -> dict[str, AgentDefinition]:
    return {agent.id: agent for agent in CORE_AGENTS}
