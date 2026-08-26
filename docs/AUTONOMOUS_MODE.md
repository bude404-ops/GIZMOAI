# Autonomous Mode

Telegram supports:

- `/autonomous on`
- `/autonomous off`
- `/pause`
- `/resume`
- `/stop`

Autonomous mode is permission-bound. It may inspect projects, create tasks, assign agents, execute safe work, test, review, update memory, and select next tasks.

It may not bypass approval requirements.

## Emergency states

- Pause: block new autonomous work while allowing approved active work to finish.
- Resume: restore manual control and clear pause state.
- Stop: set emergency mode and halt new autonomous work.

## Learning loop

```text
OBSERVE → RESEARCH → EXPERIMENT → IMPLEMENT → TEST → REVIEW → MEASURE → STORE LESSON → UPDATE MEMORY → IMPROVE
```

## Telegram autonomous knowledge cycle

The Telegram control layer includes `TelegramAutonomousKnowledgeRunner`.

When enabled, each cycle:

1. reads the current autonomous state,
2. inspects safe knowledge topics,
3. recalls relevant Second Brain context,
4. detects gaps,
5. records research memories,
6. records lessons,
7. creates follow-up Learning Agent tasks,
8. records an evaluation,
9. rebuilds vault indexes,
10. queues a Telegram summary.

Scheduled GitHub Actions run this every six hours through `GIZMO Telegram Autonomous Learning`. Manual dispatch can run the same loop immediately.
