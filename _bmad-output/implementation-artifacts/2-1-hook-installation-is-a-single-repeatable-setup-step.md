---
baseline_commit: 15b23cb2034e12def039d79b2e99263078d15222
---

# Story 2.1: Hook Installation Is a Single Repeatable Setup Step

Status: review

## Story

As a developer joining the project,
I want one command to install all capture hooks,
so that my activity is captured identically to everyone else's on the team.

## Acceptance Criteria

1. **Given** a fresh clone of the repository, **when** the developer runs `tools/setup-hooks`, **then** it installs git hooks into `.git/hooks/` and merges the required entries into `.claude/settings.json` (AD-8).
2. Hook logic lives in git-tracked `tools/hooks/`, never hand-maintained per machine — the installer only ever copies/wires what the repo tracks.

## Tasks / Subtasks

- [x] Task 1: Tracked hook sources under `tools/hooks/` (AC: 2)
  - [x] `tools/hooks/git/`: 4 shims (`post-commit.sh`, `post-checkout.sh`, `post-merge.sh`, `commit-msg.sh`) — `#!/bin/sh`, marker line, `uv run tools/hooks/git/<name>.py "$@"` (git runs hooks from the repo top-level; git requires a directly executable file, hence shims — spine Stack)
  - [x] `tools/hooks/git/`: 4 placeholder Python hooks (`post-commit.py` etc.) — PEP 723 header, docstring "event emission lands in Story 2.2 (AD-1)", `main(argv) -> 0`
  - [x] `tools/hooks/claude/`: 6 placeholder Python hooks (`session_start.py`, `session_end.py`, `pre_tool_use.py`, `post_tool_use.py`, `stop.py`, `user_prompt_submit.py`) — same shape, "Story 2.3 (AD-10)"; placeholders exit 0 so wired hooks never break a session before their story lands
- [x] Task 2: The installer `tools/setup-hooks.py` (AC: 1, 2)
  - [x] CLI: `--repo-root DIR` (required); validate `.git/` exists (exit 2 otherwise) and `tools/hooks/` sources exist
  - [x] Install git shims: copy each `tools/hooks/git/<name>.sh` → `.git/hooks/<name>` (extensionless), `chmod 0o755`, atomic write
  - [x] Conflict safety: target exists **without** our marker → collect and exit 2 listing conflicting hooks, touching nothing; **with** marker → upgrade in place (idempotent re-install)
  - [x] Merge `.claude/settings.json`: create if absent; parse existing (malformed JSON → exit 2, never clobber); ensure `hooks.<Event>` entries exist for the 6 events with command `uv run tools/hooks/claude/<script>.py`; skip events already carrying our exact command (idempotent); preserve every unrelated key and any user-added hook entries; atomic write
  - [x] Ack: one JSON line `{"ok": true, "git_hooks": [...], "settings": "<path>", "events_wired": [...]}`, exit 0
- [x] Task 3: CI per §11 — Epic 2 implementation starts now (process requirement)
  - [x] `.github/workflows/ci.yml`: on `pull_request` + push to `develop`/`main`; `astral-sh/setup-uv` → `uv run ruff check .` + `uv run ruff format --check tools tests` + `uv run pytest -q`
- [x] Task 4: Tests `tests/test_setup_hooks.py` (AC: 1, 2)
  - [x] Fake repo fixture: `tmp_path` with a hand-made `.git/hooks/` dir and a copy of (or path to) the real `tools/hooks/` sources — no real git operations (§5)
  - [x] Fresh install: 4 extensionless hooks appear with shim content + marker; settings.json created with all 6 events; ack lists both; exit 0
  - [x] Idempotency: second run → exit 0, no duplicate settings entries, hook files unchanged
  - [x] Foreign hook present (no marker) → exit 2, file byte-identical, error names the conflicting hook(s), settings untouched
  - [x] Ours present (marker) → upgraded without error
  - [x] Existing settings.json with unrelated keys + a user hook entry → preserved verbatim alongside ours
  - [x] Malformed settings.json → exit 2, file untouched
  - [x] Missing `.git/` → exit 2
  - [x] Placeholder hooks: each of the 10 scripts' `main()` returns 0
- [x] Task 5: Full regression + lint (all ACs)

### Review Follow-ups (AI)

