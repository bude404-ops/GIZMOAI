# GIZMOAI General-Purpose Autonomous Worker Upgrade

GIZMOAI remains one system with one brain. This upgrade extends the existing orchestrator, agents, Memory Vault, scheduler, Telegram interface, CLI, tool registry, and safety policy instead of rebuilding them.

## Request Flow

Creator request -> intent classification -> task decomposition -> capability discovery -> tool/agent selection -> execution plan -> verification -> result -> selective memory.

Safe executable requests also pass through an execution ledger:

route plan -> task IDs -> dependency chain -> approval state -> step status -> safe runner -> evidence -> refreshable execution record.

## Capability Registry

The registry is dynamic and provider-neutral. Each capability declares:

- capability name
- description
- tools
- agents
- providers
- permissions
- cost
- reliability
- input schema
- output schema
- verification method
- guardrail mode

Registered capabilities:

1. question_answer
2. web_research
3. software_development
4. github
5. unreal_engine
6. ai_generation
7. business_analysis
8. data_analysis
9. system_administration
10. trading

Trading is intentionally one capability. It does not define the architecture.

## Research Pipeline

The research subsystem is structured as:

search -> collect -> filter -> read -> cross-check -> synthesize -> cite -> store useful knowledge.

The report separates:

- FACT
- SOURCE
- INFERENCE
- HYPOTHESIS
- UNCERTAINTY

Each useful source or claim records provenance, quality, confidence, and memory metadata.

## Project Mode

Project-scale requests create persistent project state and route through:

discover -> requirements -> research -> architecture -> plan -> build -> test -> debug -> deploy/package -> monitor -> improve.

GIZMO records project state, files, technologies, decisions, failures, fixes, and verification evidence.

## Unreal Engine Mode

Unreal requests route to the Unreal integration layer. It detects the available editor/project bridge, records automation interfaces, creates honest bridge reports, and requires real evidence: project files, generated scripts, build/test logs, or a clear bridge blocker.

## AI Generation Mode

Generation is provider-neutral across TEXT, IMAGE, VIDEO, AUDIO, 3D, VOICE, and CODE. Each request records provider, model, project, result artifacts, cost estimate, quality score, and license notes.

## Guardrails

Capability modes are:

- AUTO
- APPROVAL_REQUIRED
- DISABLED

Dangerous or high-impact operations remain approval-gated, including production deployment, destructive database operations, credential changes, destructive project deletion, and financial execution.

## Acceptance Proof

Run:

```bash
python -m gizmo.core.cli universal-acceptance
```

The proof covers:

- latest-question research routing
- market research with sources
- software project mode
- debugging reproduction/root-cause planning
- Unreal bridge honesty
- AI generation manifest creation
- memory retrieval planning
- unknown-problem research behavior
- trading remaining one capability, not the core
- execution ledger handoff from universal route to traceable task IDs
- dependency-aware execution runner advancing ready steps only

## Execution Handoff

Run a safe request as queued internal work:

```bash
python -m gizmo.core.cli universal-execute --text "Build a small verified automation script."
```

Advance queued execution steps through the safe bootstrap executor:

```bash
python -m gizmo.core.cli universal-run --max-steps 1
python -m gizmo.core.cli universal-run --execution-id <execution_id>
```

The result includes an `execution` record with:

- execution_id
- request_id
- task_ids
- step-to-task mapping
- approval_required
- permission_mode
- acceptance_checks
- verification evidence
- runner evidence showing how many ready steps advanced and what remained blocked/skipped

Approval-required requests create a ledger but no task IDs. Their status remains `WAITING_APPROVAL` until the operator approves the action.
