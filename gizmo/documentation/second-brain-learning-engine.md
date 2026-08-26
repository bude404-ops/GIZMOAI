# Gizmo Second Brain + Autonomous Learning Engine

This document tracks the new phased build requested by the Creator.

## Objective

Gizmo is not a notes database. Gizmo is becoming a persistent autonomous AI operating system with shared memory, retrieval, research, experimentation, evaluation, procedural learning, goal management, and feedback loops.

Model weights are not modified or retrained. Learning comes from infrastructure:

- persistent memory
- retrieval
- research
- experimentation
- evaluation
- procedural learning
- goal management
- feedback loops

## Authority

Creator decisions have highest authority. Agents may propose changes, but they cannot silently overwrite Creator decisions or make consequential changes without approval.

## Phase Plan

1. Second Brain + persistent storage
2. Memory API + semantic retrieval
3. Obsidian-compatible knowledge vault
4. Agent memory integration
5. Curiosity Engine
6. Autonomous Research Engine
7. Experiment Engine + sandbox
8. Self-Evaluation Engine
9. Procedural + Skill Memory
10. Goal Manager
11. Self-Improvement Engine
12. Autonomous continuous-learning loop
13. Performance optimization + reliability
14. Full autonomous operation

## Phase 1 Implemented

Phase 1 creates the persistent shared brain foundation.

### Structured storage

Current backend: local JSON structured storage.

Designed fallback path:

1. database when configured
2. local structured write queue
3. Markdown vault
4. Git synchronization

No PostgreSQL/Supabase credential is assumed or fabricated.

### Human-readable vault

The brain creates an Obsidian-compatible Markdown vault with these directories:

- memory
- facts
- decisions
- preferences
- lessons
- experiences
- projects
- research
- experiments
- goals
- evaluations
- agents
- tasks
- sessions
- archive
- inbox

Every memory file uses YAML frontmatter, Markdown body, tags/properties, and wikilinks for entities.

### Memory types

Implemented memory types:

- FACT
- DECISION
- PREFERENCE
- LESSON
- EXPERIENCE
- PROJECT_STATE
- TASK
- RESEARCH
- CONVERSATION
- AGENT_MEMORY
- RELATIONSHIP
- WARNING
- IDEA
- HYPOTHESIS
- EXPERIMENT
- EVALUATION
- GOAL
- PROCEDURE
- SKILL

### Required fields

Every memory supports:

- id
- type
- title
- content
- summary
- created_at
- updated_at
- source
- source_agent
- project
- importance
- confidence
- status
- tags
- entities
- relationships
- supersedes
- superseded_by
- last_accessed
- access_count
- embedding

### Central API

Implemented:

- remember()
- recall()
- search_memory()
- semantic_search()
- get_related_memory()
- get_project_memory()
- get_agent_memory()
- record_fact()
- record_decision()
- record_lesson()
- record_experience()
- record_research()
- record_experiment()
- record_evaluation()
- record_goal()
- record_procedure()
- update_memory()
- supersede_memory()
- archive_memory()
- link_memories()

### Model independence

Phase 1 ships a local deterministic lexical embedder. It requires no AI provider and stores embeddings as plain numeric vectors. It can later be swapped for another embedding provider without changing memory records.

### Initial bootstrap

The bootstrap importer performs verified local import of:

- current repository structure
- current agent registry
- current documentation
- recent git history
- initial goals
- initial curiosity queue
- Brain Initialization Report

Unverified integrations are explicitly marked as future configuration, not claimed complete.

## Next Phase

Phase 2 should strengthen retrieval:

- hybrid scoring
- project relevance weighting
- recency weighting
- confidence weighting
- knowledge graph relationship expansion
- recall context builder before significant work
