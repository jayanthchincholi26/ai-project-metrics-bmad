# Bugs

> **Superseded — real bug tracking moved to GitHub Issues.** This folder's
> markdown-file convention below was early planning-phase scaffolding; it was
> never actually adopted (`api-bugs/`, `ui-bugs/` have stayed empty since this
> repo's initial commit). Every real bug found once implementation started —
> including everything found via live pilot testing (e.g.
> [GitHub Issue #52](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/issues/52),
> Story 6.8's close-command reliability gap) — is filed as a GitHub Issue on
> `jayanthchincholi26/ai-project-metrics-bmad`, titled `Bug: {short description}`,
> labeled `bug`, per `project-context.md` §14. This file is kept for historical
> context only, not as a description of current practice.

All bugs captured during OpenSpec SDD development lifecycle.

## Folder Structure

```
bugs/
  ui-bugs/
    unit-level-bugs/     ← compile / build / unit-test bugs found during frontend story implementation
    review-bugs/         ← defects raised by LLM PR reviewer on frontend stories
  api-bugs/
    unit-level-bugs/     ← compile / build / unit-test bugs found during backend story implementation
    review-bugs/         ← defects raised by LLM PR reviewer on backend stories
```

## File Naming

`story-{N}.{M}-{short-name}-{type}-bugs.md`

Examples:
- `story-1.1-registration-api-unit-bugs.md`
- `story-1.2-registration-ui-review-bugs.md`

## Bug Lifecycle

```
Story implemented
      │
      ▼
Unit tests run → bugs found → log to unit-level-bugs/
      │
      ▼
Bugs fixed → feature branch pushed → PR raised
      │
      ▼
Second LLM reviews PR → review defects found → log to review-bugs/
      │
      ▼
Review defects fixed → PR approved → merged to main
```

## Severity

| Level | Meaning |
|-------|---------|
| **S1 — Critical** | Blocks the story; app crashes or core flow broken |
| **S2 — High** | Feature doesn't work correctly; fails AC |
| **S3 — Medium** | Feature partially works; edge case failure |
| **S4 — Low** | Minor UI issue, cosmetic, or non-blocking |

## Complexity

| Level | Meaning |
|-------|---------|
| **C1 — Simple** | Fix is obvious; one line or config change |
| **C2 — Moderate** | Fix requires understanding the context; 1–3 files |
| **C3 — Complex** | Fix touches multiple files or requires design decision |
