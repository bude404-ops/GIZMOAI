# Repository Audit — Telegram Control Center Build

## Existing systems reused

- Reaper/Gizmo orchestrator: existing `GizmoOrchestrator` remains central.
- Agents: 27 existing core agents are reused.
- GitHub: existing workspace and API adapter are extended.
- Memory: existing legacy memory plus Phase 1-4 Second Brain are reused.
- Approval policy: existing approval engine remains the gate for high-risk work.
- Logging: existing audit log is reused for concise Telegram log summaries.
- Dashboards: existing GIZMO Dashboard is updated, not replaced.

## Existing workflows

- tests
- GIZMO Second Brain

## Added workflows

- GIZMO Agent Runner
- GIZMO Research Agent
- GIZMO Developer Agent
- GIZMO Testing Agent
- GIZMO Security Agent
- GIZMO Learning Agent
- GIZMO Nightly Evolution
- GIZMO Telegram Command

## Architecture map

```text
Telegram
   ↓
Telegram Bot Runtime
   ↓
Telegram Command Router
   ↓
Authorization + intent detection
   ↓
Telegram Control Layer
   ↓
Reaper / GizmoOrchestrator
   ↓
Agent Orchestrator
   ↓
Existing 27 agents
   ↓
GitHub API + GitHub Actions
   ↓
Second Brain / Logs / Artifacts
   ↓
Telegram notifications
```

## Storage

Runtime state uses the existing JSON store. Persistent non-sensitive code, workflows, docs, configuration, and architecture live in GitHub.

## Secrets

No secrets were committed. Telegram, GitHub, and Reaper credentials are expected from environment variables or GitHub Secrets.
