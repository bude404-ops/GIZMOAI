# Phase 3 — Deep Obsidian Knowledge Vault

Phase 3 strengthens the human-readable Second Brain vault.

## Objective

The Brain must remain useful even outside the application. A Creator, agent, or future model should be able to open the Markdown vault and understand:

- what Gizmo knows
- which memories are current
- which projects and agents are involved
- how memories relate
- what changed over time
- where low-confidence or stale knowledge lives

## Implemented components

### Vault index pages

The vault now generates:

- `Memory Index`
- `Project Index`
- `Agent Index`
- `Quality Report`

These pages make the vault navigable in Obsidian or any Markdown reader.

### Project pages

Each project receives a generated page grouping memories by type.

### Agent pages

Each source agent receives a generated page listing knowledge contributed by that agent.

### Knowledge graph export

The vault exports both:

- Markdown graph view
- machine-readable JSON graph

Graph edges include explicit relationships and temporal supersession links.

### Backlinks

The vault writes a backlink report showing which memories point toward a target memory.

### Revision views

When a memory Markdown file is rewritten, the prior Markdown is preserved as a revision. This supports temporal memory and avoids silent loss of history.

### Session notes

The Brain can write session notes that reference relevant memories. These become readable work logs inside the vault.

## New API methods

The central Brain API now exposes:

- `rebuild_vault_indexes()`
- `record_session_note()`
- `export_graph()`

## CLI

```bash
python -m gizmo.core.cli brain-phase3 --workspace .gizmo_runtime
```

The demo initializes the Brain, runs Phase 2 recall, records Creator authority and vault portability memories, links them, forces a revision, writes a session note, rebuilds all vault indexes, exports the graph, and verifies required vault artifacts exist.

## Safety

Phase 3 does not delete historical knowledge. It preserves revisions and reports stale or conflicting knowledge instead of removing it.

## Evidence

Tests verify:

- indexes are generated
- project and agent pages are generated
- graph Markdown and JSON are generated
- backlinks are generated
- revisions preserve prior Markdown
- session notes reference memories
- Brain health exposes Phase 3 capabilities
- orchestrator Phase 3 demo passes

## Next phase

Phase 4 should integrate agent memory behavior:

- all agents recall from the central Brain before meaningful work
- all agents evaluate whether new knowledge should be recorded after meaningful work
- agent-specific performance and knowledge contributions are tracked
- no agent creates isolated incompatible memory
