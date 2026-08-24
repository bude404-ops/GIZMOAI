# Phase 1 — Historical Database + Research Engine

Phase 1 implements the foundation for Historia's research-first content system.

## Pipeline

`DISCOVER -> VERIFY -> STRUCTURE -> STORE -> GENERATE`

## Implemented components

- SQLite schema with idempotent migrations.
- Historical figure records.
- Source records with reliability scoring.
- Fact records split into:
  - `VERIFIED_FACT`
  - `HISTORICAL_INTERPRETATION`
  - `AI_DRAMATIZATION`
- Source-to-fact linking.
- Uncertainty and myth tracking.
- Visual references for clothing, portraits, sculptures, architecture, and cultural context.
- Historical character bible skeletons.
- Scene concepts.
- Text-only content ideas with normalized scoring.
- Historical accuracy preflight table.

## Guardrails

- Adult-only records.
- At least two sources required per historical research record.
- Verified facts require source backing.
- Possible quote claims cannot be stored as interpretation or dramatization.
- Unknown appearance is labeled reconstruction.
- AI-generated disclosure metadata is stored on every content idea.

## Seed subjects

- Hatshepsut
- Boudica
- Ada Lovelace
- Cleopatra VII Philopator

## Later phases

Phase 1 deliberately avoids expensive media generation. Image, video, voice,
quality-control media inspection, X publishing, analytics, and learning loops are
reserved for later phases.
