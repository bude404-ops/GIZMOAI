# Phase 3 — Approval + Policy Engine

Phase 3 adds human-control gates around risky GIZMO actions.

## Implemented

- Per-project operating modes.
- Approval request records.
- Approval codes for explicit human decisions.
- Action risk classification.
- Merge gates.
- Deploy gates.
- Pending approval listing.
- Policy status export.
- CLI command: `policy-demo`.

## Protected actions

These actions require approval by default:

- `github_write`
- `merge`
- `deploy`
- `external_write`
- `delete_repo`
- `force_push`
- `modify_secrets`
- `change_owner_permissions`

## Merge gate

Required checks:

- tests
- secret scan
- review

If all pass, GIZMO still requests human approval before merge.

## Deploy gate

Required checks:

- tests
- secret scan
- security review
- quality review

If all pass, GIZMO still requests human approval before deployment.

## Operating modes

- Manual: non-routine actions request approval.
- Assisted: routine work can proceed; high-risk actions request approval.
- Autonomous: future mode for approved categories only.
- Emergency: all autonomous work is blocked.

## CLI

```bash
python -m gizmo.core.cli policy-demo --workspace .gizmo_runtime
python -m gizmo.core.cli status --workspace .gizmo_runtime
```
