# GIZMOAI General-Purpose Autonomous Worker Upgrade

GIZMOAI remains one system with one brain. This upgrade extends the existing orchestrator, agents, Memory Vault, scheduler, Telegram interface, CLI, tool registry, and safety policy instead of rebuilding them.

## Request Flow

Creator request -> intent classification -> task decomposition -> capability discovery -> tool/agent selection -> execution plan -> verification -> result -> selective memory.

Safe executable requests also pass through an execution ledger:

route plan -> task IDs or approval request -> dependency chain -> approval release -> step status -> safe runner -> checkpoint/rollback -> pause/resume -> recovery/escalation/cancellation -> outcome evaluation -> failure-pattern learning -> long-horizon progress evaluation -> autonomous goal selection -> health report -> evidence -> refreshable execution record.

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
- cancellation that stops queued or approval-waiting execution records without releasing hidden work
- pause/resume that holds unfinished work reversibly and blocks runner progress until resumed
- checkpoint/rollback that restores execution and task state to a known safe point
- outcome evaluation that judges whether execution actually solved the requested intent
- autonomous goal selection that ranks health, outcome, body queue, upgrade queue, learned failure rules, and thinking signals into the next objective
- failure-pattern learning that turns failed/escalated execution evidence into persistent lessons and recovery rules
- long-horizon progress evaluation that judges whether autonomy is advancing, mixed, or stalled across cycles

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

Cancel unfinished universal execution work:

```bash
python -m gizmo.core.cli universal-cancel --execution-id <execution_id> --reason "operator changed priority"
python -m gizmo.core.cli universal-cancel --reason "cancel latest execution"
```

Create a checkpoint, rollback, or evaluate whether work solved the original intent:

```bash
python -m gizmo.core.cli universal-checkpoint --execution-id <execution_id> --label "before risky run"
python -m gizmo.core.cli universal-rollback --execution-id <execution_id> --checkpoint-id <checkpoint_id> --reason "restore safe point"
python -m gizmo.core.cli universal-evaluate --execution-id <execution_id>
python -m gizmo.core.cli autonomous-learn-failures --min-occurrences 1
python -m gizmo.core.cli autonomous-progress --cycles 5
python -m gizmo.core.cli autonomous-goal --route
```

Pause or resume unfinished universal execution work:

```bash
python -m gizmo.core.cli universal-pause --execution-id <execution_id> --reason "hold until review"
python -m gizmo.core.cli universal-resume --execution-id <execution_id> --reason "review complete"
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
- cancellation evidence showing cancelled items, preserved terminal items, and operator reason
- pause/resume evidence showing held items, resumed items, and runner blocks while paused
- checkpoint evidence showing saved execution/task state, label, reason, and task count
- rollback evidence showing restored checkpoint, previous status, force flag, and restored task IDs
- outcome evaluation showing verdict, confidence, blockers, evidence presence, and next actions
- autonomous goal decisions showing selected objective, score, source, lane, evidence, memory ID, and optional routed plan
- failure-learning reports showing patterns, lessons, recovery rules, severity, confidence, and next actions
- progress evaluations showing long-horizon verdict, score, trend, blockers, strategic gaps, signals, and memory ID

Approval-required requests create a ledger and approval request but no task IDs. Their status remains `WAITING_APPROVAL` until the operator approves the action. Approval release creates the task chain; it does not run unless `--run-after-approval` is explicitly used.

Failed steps are not hidden. `universal-recover` requeues failures while retry budget remains, clears stale results, records retry evidence, and marks exhausted tasks `ESCALATED` for operator review.

Unfinished work can be stopped explicitly with `universal-cancel`. Queued/running/waiting tasks become `CANCELLED`, waiting approval records do not release tasks, completed work is preserved, and future runner calls are blocked with cancellation evidence.

Unfinished work can also be held without ending it. `universal-pause` moves queued or waiting work to `PAUSED`, records the reason, and blocks future runner calls. `universal-resume` returns task-backed work to `QUEUED` or approval-gated work to `WAITING_APPROVAL` without silently releasing tasks.

`universal-checkpoint` captures execution and linked task state before risky moves. `universal-rollback` restores that state from the latest or named checkpoint; terminal records require `--force` so history is not rewritten casually.

`universal-evaluate` is the first operator-intelligence layer. It judges execution against status, step completion, runner evidence, verification evidence, blockers, and checkpoint availability, then returns `SOLVED`, `NEEDS_REVIEW`, or `NOT_SOLVED` with confidence and next actions.

`autonomous-learn-failures` is the first self-improvement loop. It reads failed and escalated universal execution evidence, groups recurring signatures, writes durable lessons, and creates recovery rules for future cycles.

`autonomous-progress` is the long-horizon evaluator. It reads recent cloud snapshots, goal decisions, failure learning, health, and outcome verdicts, then decides whether GIZMO is `ADVANCING`, in `MIXED_PROGRESS`, or `STALLED`.

`autonomous-goal` is the first self-directed goal loop. It reads progress evaluations, health, the latest outcome verdict, learned failure rules, agent-body next actions, autonomous thinker upgrades, and chosen ideas, then records the highest-scoring next objective. With `--route`, it creates a universal plan for the selected goal without needing the operator to name the next step.

`universal-health` is the triage view. It reports risk level, execution counts by status, step counts, waiting approvals, paused work, checkpoint availability, failed tasks, escalations, stale queued work, dependency blockers, and recommended next actions.
