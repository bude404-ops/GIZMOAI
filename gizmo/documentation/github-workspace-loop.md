# Phase 1 — GitHub Workspace Loop

Phase 1 connects GIZMO's task system to a branch-per-task GitHub engineering workflow.

## Implemented

- Repository inspection through local git metadata.
- GitHub owner/repo parsing.
- GIZMO workspace task creation.
- Safe branch name generation from task IDs and objectives.
- Branch-per-task workflow runner.
- Pull request plan artifacts.
- Required checks attached to each PR plan.
- Human-reviewed merge policy text.
- Audit logging for inspect/task/branch/PR/review events.
- Memory lessons for reusable GitHub workflow behavior.
- CLI command: `github-demo`.

## Safety boundary

The Phase 1 loop can create local branches only when policy allows it. By default, the demo uses `execute_git=False`, which means it creates an auditable task and PR plan without changing the current branch.

Real network PR creation is intentionally not enabled yet. The system prepares a PR plan that a later GitHub adapter can submit once credential handling and approval gates are in place.

## Flow

1. Inspect repository.
2. Create GIZMO task.
3. Retrieve related memory.
4. Generate isolated branch name.
5. Create branch workspace or wait for approval.
6. Create PR plan artifact.
7. Require checks:
   - `python -m pytest -q`
   - `python scripts/scan_secrets.py`
8. Review task result.
9. Store lesson to memory.
10. Expose machine-readable status.

## CLI

```bash
python -m gizmo.core.cli github-demo --workspace .gizmo_runtime
python -m gizmo.core.cli status --workspace .gizmo_runtime
```

## Next expansion

Add real GitHub API adapters for issues and PRs using environment-provided credentials, plus approval-gated push/PR creation.
