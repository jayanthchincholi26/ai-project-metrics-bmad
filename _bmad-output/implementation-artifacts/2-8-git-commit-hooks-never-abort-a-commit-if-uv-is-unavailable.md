---
baseline_commit: 00328db
---

# Story 2.8: Git Commit Hooks Never Abort a Commit if `uv` Is Unavailable

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want a commit to never be blocked just because my git client's environment can't find `uv`,
so that a minimal-PATH environment (some GUI git clients: VS Code's built-in git, SourceTree, GitHub Desktop) never silently breaks my ability to commit.

## Background

Split out from PR #22's review (2026-07-11) — a real, valid finding about `tools/hooks/git/commit-msg.sh`, a file Story 2.7 never touched. `commit-msg.py` is deliberately written to always exit 0, but that guarantee only holds once Python is actually running — the shell wrapper invokes it via bare `uv run ...`, and if `uv` itself isn't on the invoking process's PATH, the **shell** fails before Python ever starts (typically exit 127), which git treats as a real abort signal for the `commit-msg` hook specifically.

## Acceptance Criteria

1. **Given** `uv` is not available on the PATH of the process invoking git
   **When** a commit is made
   **Then** `commit-msg.sh` does not abort the commit — checks for `uv` first, prints a visible warning if missing (AD-9), and unconditionally exits 0 regardless of what happened
2. **Given** this fix
   **When** the existing `post-commit`/`post-checkout`/`post-merge` shims are reviewed
   **Then** the same `uv`-availability guard is applied for consistent, clearer messaging — even though git already ignores their exit codes (confirmed via `_events.py`'s own documented exit-code table: "git post-commit/post-checkout/post-merge → 1 on final failure — git ignores post-hook exits"), so a missing `uv` was never actually able to block anything for these three; the guard here only replaces a raw "command not found" line with a clear one

## Tasks / Subtasks

- [x] Task 1: fix `commit-msg.sh` (AC 1)
  - [x] Subtask 1.1: `command -v uv` guard, visible stderr warning on miss, unconditional `exit 0`
- [x] Task 2: apply the consistent guard to the other three shims (AC 2)
  - [x] Subtask 2.1: `post-commit.sh`/`post-checkout.sh`/`post-merge.sh` get the same `command -v uv` check + warning (no forced `exit 0` needed — git already ignores their exit code)
- [x] Task 3: verify
  - [x] Subtask 3.1: new regression tests confirming every git hook shim contains the guard, and that `commit-msg.sh` specifically ends in an unconditional `exit 0`
  - [x] Subtask 3.2: real live E2E — a real scratch git repo, real hooks installed via `setup-hooks.py`, a real `git commit` run with `uv` stripped from `PATH` — confirmed the commit succeeded (exit 0) with visible warnings from both `commit-msg` and `post-commit`, not blocked

## Dev Notes

### Scope

Shell-script-only fix — no Python changes. `tools/hooks/git/*.sh` are the actual tracked source of truth (`setup-hooks.py` copies their text verbatim into `.git/hooks/`), so editing them directly is correct — no template/generation logic to also update.

### Source tree touched

```text
tools/hooks/git/commit-msg.sh       UPDATE  uv-availability guard + unconditional exit 0
tools/hooks/git/post-commit.sh      UPDATE  uv-availability guard (visibility only)
tools/hooks/git/post-checkout.sh    UPDATE  uv-availability guard (visibility only)
tools/hooks/git/post-merge.sh       UPDATE  uv-availability guard (visibility only)
tests/test_setup_hooks.py           UPDATE  2 new regression tests
```

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5

### Debug Log References

`tests/test_setup_hooks.py`: 29 passed (up from 27). Full suite: 337 passed. `ruff check`/`ruff format --check` clean (shell scripts, not linted by ruff). Live E2E: real scratch repo, real `setup-hooks.py` install, real `git commit` with `uv` removed from `PATH` via a filtered `PATH` — commit succeeded with visible warnings, confirming the fix.

### Completion Notes List

- Confirmed via `_events.py`'s own documented exit-code table that `post-commit`/`post-checkout`/`post-merge` were never actually at risk of blocking anything (git ignores their exit codes) — applied the same guard to them anyway, for consistent UX (a clear warning instead of a raw shell error), not because they needed it for correctness.

### File List

tools/hooks/git/commit-msg.sh (updated)
tools/hooks/git/post-commit.sh (updated)
tools/hooks/git/post-checkout.sh (updated)
tools/hooks/git/post-merge.sh (updated)
tests/test_setup_hooks.py (updated)
