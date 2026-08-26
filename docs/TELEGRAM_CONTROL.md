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
- `/learn autonomous cycle`
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

Required secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ADMIN_ID`
- `REAPER_AUTH_SECRET`

Required runtime environment:

- `GITHUB_REPOSITORY` — supplied automatically by GitHub Actions; set manually only outside Actions.

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

## Autonomous Telegram knowledge mode

Telegram can now trigger and monitor a safe autonomous knowledge cycle.

- `/autonomous on` requests approval to enable permission-bound autonomous mode.
- `/learn autonomous cycle` runs one knowledge enhancement pass when autonomous mode is enabled.
- Scheduled GitHub workflow `telegram-autonomous-learning.yml` runs the same cycle every six hours.
- `/status` reports the latest knowledge cycle state.

The cycle creates structured Second Brain research, lessons, evaluations, follow-up learning tasks, vault indexes, and a Telegram-ready summary. It does not store secrets or bypass approval gates.

## Viewing GIZMO from Telegram

Open the bot and send `/status`, `/memory autonomous learning`, `/tasks`, or `/agents`.

Inbound command replies are handled by `GIZMO Telegram Command Poller`, which runs every five minutes and can also be manually dispatched. The poller reads pending Telegram updates, routes only allowlisted admin commands, sends the result back to the same chat, and acknowledges the processed update offset.
