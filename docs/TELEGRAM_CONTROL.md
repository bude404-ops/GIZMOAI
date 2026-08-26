# Telegram Control Center

Telegram is the human control interface for Gizmo.

```text
Telegram
   ↓
TelegramCommandRouter
   ↓
Authorization + intent detection
   ↓
TelegramControlLayer
   ↓
Reaper / GizmoOrchestrator
   ↓
Agent Orchestrator
   ↓
Registered Agents
   ↓
GitHub Actions / GitHub API
   ↓
Second Brain / Logs / Artifacts
   ↓
Telegram notifications
```

## Commands

- `/start`
- `/help`
- `/status`
- `/agents`
- `/projects`
- `/tasks`
- `/task <task_id>`
- `/run <objective>`
- `/stop`
- `/pause`
- `/resume`
- `/autonomous on|off`
- `/learn <topic>`
- `/memory <query>`
- `/remember <safe memory>`
- `/logs latest|task <id>|agent <id>`
- `/build <objective>`
- `/test <objective>`
- `/deploy <objective>`
- `/approve <approval_id> <approval_code>`
- `/deny <approval_id> <approval_code>`
- `/restart`

Natural language is supported. Example:

```text
Build me a new autonomous research agent that learns from previous research.
```

The router converts the message into a structured task envelope before Reaper receives it.

## Runtime secrets

Required:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ADMIN_ID`
- `GITHUB_REPOSITORY`
- `REAPER_AUTH_SECRET`

Optional:

- `GITHUB_APP_ID`
- `GITHUB_PRIVATE_KEY`
- `GITHUB_TOKEN`
- `REAPER_ENDPOINT`
- `GIZMO_NOTIFICATION_MIN_PRIORITY`
- `GIZMO_DAILY_REPORT`

Secrets are read from environment variables or GitHub Secrets. They are not committed.

## Local simulation

```bash
python -m gizmo.core.cli telegram-demo --user-id 101 --chat-id 201 --text "/status"
python -m gizmo.core.cli telegram-demo --user-id 101 --chat-id 201 --text "Build me a new autonomous research agent that learns from previous research."
```

## GitHub workflow path

Telegram build/test requests create a Gizmo task and a planned GitHub workflow dispatch. Real execution is enabled only when credentials and policy allow it.