External LLM review (Gemini, via PR #10) triaged per project-context §9 — 2026-07-10:

- [x] [AI-Review][Low] Conflict scan could crash on a directory named like a hook (`.exists()` + `.read_text()`) — applied a **stronger variant** than suggested: `.is_file()` alone would have skipped the directory in detection and crashed later at `os.replace`; instead, any non-file target is itself a conflict (refused with exit 2). Regression test added (`test_directory_named_like_a_hook_is_a_conflict_not_a_crash`).
- Zero defects reported; reviewer highlighted atomic writes, the `newline="\n"` CRLF-proofing of sh shebangs, and foreign-hook refusal.

## Dev Notes

- **Scope:** installation infrastructure only. NO event emission, NO `.story-events.jsonl` writes, NO retry logic (AD-9 binds emission, Story 2.2/2.3), NO `.gitignore` changes yet (event-log ignores land with 2.2 when the file first gets written).
- **AD-8 is the contract:** hook logic tracked in `tools/hooks/`; one committed installer wires `.git/hooks/` + `.claude/settings.json`; runs once per clone; nothing hand-maintained per machine. Idempotency is what makes "runs once per clone" forgiving.
- **settings.json shape:** `{"hooks": {"<Event>": [{"hooks": [{"type": "command", "command": "uv run tools/hooks/claude/<script>.py"}]}]}}` — merge additively; our-command-presence is the dedup key. The 6 events are exactly the spine Stack's list; `SubagentStop`/`PreCompact`/`Notification` are explicitly out of scope.
- **Never trust / never clobber (§3, §4):** malformed settings.json and foreign hooks both refuse loudly. All writes atomic (memlog `write_atomic` pattern, already used in 3 scripts).
- **Windows note:** `chmod` is a no-op on Windows but required for POSIX teammates; git-for-Windows runs `#!/bin/sh` shims via its bundled sh. `os.chmod(path, 0o755)` after the atomic replace.
- **Dogfooding caution:** do NOT run the installer against this repo during dev (placeholders are harmless but keep the working tree clean); E2E runs against a scratch dir with a hand-made `.git/`.
- **Previous story intelligence (Epic 1):** `main(argv)`/`fail()`/one-line-ack/exit-0-2 patterns; f-strings; exact hints; validate-before-write; grep-verify hallucinated review findings; ruff format before finishing. The Epic 1 retro flagged Issue #7 (shared parser) — this story needs no config parsing, so it stays moot.
- **CI (§11):** deliberately part of this story ("add at the point Epic 2 implementation starts"). Keep the workflow minimal — no caching tuning, no matrix; pin action majors.
- **Process:** branch `story/2.1-hook-installation` (the §8 example, verbatim); PR `Story 2.1: Hook Installation Is a Single Repeatable Setup Step` linking FR1-enabling (CAP-1), AD-8, §11 CI; squash-merge; epics annotation inside PR; metrics entry provisional→final; epic-2 flips in-progress with this story.

### References

- [epics.md § Story 2.1](../planning-artifacts/epics.md) (lines 169–181) · [ARCHITECTURE-SPINE.md § AD-8 + Stack + Structural Seed](../planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md) · [project-context.md](../../project-context.md) §2 atomic writes, §3 ack/exit, §5–6 testing (no real git in unit tests), §11 CI trigger · [_bmad/scripts/memlog.py](../../_bmad/scripts/memlog.py) + Epic 1 adapters (pattern sources)

## Dev Agent Record

### Agent Model Used

claude-fable-5 (create-story context engineering + dev-story implementation)

### Debug Log References

- RED: collection error, `tools/setup-hooks.py` absent (11 tests authored first)
- GREEN: 98/98 (was 87); ruff check/format clean
- Scratch E2E (hand-made `.git/`, no real git ops): fresh install → ack lists 4 git hooks + 6 events, exit 0; immediate re-run → exit 0, no duplicates

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created
- `tools/setup-hooks.py`: validates everything before writing anything (no partial installs) — `.git/` presence, all 4 tracked shim sources, foreign-hook conflicts (marker-based; refuses with exit 2 listing names), settings.json parseability (malformed → refuse, never clobber). Then: shims copied to extensionless `.git/hooks/<name>` atomically + `chmod 0o755`; `.claude/settings.json` merged additively (our-command-presence is the dedup key; user keys and user hook entries preserved verbatim); one JSON ack.
- `tools/hooks/git/`: 4 `#!/bin/sh` shims (marker line + `uv run tools/hooks/git/<name>.py "$@"`) + 4 PEP 723 placeholder hooks (exit 0; emission is Story 2.2). `tools/hooks/claude/`: 6 placeholders (Story 2.3). Placeholders mean wired hooks never break a git flow or Claude session before their story lands.
- `.github/workflows/ci.yml` added per §11's "at the point Epic 2 implementation starts": ruff check + format check + pytest on every PR and on pushes to develop/main.
- AC→test traceability: AC 1 → fresh-install (hooks + settings + ack), idempotency, conflict/malformed/missing-git refusal tests; AC 2 → installed-content-equals-tracked-source assertion + placeholder-exit-0 sweep (all 10 scripts).
- Epic 2 now in-progress (first story).

### Change Log

- 2026-07-10: Story 2.1 implemented — setup-hooks installer (marker safety, additive settings merge, atomic writes), 14 tracked hook files, CI workflow. 11 new tests (98 total). Status → review.
- 2026-07-10: Addressed Gemini review of PR #10 — 1 applied with a stronger variant (directory-as-conflict instead of bare `.is_file()`, which would have deferred the crash to write time). 99 tests passing.

### File List

- tools/setup-hooks.py (new)
- tools/hooks/git/post-commit.sh, post-checkout.sh, post-merge.sh, commit-msg.sh (new — shims)
- tools/hooks/git/post-commit.py, post-checkout.py, post-merge.py, commit-msg.py (new — Story 2.2 placeholders)
- tools/hooks/claude/session_start.py, session_end.py, pre_tool_use.py, post_tool_use.py, stop.py, user_prompt_submit.py (new — Story 2.3 placeholders)
- .github/workflows/ci.yml (new — §11 CI)
- tests/test_setup_hooks.py (new)
- _bmad-output/implementation-artifacts/2-1-hook-installation-is-a-single-repeatable-setup-step.md (modified — this story file)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — epic-2 + story transitions)
- _bmad-output/planning-artifacts/epics.md (modified — §12 annotation, inside PR)
