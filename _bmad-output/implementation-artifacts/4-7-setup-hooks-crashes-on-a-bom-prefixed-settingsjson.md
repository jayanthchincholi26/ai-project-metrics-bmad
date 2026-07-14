---
baseline_commit: 91a250c
---

# Story 4.7: `setup-hooks.py` Crashes on a BOM-Prefixed `settings.json`

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer running `uv run tools/setup-hooks.py --repo-root .` after an uninstall/reinstall cycle,
I want it to tolerate a UTF-8 BOM in `.claude/settings.json`,
so that a file written by PowerShell (which commonly adds a BOM) doesn't hard-block setup with a confusing error.

## Background

Reported live during real pilot testing (2026-07-14): `uv run tools/setup-hooks.py --repo-root .` failed with
`error: ...\.claude\settings.json is not valid JSON (Unexpected UTF-8 BOM (decode using utf-8-sig): line 1 column 1 (char 0))`.

Root cause, confirmed two ways:
1. `tools/setup-hooks.py` read `settings.json` with plain `encoding="utf-8"` — every other file read in this codebase already uses `encoding="utf-8-sig"` for exactly this reason (this is now the fourth BOM bug this project has caught, per existing project memory).
2. `tools/build-release/uninstall.ps1`'s own settings.json rewrite step used `Set-Content -Encoding utf8`, which — confirmed empirically on this machine — writes a real UTF-8 BOM on Windows PowerShell 5.1 (`-Encoding utf8` is BOM-full in 5.1; only `-Encoding utf8NoBOM`, not available in 5.1, is BOM-less). An uninstall→reinstall cycle is exactly the scenario the reporting user was running.

## Acceptance Criteria

1. **Given** `.claude/settings.json` exists with a UTF-8 BOM (regardless of what wrote it)
   **When** `uv run tools/setup-hooks.py --repo-root .` runs
   **Then** it parses successfully (reads with `encoding="utf-8-sig"`, which tolerates a BOM-or-not transparently) — same defensive posture as every other file this codebase reads

2. **Given** `uninstall.ps1` rewrites `settings.json` as part of its surgical hook-entry removal
   **When** it writes the file
   **Then** it writes BOM-less UTF-8 (not `Set-Content -Encoding utf8`, which is BOM-full on PowerShell 5.1) — fixing the actual source of the corruption, not just tolerating it downstream

3. **Given** this is a two-sided fix (defensive read + root-cause write)
   **When** Definition of Done is evaluated
   **Then** a real crash reproduction (a BOM-prefixed `settings.json`, byte-for-byte matching what PowerShell actually writes) is used to prove both the RED state and the GREEN fix — not just reasoning about encodings

## Tasks / Subtasks

- [x] Task 1: fix `setup-hooks.py`'s read (AC 1)
  - [x] Subtask 1.1 (RED): a test writing a real BOM-prefixed `settings.json` (`b"\xef\xbb\xbf" + json.dumps(...).encode()`), asserting `setup-hooks.py` succeeds and preserves existing keys
  - [x] Subtask 1.2 (GREEN): change `settings_path.read_text(encoding="utf-8")` to `encoding="utf-8-sig"`

- [x] Task 2: fix `uninstall.ps1`'s write (AC 2)
  - [x] Subtask 2.1: replace `Set-Content -Encoding utf8` with `[System.IO.File]::WriteAllText(path, json, [System.Text.UTF8Encoding]::new($false))` — BOM-less on both PowerShell 5.1 and 7+

- [x] Task 3: live E2E (AC 3)
  - [x] Subtask 3.1: real scratch repo — installed, ran `setup-hooks.py`, injected an unrelated settings.json key via PowerShell's actual BOM-writing `Set-Content -Encoding utf8` (confirmed via raw byte inspection: `239 187 191` = a real BOM), ran the real `uninstall.ps1`, confirmed the rewritten file has no BOM (byte inspection again), then reinstalled and re-ran `setup-hooks.py` against that BOM-less file to confirm the full round-trip is clean

## Dev Notes

### Scope

- Purely a robustness fix — no change to what `setup-hooks.py` installs, no change to `uninstall.ps1`'s removal logic, no change to any capture behavior.
- Two-sided deliberately: fixing only the read side would leave `uninstall.ps1` still writing a BOM (working around a bug in this project's own tooling rather than fixing it); fixing only the write side wouldn't help a `settings.json` corrupted by some other BOM-writing tool (Notepad, other PowerShell cmdlets, etc.) — both matter.

### Architecture compliance

- No AD/architecture invariant touched. Matches this project's existing established convention (`utf-8-sig` for every file read that might see a BOM) — see `tools/hooks/_events.py`'s `read_stdin_json()` docstring for the prior instances of this exact class of bug.

### Source tree touched

```text
tools/setup-hooks.py               UPDATE  settings.json read: utf-8 -> utf-8-sig
tools/build-release/uninstall.ps1  UPDATE  settings.json write: BOM-less UTF8Encoding
tests/test_setup_hooks.py          UPDATE  new BOM-tolerance test
```

### References

- [Source: tools/hooks/_events.py#read_stdin_json] — this project's established `utf-8-sig` convention and prior BOM bugs
- [Source: tools/build-release/uninstall.ps1] — the write side fixed in the same story

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5

### Debug Log References

RED: reproduced the user's exact error message with a real BOM-prefixed `settings.json` before the fix. GREEN: same test passes after switching to `utf-8-sig`. Full suite: 323 passed (up from 322), `ruff check` clean.

Live E2E: confirmed via direct byte inspection (`[System.IO.File]::ReadAllBytes`) that PowerShell's `Set-Content -Encoding utf8` writes a real BOM (`239 187 191`) on this machine's PowerShell 5.1, that the old `uninstall.ps1` reproduced it, and that the fixed `uninstall.ps1` no longer does — then ran the real `setup-hooks.py` against the round-tripped file to confirm no crash.

### Completion Notes List

- Confirmed this is the 4th instance of a BOM-related bug in this project (per prior project memory) — the general lesson (default to `utf-8-sig` for any file this project didn't just write itself) continues to hold.
- Deliberately fixed both sides rather than just the read (see Dev Notes Scope).

### File List

tools/setup-hooks.py (updated)
tools/build-release/uninstall.ps1 (updated)
tests/test_setup_hooks.py (updated)
