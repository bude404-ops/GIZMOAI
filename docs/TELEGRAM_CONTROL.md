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

## Plain English Telegram controls

Slash commands are no longer required for the common operator flow. The router accepts short English phrases and maps them to the same secured handlers.

Examples:

- `status` → GIZMO status
- `help` or `commands` → help menu
- `agents` → agent registry
- `tasks` → task list
- `logs` → latest logs
- `what did you learn?` → autonomous learning memory search
- `begin learning` or `learn now` → run one autonomous knowledge cycle
- `turn on learning` → approval-gated autonomous enable
- `turn off learning` → disable autonomous mode
- `remember that <text>` → safe explicit memory write
- `search memory for <query>` → Second Brain search
- `build <thing>` → create a GIZMO task

Sensitive English phrases still hit the same gates. `turn on learning`, `deploy ...`, `release ...`, `stop`, and `stop everything` remain approval/safety-bound.

## Live Telegram responder

Telegram command handling now uses a live long-poll responder instead of relying on a single scheduled check. The responder stays awake for a controlled window, renews on schedule, replies to authorized admin messages, and acknowledges processed updates.

Expected behavior: simple English terms such as `status`, `begin learning`, and `what did you learn?` should be answered by the bot without Reaper manually dispatching a workflow.

## Cloud brain swarm controls

The Telegram bot can now start the stronger cloud brain loop with plain English:

```text
become smarter
start working
start cloud brain
run the agents
make yourself smarter
```

This enables the cloud brain state, runs the specialist swarm, records public non-secret knowledge into the Second Brain, rebuilds vault indexes, and persists a cloud snapshot for future runs.

## Super Brain controls

GIZMO now has three upgraded organs inside each cloud brain cycle:

- Brain: model-backed reasoning with safe local fallback.
- Memory: durable semantic search manifest and query log.
- Body: always-on agent execution, scoring, and next-action queue.

Use Telegram:

```text
activate super ai
run super brain
start super brain
status
```

## Universal knowledge and app creation

GIZMO is no longer limited to market knowledge. It can ingest public/general knowledge from any domain, store it in the Second Brain, and turn the strongest patterns into app blueprints.

Use Telegram:

```text
learn anything
learn about cooking meal prep apps
learn about language learning
create app ideas
create app ideas from language learning
app factory
```

Each Super Brain cloud cycle now runs universal ingestion and an app factory before agent execution.

## Autonomous thinking controls

GIZMO can now run an internal ideation loop. It asks self-improvement questions, searches its own memory, reviews app backlog and body scorecards, generates ideas, ranks upgrade proposals, and stores chosen next actions.

Use Telegram:

```text
think for yourself
generate your own ideas
find your own upgrades
decide what to build next
```

The Super Brain cloud cycle runs this thinker automatically after universal knowledge ingestion and app blueprint generation.

## Safe prototype controls

GIZMO can now turn its chosen ideas and app blueprints into real Mini App prototype files. These drafts are stored for review and are not published automatically.

Use Telegram:

```text
prototype your best idea
prototype best idea
make prototypes
create prototypes
```

The full Super Brain cycle now runs: universal learning → app factory → autonomous thinking → safe prototype generation → body execution → storage snapshot.

## Obsidian-style cloud memory vault

GIZMO now keeps a self-managed Markdown memory vault in cloud storage. Every Super Brain cycle rebuilds note indexes, graph files, backlinks, quality reports, a manifest, and a portable archive. The archive is restore-ready and can be opened in Obsidian-compatible tools after extraction.

Use Telegram:

```text
sync memory vault
cloud memory vault
obsidian vault
```
