---
baseline_commit: 16843980f24395b0648810062335cf8669bbd6fb
---

# Story 3.1: Active-Story Pointer Tracks Time Automatically

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want the system to know which story I'm actively working on without me telling it,
So that my time-on-task is attributed correctly without logging hours.

## Acceptance Criteria

1. **Given** the branch-per-story convention (NFR5) and hooks installed (Story 2.1)
   **When** the developer checks out a story branch or a Claude Code session starts
   **Then** `.active-story` updates, closing the outgoing story's time slice and opening a new one for the incoming story (AD-7)

## Tasks / Subtasks

- [x] Task 1: Define and implement the shared active-story pointer mechanics in `tools/hooks/_events.py` (AC: 1)
  - [x] Subtask 1.1 (RED): write failing tests in `tests/hooks/test_active_story.py` for a new `update_active_story(root, incoming_story_id)` function: first-ever call with no prior `.active-story` opens a slice and writes the pointer file with no close event; a call with a *different* incoming story_id than the current pointer emits a `time.slice_closed` event for the outgoing story (with `duration_seconds`) via the existing shared emitter, then emits `time.slice_opened` and rewrites the pointer for the incoming story; a call with the *same* incoming story_id as the current pointer is a no-op (no events, pointer file unchanged); a call with `incoming_story_id=None` is a no-op (nothing to attribute time to, mirrors AD-1b's "buffer/skip rather than corrupt" philosophy)
  - [x] Subtask 1.2 (GREEN): implement `update_active_story()` in `_events.py`, reusing `envelope()`/`emit()` for the two new namespaced event types (`source="time"`, `type="time.slice_closed"` / `"time.slice_opened"`) so AD-1/AD-1b/AD-9 (append-only, pending-spool buffering, retry-then-surface) apply automatically — do not reimplement any of that here
  - [x] Subtask 1.3: add an atomic pointer-file writer (temp file → flush → `os.fsync` → `os.replace`, per project-context.md §2) for `.active-story`; do not append/mutate it in place. Pointer file shape: `{"story_id": str, "opened_at": iso8601}` — a plain JSON object, not flat-YAML (this file is machine-only, never hand-edited, so JSON is the simpler and consistent choice against the event envelope's own JSON shape)
  - [x] Subtask 1.4 (REFACTOR): confirm `update_active_story()` has no knowledge of *why* it's being called (git checkout vs. Claude session) — it only ever receives "what story should be active now"

- [x] Task 2: Wire the git side — `tools/hooks/git/post-checkout.py` (AC: 1)
  - [x] Subtask 2.1 (RED): extend `tests/hooks/test_git_hooks.py` — a branch checkout (`branch_checkout=True`, i.e. the third arg is `"1"`) into a directory whose (git-managed, branch-specific) `.story.yaml` now names a different story_id causes `.active-story` to update and a `time.slice_closed`/`time.slice_opened` pair to be appended; a *file* checkout (`branch_checkout=False`) must NOT touch `.active-story` at all — filter on the existing `branch_checkout` flag already parsed by this hook
  - [x] Subtask 2.2 (GREEN): after the existing `git.checkout` event emission, call `_events.update_active_story(root, _events.story_id(root))` — but only when `branch_checkout` is true. Read `.story.yaml` again post-checkout (not the pre-checkout value) since git has already updated the working tree by the time `post-checkout` fires

- [x] Task 3: Wire the Claude Code side — `tools/hooks/claude/session_start.py` (AC: 1)
  - [x] Subtask 3.1 (RED): extend `tests/hooks/test_claude_hooks.py` — a `SessionStart` firing while `.active-story` is stale (points at a different, or no, story) updates the pointer and emits the close/open pair; a `SessionStart` firing when the pointer already matches the current story is a no-op beyond the existing `ai.claude-code.session_start` event
  - [x] Subtask 3.2 (GREEN): call `_events.update_active_story(root, _events.story_id(root))` unconditionally in `session_start.py`'s `main()`, alongside (not replacing) the existing `ai.claude-code.session_start` emission. Keep the hook's `return 0` unconditional exit behavior (Claude Code hooks must never block the session, per the existing docstring convention in this file)

- [x] Task 4: Full regression and documentation parity (AC: 1)
  - [x] Subtask 4.1: run the full test suite (`uv run pytest`) — confirm no regression in existing `test_git_hooks.py` / `test_claude_hooks.py` coverage from Stories 2.2/2.3
  - [x] Subtask 4.2: update `ARCHITECTURE-SPINE.md`'s AD-7 section and Structural Seed to record the concrete `.active-story` JSON shape and the new `time.slice_opened`/`time.slice_closed` event types this story introduces — the current spine names the file and the rule but not the wire format; per project-context.md §12 DoD, a story that fixes a documented gap must close it in the same PR

## Dev Notes

- **This is the first story in Epic 3** — no previous-story intelligence to inherit. Epic 2's retrospective (in `epics.md`) flagged that a story's stated ACs must be checked against what *later* stories in the same epic will assume. Story 3.2 (idle timeout) and Story 3.3 (mid-session checkout precedence) will both read/extend whatever pointer file shape this story establishes — keep the `.active-story` schema to exactly `{story_id, opened_at}` now. Do not add idle-tracking or session-precedence fields speculatively; that is explicitly those stories' job (project-context.md §2, "no premature abstraction").
- **Reuse, don't reinvent (critical):** `tools/hooks/_events.py` already provides everything this story needs structurally — `emit()`, `envelope()`, the pending-spool buffering, and the 4-attempt retry-then-surface ladder (AD-1/AD-1b/AD-9). `update_active_story()` must be built *on top of* `emit()`, not as a parallel append mechanism. This is the same "shared emitter, source-parameterized" pattern the Epic 2 retro called out as having paid for itself twice already (Story 2.3's spine amendment, then Story 2.6 reusing `git_out()`).
- **Where `.story.yaml` gets its new value from:** per project-context.md §11 and ARCHITECTURE-SPINE.md's Deployment note, `.story.yaml` *is* git-tracked and committed per branch (unlike `.story-events.jsonl`/`.active-story`, which are git-ignored). This means after `git checkout` completes, the working tree's `.story.yaml` already reflects the new branch's story — `post-checkout.py` does not need to inspect the previous branch at all; it only needs to re-read `.story_id(root)` *after* the checkout (the hook fires post-checkout, so this is already the new value).
- **Branch vs. file checkout filter already exists**: `post-checkout.py` already parses git's third argument into `payload["branch_checkout"]` (a bool) for the existing `git.checkout` event (Story 2.2). Reuse that same parsed value to gate the new active-story-update call — do not re-parse `sys.argv` a second time.
- **Atomic writes are a hard project rule (project-context.md §2)**, not just for `.story.yaml`/`.story-events.jsonl`/snapshots as literally listed — `.active-story` is exactly the same class of "must never corrupt" local state file, so the same temp-file → fsync → `os.replace` pattern applies. Reference implementation: `_bmad/scripts/memlog.py`'s `write_atomic()`.
- **AD-7's precedence rule is explicitly OUT of scope for this story** — "a live session's SessionStart/SessionEnd boundaries take precedence over a mid-session checkout" is Story 3.3's acceptance criterion. Story 3.1 only needs both triggers (checkout, session start) to correctly open/close slices when the pointer's story_id actually differs; do not attempt to detect or special-case a checkout happening *during* a live session yet — that would be scope creep into 3.3.
- **Testing standards (project-context.md §5/§6):** no real git operations, no real Claude Code process — same `monkeypatch`-on-`events.repo_root`/`events.git_out`/`events.read_stdin_json` fixture pattern already established in `tests/hooks/test_git_hooks.py` and `tests/hooks/test_claude_hooks.py`. One behavior per test. Every AC line maps to at least one test — this story has a single AC, but it covers four distinct behaviors (first-ever open, close+reopen on change, no-op on same story, no-op on `None`), each needs its own test per §6's "one behavior per test" rule.
- **New test file `tests/hooks/test_active_story.py`** is appropriate here (rather than folding everything into the existing git/claude test files) since `update_active_story()` itself lives in the shared `_events.py` module and its correctness doesn't depend on which producer family calls it — mirrors how `tests/hooks/` already separates by what's under test, not by which hook fires it. The git- and claude-hook test files still each get a smaller integration-style test confirming *they* call it correctly (Tasks 2/3).

### Project Structure Notes

- Extends (does not create new top-level modules): `tools/hooks/_events.py`, `tools/hooks/git/post-checkout.py`, `tools/hooks/claude/session_start.py`.
- New file: `tests/hooks/test_active_story.py` (mirrors the existing `tests/hooks/` layout convention, project-context.md §5).
- New git-ignored runtime artifact: `.active-story` at repo root (already named in ARCHITECTURE-SPINE.md's Structural Seed and Deployment section as git-ignored; no `.gitignore` change needed if `.story-events.jsonl`'s existing ignore pattern already covers dotfiles generically — verify during implementation and add an explicit `.active-story` line if not).
- No conflicts detected with the unified project structure; this story's whole surface area is inside `tools/hooks/` and `tests/hooks/`, consistent with Epic 2's file layout.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.1: Active-Story Pointer Tracks Time Automatically] — AC text
- [Source: _bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md#AD-7 — Time-on-task via an explicit active-story pointer] — binds, rule, precedence note (precedence itself deferred to Story 3.3)
- [Source: _bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md#Structural Seed] — `.active-story` file location and git-ignored status
- [Source: _bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md#Deployment & Environments] — `.story.yaml` committed per branch vs. `.active-story`/`.story-events.jsonl` git-ignored
- [Source: project-context.md#2. Code Standards] — atomic writes, small single-purpose functions, no premature abstraction
- [Source: project-context.md#5. Testing Framework / #6. Unit Testing Standards] — pytest, mocking conventions, one-behavior-per-test, boundary testing
- [Source: tools/hooks/_events.py] — `emit()`, `envelope()`, `git_out()`, `story_id()`, retry/buffering mechanics to reuse as-is
- [Source: tools/hooks/git/post-checkout.py] — existing `branch_checkout` flag parsing to reuse
- [Source: tools/hooks/claude/session_start.py] — existing hook structure and unconditional `return 0` convention
- [Source: tests/hooks/test_git_hooks.py, tests/hooks/test_claude_hooks.py] — existing fixture/monkeypatch pattern to follow

## Dev Agent Record

### Agent Model Used

claude-sonnet-5

### Debug Log References

- Live E2E: real temp git repo, two committed branches each with their own `.story.yaml`, real `git checkout` + real `post-checkout.py` invocation via `uv run --script`. Confirmed `.active-story` and the event log both update correctly across a real branch switch, including a real non-zero `duration_seconds` on the closed slice.

### Completion Notes List

- Implemented `update_active_story()` as a thin layer on top of the existing `emit()`/`envelope()` machinery — no parallel append mechanism. Extended `emit()` with an optional `story_override` parameter (backward-compatible; every existing caller is unaffected) so slice-close/slice-open events can be attributed to the outgoing/incoming story explicitly, rather than whatever `.story.yaml` happens to say at emit time.
- `.active-story` pointer file uses the same atomic temp-file → fsync → `os.replace` pattern as `memlog.py`'s `write_atomic()`, applied via a new `write_atomic_json()` helper in `_events.py`.
- Wired into `post-checkout.py` (gated on the existing `branch_checkout` flag — file checkouts never touch the pointer) and `session_start.py` (unconditional, matching the existing "Claude Code hooks never block" convention).
- Updated 3 existing tests in `test_git_hooks.py`/`test_claude_hooks.py` whose event-count/tuple-destructuring assertions were invalidated by the new events now interleaved into branch-checkout and session-start flows; this is a legitimate behavior change (AC 1), not a weakened test — assertions were extended, not removed.
- Updated `ARCHITECTURE-SPINE.md`'s AD-7 section with the concrete `.active-story` JSON shape and the two new `time.*` event types, per project-context.md §12 DoD (a story closing a documented gap must close it in the same PR).
- Full suite: 188 passed, 0 regressions. `ruff check` clean on all touched files.

### File List

- `tools/hooks/_events.py` (modified — `update_active_story()`, `write_atomic_json()`, `read_active_story()`, `emit()` gained `story_override`)
- `tools/hooks/git/post-checkout.py` (modified — calls `update_active_story()` on branch checkouts)
- `tools/hooks/claude/session_start.py` (modified — calls `update_active_story()` unconditionally)
- `tests/hooks/test_active_story.py` (new)
- `tests/hooks/test_git_hooks.py` (modified — extended for active-story pointer behavior)
- `tests/hooks/test_claude_hooks.py` (modified — extended for active-story pointer behavior)
- `_bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md` (modified — AD-7 wire-format documentation)
- `.gitignore` (modified — added `.active-story`, which was not covered by the existing `.story-events*` entries)
