# History After Dark

AI historical women content engine: a research-first cinematic studio for short-form X content.

The core premise:

> What if history's most fascinating women came alive again?

This project is not a generic attractive AI model generator. It is designed to turn a historical woman into:

`Research -> Hook -> Cinematic Visual -> AI Video -> Caption -> X Post -> Analytics -> Learning`

## Current milestone

**Phase 1 is implemented:** historical database + research engine.

**Phase 2 is implemented:** character bible + visual identity system.

The project now has the research foundation and the visual consistency layer needed before expensive image or video generation.

## Implemented in Phase 1

- Historical figure database.
- Reliable source tracking.
- Fact classification:
  - `VERIFIED_FACT`
  - `HISTORICAL_INTERPRETATION`
  - `AI_DRAMATIZATION`
- Source-to-fact links.
- Historical uncertainty handling.
- Myth/interpretation controls.
- Visual reference tracking for portraits, sculpture, clothing, architecture, and environments.
- Historical character bible foundation.
- Cinematic scene concept storage.
- Text-only content idea generation.
- Virality-style normalized content scoring.
- Historical accuracy preflight checks.
- Adult-only guardrails.
- Quote safety guardrails.
- AI reconstruction disclosure metadata.

## Implemented in Phase 2

- Character visual identity profiles.
- Consistent face, silhouette, hair, palette, lighting, and camera rules.
- Tasteful visual appeal constraints.
- Approved wardrobe options.
- Approved environment options.
- Provider-neutral visual prompt templates.
- Visual identity audits for consistency, historical fit, appeal, and safety.
- Adult-only/non-explicit prompt safety checks.

## Seed historical subjects

- Hatshepsut
- Boudica
- Ada Lovelace
- Cleopatra VII Philopator

## Run tests

```bash
python -m pytest -q
```

## Build seed database

```bash
PYTHONPATH=src python -m historia.cli build-seed --db data/historia.db
PYTHONPATH=src python -m historia.cli summary --db data/historia.db
```

The local `data/` directory is intentionally ignored by git.

## Development phases

1. Historical database + research engine — complete.
2. Character Bible + visual identity system — complete.
3. Content idea + hook + script engine expansion.
4. Image generation.
5. Video provider abstraction.
6. Voice/audio generation.
7. Quality-control system.
8. X publishing.
9. Analytics.
10. A/B testing.
11. Learning engine.
12. Fully automated content pipeline.

## Safety rules

- Never commit API keys or secrets.
- Never invent quotes and present them as authentic.
- Never present fictional events as documented history.
- Fictional characters must be clearly labeled fictional.
- Historical recreations must be labeled as AI reconstructions.
