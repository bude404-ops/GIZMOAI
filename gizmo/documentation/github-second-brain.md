# Phase 4 — GitHub Second Brain

Phase 4 makes GIZMO behave like a repo-native second brain on GitHub.

## What it means

The repository becomes the control surface. Issues and PRs are no longer just tickets — they become memory, context, plans, and audit trails.

## Commands

Use these from GitHub issue or PR comments:

```text
/gizmo help
/gizmo status
/gizmo context <topic>
/gizmo remember <lesson>
/gizmo recall <topic>
/gizmo plan <objective>
```

## Implemented

- Repository context indexing.
- Context packs for focused work.
- Comment command router.
- Memory write and recall from commands.
- Task planning from commands.
- GitHub Actions workflow scaffold.
- Markdown responses suitable for issue/PR comments.
- Artifacts for every workflow response.

## Safety

This layer is allowed to read, remember, recall, and plan.
Risky writes remain controlled by the approval/policy engine.

## GitHub Actions flow

1. Owner comments `/gizmo ...` on an issue or PR.
2. GitHub Actions checks out the repo.
3. GIZMO routes the command.
4. GIZMO emits JSON and markdown artifacts.
5. The workflow posts the markdown back to the thread.

## Why this is the second brain

- Context lives close to code.
- Decisions happen where work happens.
- Lessons are stored and recalled by topic.
- Plans become traceable tasks.
- Approvals and gates stay visible.
