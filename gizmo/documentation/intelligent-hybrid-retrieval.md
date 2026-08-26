# Phase 2 — Intelligent Hybrid Retrieval

Phase 2 strengthens the Second Brain from storage into useful pre-work intelligence.

## Objective

Before significant work, Gizmo should stop, recall what matters, identify what is missing, and only then act.

The preflight loop is:

```text
TASK
 ↓
Identify project
 ↓
Retrieve relevant memories
 ↓
Retrieve decisions
 ↓
Retrieve lessons
 ↓
Retrieve previous failures
 ↓
Retrieve related procedures
 ↓
Retrieve current project state
 ↓
Detect knowledge gaps
 ↓
Create research tasks when critical knowledge is missing
 ↓
Build useful context
 ↓
ACT
```

## Implemented components

### HybridRetriever

Scores memory using:

- keyword match
- semantic vector similarity
- project relevance
- recency
- importance
- confidence
- graph relationship signal

It returns retrieval traces so Gizmo can explain why a memory was selected.

### ContextBuilder

Builds a task-ready context pack containing:

- useful context
- decisions
- lessons
- procedures
- project state
- warnings
- knowledge gaps
- proposed research tasks
- retrieval trace

The context pack is designed to be passed to any model provider. It contains infrastructure-level memory, not model-specific state.

### KnowledgeGapDetector

Detects missing or low-confidence knowledge for common high-value work areas:

- deployment
- database
- GitHub
- retrieval
- experiments
- learning

Critical gaps create research task memories automatically. Gizmo does not hallucinate missing knowledge.

## New API methods

The central brain now exposes:

- `hybrid_search()`
- `build_context()`
- `detect_knowledge_gaps()`

These sit beside the Phase 1 methods and keep all agent memory access centralized.

## CLI

```bash
python -m gizmo.core.cli brain-phase2 --workspace .gizmo_runtime
```

The demo initializes the brain, records a retrieval procedure, builds a context pack for GitHub workflow learning, runs hybrid retrieval, stores a Phase 2 report, and emits verifiable JSON.

## Safety

Phase 2 does not grant autonomous execution privileges. It improves recall and research-task creation only. Consequential work remains governed by the existing approval policy.

## Evidence

Tests verify:

- hybrid retrieval returns scored traces
- Creator decisions rank with high authority when relevant
- context packs contain decisions, lessons, procedures, and traces
- critical knowledge gaps create research-task memories
- bootstrapped brain data supports Phase 2 context building
- orchestrator Phase 2 demo passes

## Next phase

Phase 3 should deepen the Obsidian vault:

- stronger backlinks
- graph exports
- vault index pages
- daily/session notes
- memory revision history views
- relationship repair reports
