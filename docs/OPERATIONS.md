# Operations

## Start local Telegram simulation

```bash
python -m gizmo.core.cli telegram-demo --workspace .gizmo_runtime/telegram --user-id 101 --chat-id 201 --text "/status"
```

## Test complete local control loop

```bash
python -m gizmo.core.cli telegram-demo --workspace .gizmo_runtime/telegram --user-id 101 --chat-id 201 --text "Build me a new autonomous research agent that learns from previous research."
```

Expected path:

```text
Telegram text
 ↓
Authorization
 ↓
Intent detection
 ↓
Structured Telegram task
 ↓
Reaper control layer
 ↓
Gizmo task
 ↓
Agent selection
 ↓
GitHub workflow dispatch plan
 ↓
Notification queued
```

## Logs

Use `/logs latest` for concise summaries. Detailed records remain in structured audit logs and task result records.

## Troubleshooting

- Missing Telegram token: bot cannot poll real Telegram, but local simulation still works.
- Missing admin ID: runtime is not production-ready until allowlist is configured.
- GitHub write blocked: provide least-privilege GitHub App credentials or token and satisfy approval policy.
- Deployment blocked: approve the exact approval ID and code.

## Run autonomous Telegram knowledge cycle

Local enabled run:

```bash
python -m gizmo.core.cli telegram-autonomous-cycle --workspace .gizmo_runtime/telegram-auto --chat-id 7257834686 --text on
```

Telegram command after approval:

```text
/learn autonomous cycle
```

GitHub workflow:

- `GIZMO Telegram Autonomous Learning`
- schedule: every six hours
- manual dispatch input: `enable=true`

The workflow sends a short Telegram summary when Telegram secrets are present.

## Telegram command poller

Manual one-shot command processing:

```bash
python -m gizmo.core.cli telegram-poll-once --workspace .gizmo_runtime/telegram-poller
```

GitHub workflow:

- `GIZMO Telegram Command Poller`
- schedule: every five minutes
- action: polls Telegram once, routes pending updates, sends replies, acknowledges processed updates

This is the path that makes `/status` and `/memory` visible inside the Telegram bot.

## Plain English Telegram checks

After deployment, verify these from Telegram without slashes:

```text
status
what did you learn?
begin learning
agents
tasks
remember that Telegram should answer simple English terms
search memory for simple English terms
```

The poller treats these exactly like slash commands after admin authorization.

## Telegram live responder verification

The Telegram responder workflow should normally be running or recently renewed. If Telegram appears silent, dispatch `GIZMO Telegram Live Responder` once and then check that the `Keep Telegram responder online` step is in progress or completed successfully.

## 24-7 cloud brain storage

`GIZMO Cloud Brain 24-7` restores `.gizmo_cloud_brain` from workflow cache, runs the multi-agent cloud brain cycle, saves the updated storage back to cache, and uploads audit artifacts. The live responder handles Telegram commands; the cloud brain workflow handles recurring learning and storage.

Operator checks:

```text
status
become smarter
what did you learn?
```

## Super Brain organs

The cloud brain cycle now runs model-backed reasoning, semantic memory indexing, and an always-on agent body. Artifacts include cloud snapshots, semantic index reports, body scorecards, and queued next actions. If no external model key is configured, local synthesis keeps the cycle safe and testable while recording that stronger model access is a next action.

## Universal app-builder loop

The general intelligence loop is: ingest public/domain knowledge, preserve it as searchable memory, extract app opportunities, generate app blueprints, queue safe build steps, then let the agent body score and execute allowed work. The system remains approval-gated for external side effects and never stores secrets.

## Autonomous thinker

Every full Super Brain cycle now includes a self-questioning pass. The thinker reads recent cloud state, app blueprints, body next-actions, scorecards, and semantic memories. It produces ranked ideas, upgrade proposals, and chosen next actions. Safe items enter the queue; risky items remain approval-gated.
