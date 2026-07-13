---
baseline_commit: 18edb0b
---

# Story 2.11: Setup Enforces `.gitignore` for Local Capture State

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer working multiple story branches off the same trunk,
I want `.story-events.jsonl` (and the other local capture files) to always be git-ignored,
so that switching between story branches never silently discards or forks captured events.

## Acceptance Criteria

1. **Given** `tools/setup-hooks.py --repo-root .` is run (fresh install or re-run/upgrade)
   **When** the repo's `.gitignore` doesn't already contain one or more of `.story-events.jsonl`, `.story-events.pending.jsonl`, `.active-story`, `.active-claude-session`
   **Then** the installer appends exactly the missing entries (creating `.gitignore` if it doesn't exist at all), without duplicating any entry already present

2. **Given** a repo where one or more of these four files is **already tracked by git** (a stale commit predates this fix — the exact situation found in live pilot testing)
   **When** the installer runs
   **Then** it prints a visible, actionable warning to stderr naming the tracked file(s) and the fix (`git rm --cached <file>`) — but does **not** fail the install (exit 0, `.gitignore`/hooks/settings all still get written); this is a warning about pre-existing repo state, not an installer failure

3. **Given** this fix
   **When** a developer works two story branches off the same trunk and switches between them repeatedly
   **Then** `.story-events.jsonl` is never touched by `git checkout` at all (untracked + ignored), so the log stays continuous and no branch's events are ever discarded or forked

4. **Given** the installer is run a second time on an already-fixed repo (both `.gitignore` correct and nothing tracked)
   **When** it runs
   **Then** it is a silent no-op for this behavior — no duplicate `.gitignore` lines, no spurious warning

## Tasks / Subtasks

- [x] Task 1: `.gitignore` enforcement (AC: 1, 4)
  - [x] Subtask 1.1 (RED): add a test creating a `fake_repo` with no `.gitignore` at all; run the installer; assert all 4 entries now present
  - [x] Subtask 1.2 (RED): add a test with a `.gitignore` that already has 2 of the 4 entries (plus an unrelated line, e.g. `node_modules/`); run the installer; assert only the missing 2 are appended, the existing 2 aren't duplicated, and the unrelated line survives untouched
  - [x] Subtask 1.3 (GREEN): implement `ensure_gitignore(root: Path) -> None` in `tools/setup-hooks.py` — read existing `.gitignore` lines (if the file exists; `utf-8-sig` per this codebase's established BOM-safety convention, see `tools/adapters/resolve.py`'s `read_config()`), compare against `GITIGNORE_ENTRIES = (".story-events.jsonl", ".story-events.pending.jsonl", ".active-story", ".active-claude-session")` by exact line match (ignoring trailing whitespace), append only what's missing via `write_atomic()` (reuse the existing helper — never a partial/non-atomic write), preserving all existing lines and their order
  - [x] Subtask 1.4 (GREEN): wire `ensure_gitignore(root)` into `main()`, called unconditionally alongside the existing git-hooks/settings.json writes
  - [x] Subtask 1.5: re-run `test_second_run_is_idempotent`-style check for this new behavior — second install produces byte-identical `.gitignore`

- [x] Task 2: warn (never fail) when a covered file is already tracked (AC: 2)
  - [x] Subtask 2.1 (RED): add a test that pre-creates one of the 4 files, marks it tracked via a mocked/injected git-query function returning the file as tracked, and asserts (a) a warning appears on stderr naming that file and mentioning `git rm --cached`, (b) exit code is still 0, (c) `.gitignore`/git hooks/`.claude/settings.json` are all still written normally
  - [x] Subtask 2.2 (GREEN): implement `tracked_capture_files(root: Path) -> list[str]` — for each of the 4 entries, ask git whether it's tracked. Reuse the existing safe-subprocess pattern already established in `tools/hooks/_events.py`'s `git_out()` (10s timeout, `capture_output=True`, returns `None` on any failure — never raises, never blocks). A `None`/failed git call (not a repo, git unavailable, timeout) must be treated as "can't determine, don't warn" — same fail-safe philosophy as every other git call in this codebase, not a reason to error out of the whole install
  - [x] Subtask 2.3 (GREEN): print one consolidated warning line per tracked file to stderr from `main()`, after the normal install work completes and before the final JSON ack — e.g. `warning: .story-events.jsonl is tracked by git; this can silently fork your event log across story branches — run: git rm --cached .story-events.jsonl` — and confirm the JSON ack line is still the only stdout line (existing tests assert exactly one stdout line; don't break that contract by printing warnings to stdout)

- [x] Task 3: full regression, live E2E, and doc parity (AC: 1-4)
  - [x] Subtask 3.1: `uv run pytest` full suite green; `uv run ruff check .`; `uv run ruff format --check tools tests`
  - [x] Subtask 3.2: live E2E reproduction of the exact bug this story fixes — real git repo, deliberately commit `.story-events.jsonl` (simulating the pre-fix state found in testing), then run the fixed installer and confirm the warning appears; separately, on a **fresh** repo (nothing tracked yet), run the installer, do real work across two branches with real `git checkout`s, and confirm the event log stays continuous (no forking) — this is the actual real-world scenario that motivated the story, not just a unit-test abstraction
  - [x] Subtask 3.3: update `tools/build-release/INSTALL.md`'s "Daily use" section — the manual `.gitignore` step listed there is no longer something the developer needs to do themselves; note that `setup-hooks.py` now handles it, while leaving the actual `.gitignore` line list visible for anyone curious what's being ignored and why

## Dev Notes

### Scope — what this story is and is not

- This extends Story 2.1's installer (`tools/setup-hooks.py`) with one more piece of setup it's now responsible for — same file, same "single repeatable setup step" contract, no new script or command.
- **Do NOT build in this story:** any change to what happens *after* a file is already forked (no merge/reconciliation logic for divergent branch-local copies of `.story-events.jsonl` — prevention only, not recovery); any general "scan for other dangerous already-committed state" beyond these 4 specific files (that's explicitly Held for later in `epics.md`); any change to the git hook shims or Claude hook scripts themselves.

### Why this matters (severity context)

Found live during pilot testing (2026-07-13) of a deliberate mid-session branch-switch scenario (`story/AI-53` ↔ `story/AI-54`, both off the same base). `.story-events.jsonl` had been git-tracked because the `.gitignore` entries documented in `INSTALL.md` were never actually added — a manual step, easy to miss, and missed here. With the file tracked, each branch accumulated its own committed version of the shared event log; every `git checkout` between the two branches **silently overwrote the working-tree file with whichever branch's committed version was checked out**, discarding — not merging — whatever had been captured on the branch just left. Confirmed via `Select-String` over the full log: every event recorded while on `AI-54` (a commit, a kickoff) was completely absent once back on `AI-53`. No error, no warning, just quietly wrong data — worse than a crash, because a resulting snapshot would look completely normal while being silently incomplete. This is the highest-severity finding from this round of testing: it's the kind of bug that corrupts the exact data this whole project exists to produce, with nothing visibly wrong to tip off the developer.

### Architecture compliance (binding invariants)

- **AD-8** — "a single committed setup script installs [hooks]... runs once per clone/checkout." This story extends what that one setup step is responsible for guaranteeing — the same spirit as Story 2.7's fix, just for a different failure mode of the same installer.
- **AD-9** — "Silence is never an acceptable outcome." The tracked-file warning (Task 2) is a direct AD-9 application: this codebase's established pattern is prevention where possible (Task 1 stops the problem from recurring on a clean repo) plus a visible surfaced warning where prevention alone can't undo pre-existing bad state (Task 2, for repos where the damage is already done).
- **`write_atomic()` (already in `tools/setup-hooks.py`)** — reuse it for the `.gitignore` write. Never a partial/in-place write, matching `project-context.md` §2's atomic-write rule.
- **BOM-safety convention** — `tools/adapters/resolve.py`'s `read_config()` reads with `encoding="utf-8-sig"` specifically because "Windows editors and PowerShell 5.1 commonly write a UTF-8 BOM." Reading an existing `.gitignore` should use the same encoding, for the same reason — this project's own pilot testing has repeatedly been done from a Windows/PowerShell environment.
- **Existing test infrastructure** (`tests/test_setup_hooks.py`) already has a `fake_repo` fixture and `run()`/`settings_of()`/`our_commands()` helpers — extend this file, don't create a new one. Follow the same "one behavior per test, sentence-style name" pattern already established there.

### The stdout-contract trap (read before writing Task 2)

`test_ack_lists_git_hooks_and_events` currently asserts **exactly one line of stdout** — the JSON ack. Task 2's warning must go to **stderr**, never stdout, or that existing test (and the "one JSON object on success" API contract in `project-context.md` §3) breaks. Don't `print()` the warning without `file=sys.stderr`.

### The git-availability trap (read before writing Task 2)

Tests use a `fake_repo` fixture with **no real `git init`** — just a manually-created `.git/hooks/` directory, not an actual git repository. A real `git ls-files`-style call against that fixture will fail (not a repo). `tracked_capture_files()` must treat that failure exactly like `tools/hooks/_events.py`'s `git_out()` already does — return `None`/skip that file, never raise, never block the rest of the install. For the RED/GREEN tests in Subtask 2.1, don't try to make `fake_repo` a real git repo just for this — inject/monkeypatch the tracked-check function (or the underlying `git_out`-style call) the same way `tests/hooks/test_git_hooks.py` already monkeypatches `events.git_out` for its own tests. For Subtask 3.2's E2E reproduction, use a **real** git repo (as Story 2.7's Task 3/4 did) since that's the only way to prove the actual warning path and the actual continuity fix work outside of mocks.

### Source tree touched

```text
tools/setup-hooks.py        UPDATE  new GITIGNORE_ENTRIES constant, ensure_gitignore(), tracked_capture_files(), wired into main()
tests/test_setup_hooks.py   UPDATE  new tests for gitignore creation/append/idempotency and the tracked-file warning
tools/build-release/INSTALL.md  UPDATE  Task 3.3 — note the manual .gitignore step is now automatic
```

`tools/hooks/_events.py`, `tools/hooks/git/*.sh`, `tools/hooks/claude/*.py`, and the opsx wrapper are **not** touched — this story is scoped entirely to the installer.

### Project Structure Notes

No conflicts with the unified project structure — this story extends the same file (`tools/setup-hooks.py`) Story 2.1 created and Story 2.7 already modified once.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.11] — the live-testing incident this story fixes, verbatim reproduction detail
- [Source: tools/setup-hooks.py] — `write_atomic()`, `main()`, existing `GIT_HOOKS`/`CLAUDE_EVENTS` constant pattern to follow for the new `GITIGNORE_ENTRIES` constant
- [Source: tools/hooks/_events.py#git_out] — the established safe-subprocess pattern (timeout, capture_output, returns `None` on any failure) to mirror for `tracked_capture_files()`
- [Source: tools/adapters/resolve.py#read_config] — the `utf-8-sig` BOM-safety convention to reuse when reading an existing `.gitignore`
- [Source: tests/test_setup_hooks.py] — existing `fake_repo` fixture, `run()`/`settings_of()`/`our_commands()` helpers to extend
- [Source: tests/hooks/test_git_hooks.py#repo fixture] — the monkeypatch-a-git-helper pattern to use instead of a real git repo for Task 2's unit tests
- [Source: tools/build-release/INSTALL.md] — the manual `.gitignore` bullet this story makes obsolete (Task 3.3)
- [Source: ARCHITECTURE-SPINE.md#AD-8, AD-9] — the setup-step and never-silent invariants this story fulfills more completely
- [Source: project-context.md] — §1 stdlib-only, §2 atomic writes, §5-6 testing standards, §8-12 branch/PR/DoD

## Dev Agent Record

### Agent Model Used

claude-sonnet-5 (create-story context engineering + dev-story implementation)

### Debug Log References

- RED: 6 new tests added to `tests/test_setup_hooks.py`, confirmed all 6 failing against pre-fix `tools/setup-hooks.py` (`AttributeError: module 'setup_hooks' has no attribute '_events'` — expected, since `_events` wasn't imported yet)
- GREEN: `uv run pytest tests/test_setup_hooks.py -q` → 22/22 passed after implementation
- Full suite: `uv run pytest -q` → 238 passed; `uv run ruff check .` clean; `uv run ruff format --check tools tests` flagged 2 files (whitespace-only), fixed via `ruff format`, then clean
- Live E2E #1 (tracked-file warning): real git repo, deliberately committed `.story-events.jsonl` (simulating the exact pre-fix state found in pilot testing), ran the fixed installer — warning correctly printed to stderr naming the file and `git rm --cached` fix, exit code 0, `.gitignore`/hooks/settings all written normally
- Live E2E #2 (branch continuity): real git repo, fresh install (no pre-existing tracked files, confirmed zero warnings), kicked off a story, created `story/A`, appended an event, committed, created `story/B` off `story/A`, appended a second event (uncommitted — file is now ignored, nothing to commit), checked out back to `story/A` — confirmed `.story-events.jsonl` still contained **both** events (`on-A-1` and `on-B-1`) after the round-trip checkout, proving the log stays continuous and is never touched/forked by `git checkout` once ignored
- Post-review E2E: real git repo with both edge cases at once — a pre-existing anchored `/.story-events.jsonl` rule in `.gitignore` **and** the file force-tracked (`git add -f`, simulating a stale commit despite the ignore rule) — confirmed no redundant plain entry was added to `.gitignore`, and the tracked-file warning still fired correctly via the new single batched `git ls-files` call

### Completion Notes List

- Task 1: `ensure_gitignore(root)` reads the existing `.gitignore` (if any, `utf-8-sig` per this codebase's BOM-safety convention) and appends only the missing entries via the existing `write_atomic()` helper — creates the file if absent, preserves existing lines/order, no duplication on repeat runs.
- Task 2: `tracked_capture_files(root)` asks git (`git ls-files --error-unmatch <file>`, via the shared `_events.git_out()` helper — same 10s-timeout/never-raises pattern used everywhere else in this codebase) whether each of the 4 covered files is tracked; a failed/unavailable git call degrades to "not tracked" exactly like every other `git_out()` caller, never blocking the install. `main()` prints one warning line per tracked file to **stderr** (never stdout — verified the existing "exactly one JSON line on stdout" contract still holds) after the normal install work, before the final ack.
- Task 3: full regression green, both real-git E2E scenarios reproduced and confirmed (not just unit-tested), `INSTALL.md` updated to note the `.gitignore` step is now automatic and to explain why the warning matters if seen.
- No new dependencies (reused the existing `_events.git_out()` and `write_atomic()`). No architecture deviations from the story file.

### File List

- tools/setup-hooks.py (modified — new `GITIGNORE_ENTRIES` constant, `ensure_gitignore()`, `tracked_capture_files()`, both wired into `main()`; imports `_events` for the shared `git_out()` helper)
- tests/test_setup_hooks.py (modified — 11 new tests total: fresh-install creation, partial-existing append, idempotency, tracked-file warning, no-warning-when-clean, git-unavailable-degrades-safely, anchored-slash-entry recognition, whitespace-padded-entry recognition, gitignore-as-a-directory doesn't crash, single-batched-git-call)
- tools/build-release/INSTALL.md (modified — notes the `.gitignore` step is now automatic via `setup-hooks.py`, explains the tracked-file warning)
- _bmad-output/implementation-artifacts/2-11-setup-enforces-gitignore-for-local-capture-state.md (this file — task checkboxes, Dev Agent Record, status)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — story status transitions)

### Review Follow-ups (AI)

External LLM review (Gemini, via PR #23) — 2026-07-13, all 3 findings genuine (this PR's own new code, no misattribution):

- [x] [AI-Review][Minor] `tracked_capture_files()` spawned one `git ls-files` subprocess per entry (4 total) — wasteful, especially on Windows where process creation is slower. Fixed: a single batched `git ls-files -- <paths...>` call, which exits 0 and prints just the subset that's tracked. New test: `test_tracked_check_uses_a_single_batched_git_call`.
- [x] [AI-Review][Minor] `ensure_gitignore()`'s exact-string-equality check missed a pre-existing entry written with surrounding whitespace, or anchored with a leading slash (e.g. `/.story-events.jsonl`) — would redundantly append a duplicate plain entry. Fixed: matching now strips whitespace and also recognizes the leading-slash-anchored form as already-covered. New tests: `test_anchored_slash_prefixed_entry_is_not_redundantly_duplicated`, `test_whitespace_padded_existing_entry_is_recognized_not_duplicated`.
- [x] [AI-Review][Minor] `path.exists()` before `read_text()` would crash (`IsADirectoryError`) if `.gitignore` were somehow a directory rather than a file. Fixed: guarded with `path.is_file()`, printing a visible warning and skipping enforcement rather than crashing the whole install. New test: `test_gitignore_as_a_directory_does_not_crash_the_install`.

All 3 findings verified against the actual PR #23 diff before fixing (`git log --oneline -1 story/2.11-gitignore-enforcement -- tools/setup-hooks.py` confirms the file is this PR's own new code) — no misattribution this round. Post-review real-git E2E re-verified both the anchored-entry dedup and the tracked-file warning together (see Debug Log).
