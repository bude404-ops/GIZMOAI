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
