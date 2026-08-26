# GIZMO — Autonomous Intelligence & Development Organization

GIZMO is a modular autonomous AI development organization operated through Reaper and GitHub.

It is not Base44. It is designed as an organization: an executive orchestrator, specialist agents, task planning, memory, tool governance, sandboxing, testing, security, observability, cost controls, and human control.

## Current milestone

**Bootstrap v0 is implemented.**

**Phase 1 GitHub Workspace Loop is implemented.**

**Phase 4 GitHub Second Brain is implemented locally.**

The system can initialize the organization, register the 27 core agents, create and execute tasks, store searchable memory, run harmless demo projects, reuse memory, detect capabilities, inspect GitHub workspace state, create branch-per-task plans, prepare PR plan artifacts, plan GitHub issue/PR/status API actions, enforce approval gates, route GitHub comments, build repo context packs, remember/retrieve lessons, and produce auditable reports.

## Design rule

Build → test → review → expand.

No giant untested codebase. No fabricated external capability. Destructive or production-level actions require human approval.

## Quickstart

```bash
python -m gizmo.core.cli bootstrap --workspace .gizmo_runtime
python -m gizmo.core.cli self-test --workspace .gizmo_runtime
python -m gizmo.core.cli github-demo --workspace .gizmo_runtime
python -m gizmo.core.cli github-api-demo --workspace .gizmo_runtime
python -m gizmo.core.cli policy-demo --workspace .gizmo_runtime
python -m gizmo.core.cli second-brain-demo --workspace .gizmo_runtime
python -m gizmo.core.cli second-brain-demo --workspace .gizmo_runtime --comment "/gizmo context approval policy"
python -m gizmo.core.cli status --workspace .gizmo_runtime
```

## Operating modes

- `MANUAL`: human approves important operations.
- `ASSISTED`: routine work allowed, significant changes require approval.
- `AUTONOMOUS`: approved categories can run independently.
- `EMERGENCY`: autonomous work stops immediately.

The emergency stop command is:

```text
GIZMO STOP
```

## Security

GIZMO never hard-codes secrets. Use environment variables or GitHub secrets. All destructive and production-level actions are policy-gated.

## Next expansion

Phase 1 should connect this bootstrap core to real GitHub branches/issues/PRs and add richer agent execution adapters while preserving the safety boundary.
