# Agent Architecture

Gizmo already contains 27 core agents. Telegram integration reuses them instead of creating duplicates.

Each agent definition includes:

- Agent ID
- Name
- Role
- Capabilities/task types
- Permissions
- Memory namespace
- Evaluation criteria
- Trust/sandbox flags

Phase 4 added agent memory profiles with:

- tasks seen
- tasks completed
- tasks failed
- average evaluation
- memory contributions
- common failures
- best skills
- last used

Telegram `/agents` reads the existing registry and augments it with profile data.

## Assignment

The Telegram control layer performs lightweight routing and leaves orchestration to Reaper. Examples:

- research/news → Research Agent
- test/QA → QA Agent
- security/audit → Security Agent
- deploy/workflow → DevOps Agent
- memory/learn → Evolution Agent
- frontend/dashboard → Frontend Agent
- database → Database Agent
- default → Executive Architect

Future assignment should use the agent profiles and Second Brain history.
