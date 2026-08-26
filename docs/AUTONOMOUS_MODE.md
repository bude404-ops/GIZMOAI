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
