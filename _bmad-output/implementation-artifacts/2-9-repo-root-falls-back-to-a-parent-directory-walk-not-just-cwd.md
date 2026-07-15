---
baseline_commit: 00328db
---

# Story 2.9: `repo_root()` Falls Back to a Parent-Directory Walk, Not Just Cwd

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want event capture to still find the correct repo root even in the rare case `git rev-parse --show-toplevel` itself fails,
so that a transient git/subprocess failure never silently writes capture files into the wrong (possibly nested) directory.

## Background

Split out from PR #22's review (2026-07-11) — a real, valid hardening suggestion about `tools/hooks/_events.py`, a file Story 2.7 never touched. `repo_root()` fell back straight to `Path.cwd()` whenever `git rev-parse --show-toplevel` failed for any reason (git unavailable, transient subprocess failure, OS-level limits) — this story adds a smarter intermediate step.

## Acceptance Criteria

1. **Given** `git_out("rev-parse", "--show-toplevel")` returns `None`
   **When** `repo_root()` is called from a subdirectory of the actual repo
   **Then** it walks up from cwd looking for a `.git` directory-**or-file** (worktrees/submodules use a file, same `-e` not `-d` precedent as `install.sh`'s own fix) and returns that parent
2. **Given** no `.git` is found anywhere in the parent chain
   **When** `repo_root()` is called
   **Then** it falls back to `Path.cwd()` exactly as before — this story only adds a smarter intermediate step, not a new failure mode

## Tasks / Subtasks

- [x] Task 1: implement the parent-directory walk (AC 1, 2)
  - [x] Subtask 1.1: `repo_root()` walks `(Path.cwd(), *Path.cwd().parents)` looking for `.git` via `.exists()` (covers both directory and file forms) before falling back to bare cwd
- [x] Task 2: verify
  - [x] Subtask 2.1: real-filesystem tests (real `tmp_path` directories/`.git` markers, real `monkeypatch.chdir`) covering: walks up correctly when `git_out` fails, accepts a `.git` file not just a directory, falls back to cwd when no `.git` exists anywhere, and still prefers a successful `git_out` result over the walk

## Dev Notes

### Scope

Single-function change in `tools/hooks/_events.py`, shared by every hook (git + Claude Code families) that calls `repo_root()`. No caller-side changes needed.

### Source tree touched

```text
tools/hooks/_events.py           UPDATE  repo_root() parent-directory walk
tests/hooks/test_git_hooks.py    UPDATE  4 new tests against the real function (not monkeypatched away)
```

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5

### Debug Log References

`tests/hooks/test_git_hooks.py`: 25 passed (up from 21). Full suite: 337 passed. `ruff check`/`ruff format --check` clean.

### Completion Notes List

- Tests exercise the real `repo_root()` function directly against a real filesystem (unlike most other tests in this suite, which monkeypatch `repo_root` away entirely) — this is the one function where that would defeat the point of the test.

### File List

tools/hooks/_events.py (updated)
tests/hooks/test_git_hooks.py (updated)
