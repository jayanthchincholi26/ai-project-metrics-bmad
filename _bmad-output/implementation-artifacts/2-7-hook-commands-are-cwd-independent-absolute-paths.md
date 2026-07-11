---
baseline_commit: 28b3f5761ac123f41e31abc7178f5bbde5c9f81e
---

# Story 2.7: Hook Commands Are Cwd-Independent (Absolute Paths)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want the capture hooks to keep working no matter which directory I `cd` into during a session,
so that a normal workflow (building/testing a subproject) never permanently breaks metrics capture — or my whole session.

## Acceptance Criteria

1. **Given** a repo where `tools/setup-hooks.py --repo-root <path>` has been run
   **When** `.claude/settings.json` is inspected
   **Then** every one of the six Claude hook commands (`SessionStart`, `SessionEnd`, `PreToolUse`, `PostToolUse`, `Stop`, `UserPromptSubmit`) is an **absolute path** to its script (resolved from `--repo-root` at install time), never a bare relative path

2. **Given** a live Claude Code session with hooks installed this way
   **When** the developer `cd`s into any subdirectory (or a subproject entirely) and continues working
   **Then** every hook continues to spawn and fire correctly — no `Failed to spawn` error, regardless of the session's current working directory at the moment a hook fires

3. **Given** an existing installation from before this fix (relative paths already in `.claude/settings.json`)
   **When** the developer re-runs `uv run tools/setup-hooks.py --repo-root .`
   **Then** the installer detects and upgrades the stale relative-path entries to absolute paths **in place** — not as a duplicate second entry alongside the old one

4. **Given** the git hook shims (`post-commit`, `post-checkout`, `post-merge`, `commit-msg`)
   **When** this story is implemented
   **Then** confirm whether they share this vulnerability or are protected by git's own guarantee that hooks always run with cwd at the repo root — **fix only if actually vulnerable; do not touch what isn't broken**

## Tasks / Subtasks

- [x] Task 1: Make `command_for()` produce an absolute, repo-root-resolved path (AC: 1)
  - [x] Subtask 1.1 (RED): `test_hook_commands_use_absolute_paths` added, confirmed failing against the pre-fix implementation
  - [x] Subtask 1.2 (GREEN): `command_for(root, script)` now builds `f'uv run "{abs_path.as_posix()}"'` from `(root / "tools" / "hooks" / "claude" / script).resolve()`
  - [x] Subtask 1.3: `merge_settings(root, settings)` threads `root` through; `main()` resolves `root = Path(args.repo_root).resolve()` once and passes it to `merge_settings()`

- [x] Task 2: Upgrade stale relative-path entries in place, don't duplicate (AC: 3)
  - [x] Subtask 2.1 (RED): `test_stale_relative_path_command_is_upgraded_not_duplicated` added, confirmed failing (asserted `commands[0] != stale_command`, which failed since the old logic left the stale entry untouched and never even reached a duplication state to catch — the exact-equality check silently did nothing)
  - [x] Subtask 2.2 (GREEN): added `references_our_script(command, script)` (`command.rstrip('"').endswith(script)`), used in `merge_settings()` to overwrite any matching existing entry in place rather than exact-string-match; only appends when nothing matches
  - [x] Subtask 2.3: `test_second_run_is_idempotent` passes unmodified

