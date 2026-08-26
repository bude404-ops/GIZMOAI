# Security

## Authorization

Every Telegram command follows:

```text
Telegram User ID
 ↓
Allowlist authorization
 ↓
Intent detection
 ↓
Command validation
 ↓
Execution or approval request
```

Unauthorized users receive a generic denial.

## Sensitive operations

The following require approval or are policy gated:

- production deploys
- destructive deletion
- database migrations
- security permission changes
- GitHub authentication changes
- external communications
- spending money
- irreversible actions
- enabling autonomous mode
- restart
- emergency controls

Approvals are tied to unique approval IDs and approval codes. Generic approval is not accepted.

## Secret handling

Never store secrets in memory. Telegram `/remember` rejects secret-like text. Telegram responses are sanitized before delivery.

Required secrets remain in environment variables or GitHub Secrets.

## GitHub least privilege

Prefer GitHub App credentials where practical. Workflow permissions are minimal by default and expanded only where required.

## Audit checks

Before release run:

```bash
python -m pytest -q
python scripts/scan_secrets.py
```
