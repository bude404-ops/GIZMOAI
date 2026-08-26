# Phase 4 — Agent Memory Integration

Phase 4 binds Gizmo agents to the central Second Brain.

## Objective

No important lesson should remain trapped inside one agent. Agents must use the shared Brain before and after meaningful work.

The required loop is:

```text
Agent receives task
 ↓
Central Brain preflight
 ↓
Recall useful context
 ↓
Detect gaps
 ↓
Act inside policy limits
 ↓
Self-evaluate
 ↓
Capture experience
 ↓
Capture lesson
 ↓
Capture evaluation
 ↓
Update agent profile
 ↓
Share through collective memory
```

## Implemented components

### AgentBrainBridge

A central bridge that connects tasks and agents to the shared Brain.

It provides:

- `before_task()`
- `after_task()`
- `capture_meaningful_memory()`
- `agent_profile()`
- `collective_memory()`

### Brain preflight

Before a meaningful task executes, the bridge builds a Brain context pack and records:

- recalled memory ids
- knowledge gaps
- critical gap count
- preflight artifact
- agent profile update

### Automatic memory capture

After meaningful work, the bridge records:

- EXPERIENCE
- LESSON, when lessons exist
- EVALUATION

Captured memories link together through Brain relationships.

### Collective Agent Memory

Shared discoveries, lessons, and evaluations are written to collective memory so other agents can benefit from useful outcomes.

### Agent performance profiles

Each agent profile tracks:

- tasks seen
- tasks completed
- tasks failed
- average evaluation
- memory contributions
- common failures
- best skills
- last used

This becomes the foundation for future agent assignment and self-improvement.

## Orchestrator integration

The bootstrap task executor now runs Brain preflight before execution and captures memory after success or failure.

This ensures the existing execution path participates in the central Brain. Future agent adapters should use the same bridge instead of creating isolated memory systems.

## CLI

```bash
python -m gizmo.core.cli brain-phase4 --workspace .gizmo_runtime
```

The demo initializes prior Brain phases, creates a Phase 4 task, executes it through the bridge, records agent memory, updates the profile, writes collective memory, rebuilds the vault, and emits a verifiable report.

## Safety

Phase 4 improves memory and evaluation only. It does not grant autonomous destructive execution. All consequential actions remain governed by approval policy.

## Evidence

Tests verify:

- preflight uses central Brain context
- preflight artifacts are written
- after-task capture records experience, lesson, and evaluation memories
- collective memory receives shared lessons and evaluations
- agent profiles track performance and contributions
- orchestrator execution uses the Brain bridge
- Phase 4 demo passes

## Next phase

Phase 5 should create the Curiosity Engine:

- detect missing knowledge
- detect unresolved questions
- detect repeated failures
- detect inefficient processes
- maintain HIGH/MEDIUM/LOW curiosity queue
- select highest-value learning opportunities
- create research tasks without hallucinating answers
