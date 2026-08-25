# Phase 2 — GitHub API Adapter

Phase 2 adds a real GitHub REST adapter while keeping all network writes approval-gated.

## Implemented

- Environment-based credential detection via `GITHUB_TOKEN`.
- Issue creation action planning.
- Pull request opening action planning.
- Workflow run status read action support.
- Issue status comment sync action planning.
- API action artifacts.
- Audit logging for every GitHub API action.
- Redaction of credential values from stored API results.
- CLI command: `github-api-demo`.

## Safety boundary

Write actions are not silently executed.

An action can only execute when:

1. The caller passes `execute=True`.
2. Security policy does not require approval for the action.
3. `GITHUB_TOKEN` is present in the environment.

Otherwise GIZMO records one of these statuses:

- `PLANNED_NOT_EXECUTED`
- `WAITING_FOR_APPROVAL`
- `BLOCKED_NO_CREDENTIAL`

## Supported actions

- `create_issue`
- `open_pull_request`
- `read_workflow_runs`
- `sync_issue_status`

## CLI

```bash
python -m gizmo.core.cli github-api-demo --workspace .gizmo_runtime
python -m gizmo.core.cli status --workspace .gizmo_runtime
```

## Next expansion

Add approval tokens/policies, live issue sync, PR creation after push, CI ingestion, and merge gates.