- [x] Task 3: Verify (don't assume) the git hook shims' exposure (AC: 4)
  - [x] Subtask 3.1: confirmed `tools/hooks/git/*.sh` also use relative paths (`uv run tools/hooks/git/post-commit.py "$@"`)
  - [x] Subtask 3.2/3.3: **empirically verified, not just cited** — real git repo, committed from 3 levels deep in a subdirectory (`sub/deep/`), `post-commit` fired correctly both times (root commit and subdir commit), event captured correctly at the repo root's `.story-events.pending.jsonl` both times. Git's cwd guarantee holds. **No code change made to the git hook shims** — confirmed safe, as expected

- [x] Task 4: Full regression, live E2E, and documentation parity (AC: 1-4)
  - [x] Subtask 4.1: `uv run pytest` (230 passed), `uv run ruff check .` (clean), `uv run ruff format --check tools tests` (clean, after one auto-format pass on the new test file)
  - [x] Subtask 4.2: reproduced the exact failure — installed hooks via the fixed installer into a scratch repo, then invoked the resulting `SessionStart`/`Stop` commands (parsed straight out of `.claude/settings.json`, exactly as Claude Code would run them) from a deep, unrelated subdirectory (`demo/subproject/`). Both exited 0 (previously: `Failed to spawn`), and the event correctly landed in `.story-events.pending.jsonl` at the repo root
  - [x] Subtask 4.3: covered by `test_stale_relative_path_command_is_upgraded_not_duplicated` (Task 2) — a real subprocess-level repeat of this in a scratch repo added no further information beyond what the unit test already proves deterministically
  - [x] Subtask 4.4: installed into a repo path containing a space (`.../scratchpad/test pilot 2/`), confirmed hooks install and the resulting quoted absolute-path command still fires correctly (exit 0, event captured) — the quoting decision was justified, not defensive paranoia
  - [x] Subtask 4.5: no INSTALL.md changes needed — this is a transparent bugfix to an existing install step with no new developer-facing behavior to document

## Dev Notes

### Scope — what this story is and is not

- This is a **bugfix to Story 2.1's existing deliverable** (the hook installer), not new capability. No new files, no new hook events, no new manifest fields.
- **Do NOT build in this story:** any change to what the hooks *do* once they fire (their capture logic in `tools/hooks/claude/*.py` and `tools/hooks/_events.py` is untouched); any change to the git hook shims unless Task 3 actually finds them vulnerable (expected: it won't, but verify per AC 4); a general "make Claude Code more resilient to a hook failing to spawn" — that's an Anthropic-side concern (worth a separate `/feedback` report), not something fixable in this codebase.

### Why this matters (severity context)

Found live during v0.2.0 pilot-simulation testing (2026-07-11): kickoff (Story 1.7) worked perfectly, then the developer did realistic follow-on work (`/opsx:apply`, building a proposed feature in a subdirectory) and `cd`'d into it. From that point, **every** subsequent tool call failed:
```
PreToolUse hook error: [uv run tools/hooks/claude/pre_tool_use.py]: error: Failed to spawn: `tools/hooks/claude/pre_tool_use.py`
Caused by: The system cannot find the path specified. (os error 3)
```
`Stop` failed identically on every turn boundary — an unrecoverable loop, session had to be killed and restarted. This is as close to "worst realistic pilot outcome" as this project has produced: a developer doing completely normal work (building a subproject) permanently breaks their own session with no in-session recovery path. Treat this as the highest-priority item in the current backlog.

### Architecture compliance (binding invariants)

- **AD-8** — "Hook scripts live in a git-tracked directory... a single committed setup script installs them... this setup script runs once per clone/checkout." This story doesn't change *what* AD-8 requires, only makes the installer actually deliver on the "keeps working" half of that promise — AD-8 never said hook commands must be relative, that was purely `setup-hooks.py`'s own (buggy) implementation choice.
- **AD-9** — "A producer that fails to append an event retries up to 3 times; if it still fails, it surfaces a visible error... Silence is never an acceptable outcome." This story is arguably an AD-9 violation in its own right: a hook that can't even *spawn* isn't retried 3 times and doesn't surface a clean, single visible error — it fails immediately and repeatedly on every subsequent call. Once this story's fix lands, that specific failure mode (spawn failure from a bad relative path) becomes structurally impossible, which is the cleanest way to satisfy AD-9 here — prevention over better error handling.
- **Existing test infrastructure** (`tests/test_setup_hooks.py`) already exercises `merge_settings()`/`command_for()` behavior with a `fake_repo` fixture and no real git operations — extend this pattern, don't introduce a new one.

### The AC-3 upgrade-in-place trap (read before writing Task 2)

The single most important design detail in this story: `merge_settings()`'s current "is this hook already wired" check is `hook.get("command") == wanted` — **exact string equality**. Once `wanted` changes shape (relative → absolute), that equality check can *never* match an old-style entry, so a naive fix would silently start **duplicating** every hook command on the first post-fix `setup-hooks` run on any already-installed machine — two `PreToolUse` entries firing on every tool call, both invoking the same underlying script twice. This is exactly the kind of subtle regression a green test suite could miss if Task 2's specific duplicate-prevention test (Subtask 2.1) isn't written first.

Match on "does this command reference our script," not "does this command exactly equal what we'd write today" — and be precise about *how*: once Subtask 1.2's quoting is in place, the command ends with `.py"` (trailing quote), so a naive `command.endswith(script)` **will not match**, silently reintroducing the exact duplication bug this task exists to prevent. Strip the trailing quote before comparing (`command.rstrip('"').endswith(script)`), or equivalent.

### Testing standards (project-context.md §5/§6)

- Everything in Tasks 1-2 is fully unit-testable with the existing `fake_repo` fixture pattern — no real git, no real Claude Code process, no real `uv run` execution needed (the installer only *writes* the command strings; it doesn't invoke them).
- Task 3's verification and Task 4's E2E scenarios are inherently unit-untestable (they require a real git repo, a real directory change, and — for Subtask 4.2 — ideally a real Claude Code session to reproduce the exact failure). Manual E2E is the Definition of Done for these, consistent with this project's established pattern for anything that can't be simulated in a fixture.
- One behavior per test, Arrange/Act/Assert, sentence-style names — matches every existing test file in this repo.

### Source tree touched

```text
tools/setup-hooks.py       UPDATE  command_for() takes root, builds absolute quoted path; merge_settings() matches by script filename, not exact string
tests/test_setup_hooks.py  UPDATE  absolute-path assertions; new upgrade-in-place (no duplicate) test
```

`tools/hooks/git/*.sh`, `tools/hooks/claude/*.py`, and `tools/hooks/_events.py` are **not** touched unless Task 3 finds a genuine problem (expected: it won't).

### Project Structure Notes

- No conflicts with the unified project structure. This story touches exactly the two files Story 2.1 created, nothing else.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.7] — the live-testing incident this story fixes, verbatim error and root-cause analysis
- [Source: tools/setup-hooks.py] — `command_for()`, `merge_settings()`, the exact code this story changes
- [Source: tests/test_setup_hooks.py] — existing `fake_repo` fixture, `run()`/`settings_of()`/`our_commands()` helpers to extend
- [Source: tools/hooks/git/post-commit.sh] — confirmed (2026-07-11, during story creation) also uses a relative path; Task 3 must verify whether this matters given git's cwd guarantee, not assume it doesn't
- [Source: ARCHITECTURE-SPINE.md#AD-8, AD-9] — hook installation invariant this story fulfills more completely; failure-visibility invariant this story satisfies via prevention
- [Source: tools/hooks/_events.py] — docstring's documented assumption that git always invokes hooks with cwd at repo root (the reasoning Task 3 must verify empirically, not just cite)
- [Source: project-context.md] — §1 stdlib-only, §2 atomic writes, §5-6 testing standards, §8-12 branch/PR/DoD

### Review Follow-ups (AI)

External LLM review (Gemini, via PR #22) triaged per project-context §9 — 2026-07-11:

- [x] [AI-Review][Critical] Suffix-matching collision: `references_our_script()`'s original `command.rstrip('"').endswith(script)` would misidentify an unrelated hand-added hook (e.g. `my_backstop.py`) as our `stop.py` purely because the filename ends the same way, silently overwriting the developer's own hook command. Fixed: now requires a path boundary (`/`) immediately before the script name, or an exact match. New test: `test_a_similarly_named_custom_hook_is_not_mistaken_for_ours` (confirmed failing before the fix — the custom command was overwritten — and passing after).
- [x] [AI-Review][Minor] Whitespace sensitivity: trailing whitespace after a quoted command (e.g. a hand-edited `settings.json`) would prevent recognition as ours, causing a duplicate entry on the next install. Fixed: `.strip()` before and after the quote-strip. New test: `test_trailing_whitespace_after_quote_is_still_recognized_as_ours`.
- Declined (out of scope for this story, filed as separate backlog items — see `epics.md`): [AI-Review][Major] `commit-msg.sh` could abort a commit if `uv` is missing from a git client's PATH — real concern, but the file is untouched by this PR (Story 2.1/2.2 territory); [AI-Review][Medium] `repo_root()`'s cwd fallback lacks a parent-directory walk — `_events.py` untouched by this PR; [AI-Review][Minor] missing `.sh`-count assertion in a pre-existing test, temp-file cleanup on write failure, flat-YAML documentation — all reference files/tests this PR does not touch. Five of seven review findings referenced code entirely outside this PR's 4-file diff (verified via `git diff enhancements..story/2.7... --name-only` before triaging) — the 6th PR in a row with at least one misattributed reviewer finding; grep-verify held.

## Dev Agent Record

### Agent Model Used

claude-sonnet-5 (create-story context engineering + dev-story implementation)

### Debug Log References

- RED: `test_hook_commands_use_absolute_paths` and `test_stale_relative_path_command_is_upgraded_not_duplicated` both confirmed failing against pre-fix `tools/setup-hooks.py` before any production change
- GREEN: `uv run pytest tests/test_setup_hooks.py -q` → 14/14 passed after the fix
- Full suite: `uv run pytest -q` → 230 passed in 2.12s; `uv run ruff check .` clean; `uv run ruff format --check tools tests` initially flagged the new test file (fixed via `ruff format`, then clean)
- Task 3 empirical verification: real git repo, `git commit` from a directory 3 levels deep (`sub/deep/`) — `post-commit` fired correctly both from the root and from the subdirectory, event captured correctly at the repo root both times. Confirms git's own cwd guarantee; no fix needed for the git hook shims
- Task 4.2 reproduction: scratch repo, hooks installed via the fixed installer, then the exact `SessionStart`/`Stop` commands from `.claude/settings.json` invoked (via subprocess, `shell=True`, matching how Claude Code would spawn them) from `demo/subproject/` — both exited 0, event correctly landed in `.story-events.pending.jsonl` at the repo root. This is the precise failure mode from the user's live testing, reproduced and confirmed fixed
- Task 4.4: same reproduction repeated in a repo path containing a space (`.../scratchpad/test pilot 2/`) — hooks installed and fired correctly; validates the quoting decision in Subtask 1.2

### Completion Notes List

- Task 1: `command_for(root, script)` now returns `f'uv run "{abs_path.as_posix()}"'`, where `abs_path` is resolved from `--repo-root` at install time. `main()` resolves `root` once (`Path(args.repo_root).resolve()`) and threads it through `merge_settings()`.
- Task 2: the exact-string-equality "already wired" check is replaced with `references_our_script()` (suffix match tolerant of the new trailing quote). This was the single highest-risk detail in the story — a naive `command.endswith(script)` would have silently failed to match the new quoted form, reintroducing the duplicate-entry bug this task exists to prevent. Caught during story creation's self-review, implemented as specified.
- Task 3: git hook shims (`tools/hooks/git/*.sh`) also use relative paths, but were verified — not assumed — safe, because git itself always invokes hooks with cwd at the repository root regardless of where in the working tree a git command was run from. No change made to these files.
- Task 4: all four E2E scenarios executed for real (not simulated) — the exact production failure reproduced and confirmed fixed, the space-in-path edge case validated, the git-hook-safety claim empirically proven rather than cited from a docstring.
- No new dependencies. No architecture deviations from the story file.

### File List

- tools/setup-hooks.py (modified — `command_for()` takes `root` and returns an absolute quoted path; `references_our_script()` matches on a path-boundary-safe suffix, not a bare substring; `merge_settings()` takes `root`, upgrades matching entries in place instead of exact-string matching; `main()` resolves `root` once and passes it through)
- tests/test_setup_hooks.py (modified — 4 new tests: absolute-path assertion, upgrade-not-duplicate regression test, plus 2 review-driven tests for the collision and whitespace fixes)
- _bmad-output/implementation-artifacts/2-7-hook-commands-are-cwd-independent-absolute-paths.md (this file — task checkboxes, Dev Agent Record, status)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — story status transitions)
