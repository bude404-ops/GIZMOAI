# GIZMOAI General-Purpose Autonomous Worker Upgrade

GIZMOAI remains one system with one brain. This upgrade extends the existing orchestrator, agents, Memory Vault, scheduler, Telegram interface, CLI, tool registry, and safety policy instead of rebuilding them.

## Request Flow

Creator request -> intent classification -> task decomposition -> capability discovery -> tool/agent selection -> execution plan -> verification -> result -> selective memory.

Safe executable requests also pass through an execution ledger:

route plan -> task IDs or approval request -> dependency chain -> approval release -> step status -> safe runner -> recovery/escalation -> health report -> evidence -> refreshable execution record.

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
- approval release from gated execution into queued task chain
- failure recovery that requeues retryable failed steps and escalates exhausted tasks
- health reporting across waiting approvals, failed steps, escalations, stale queues, and next actions

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

Recover failed universal steps within their retry budget:

```bash
python -m gizmo.core.cli universal-recover
python -m gizmo.core.cli universal-recover --execution-id <execution_id> --max-steps 1
```

Inspect universal execution health:

```bash
python -m gizmo.core.cli universal-health
python -m gizmo.core.cli universal-health --stale-after-minutes 15
```

Release a gated universal execution after explicit approval:

```bash
python -m gizmo.core.cli universal-approve --approval-id <approval_id> --approval-code <approval_code>
python -m gizmo.core.cli universal-approve --approval-id <approval_id> --approval-code <approval_code> --run-after-approval
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
- approval request and release evidence for gated executions
- recovery evidence showing requeued and escalated task IDs

Approval-required requests create a ledger and approval request but no task IDs. Their status remains `WAITING_APPROVAL` until the operator approves the action. Approval release creates the task chain; it does not run unless `--run-after-approval` is explicitly used.

Failed steps are not hidden. `universal-recover` requeues failures while retry budget remains, clears stale results, records retry evidence, and marks exhausted tasks `ESCALATED` for operator review.

`universal-health` is the triage view. It reports risk level, execution counts by status, step counts, waiting approvals, failed tasks, escalations, stale queued work, dependency blockers, and recommended next actions.
