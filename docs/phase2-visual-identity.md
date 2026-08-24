# Phase 2 — Character Bible + Visual Identity System

Phase 2 turns Phase 1 research records into consistent visual identity plans for later image and video providers.

## Implemented components

- `VisualIdentityEngine`
- Visual identity profile storage
- Wardrobe option storage
- Environment option storage
- Visual prompt template storage
- Visual identity audit storage
- CLI support for building visual identities

## Purpose

The system prevents Historia from becoming random AI-model output. Every character now gets repeatable creative constraints:

- Adult-only identity anchor
- Face signature
- Silhouette signature
- Hair signature
- Skin texture rules
- Color palette
- Camera rules
- Lighting rules
- Negative prompt rules
- Reconstruction disclosure
- Approved wardrobe
- Approved environments
- Provider-neutral prompt templates

## Visual appeal rules

The engine optimizes for tasteful scroll-stop visuals:

- Dramatic lighting
- Cinematic framing
- Elegant wardrobe
- Confident expressions
- Rich historical environments
- Realistic skin, hair, fabric, and jewelry

It rejects identity text containing unsafe or explicit terms. The goal is attractive and sophisticated, never graphic.

## Historical labeling

Historical characters receive:

`AI historical reconstruction`

Fictional characters will later receive:

`AI fictional historical-inspired character`

## CLI

Build seed data and visual identities together:

```bash
PYTHONPATH=src python -m historia.cli build-seed --db data/historia.db
```

Build visual identities for an existing database:

```bash
PYTHONPATH=src python -m historia.cli build-visual-identities --db data/historia.db
```

Summarize research and identity coverage:

```bash
PYTHONPATH=src python -m historia.cli summary --db data/historia.db
```

## Still out of scope

Phase 2 does not call image or video APIs. It prepares provider-neutral prompt templates and identity constraints so Phase 4/5 generation can be plugged in cleanly.
