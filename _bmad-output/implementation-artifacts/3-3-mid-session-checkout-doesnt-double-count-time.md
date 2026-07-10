---
baseline_commit: e8ecd48506b247b6cd51a04df5435a21b93fc4fb
---

# Story 3.3: Mid-Session Checkout Doesn't Double-Count Time

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want switching story branches mid-AI-session to not corrupt time totals,
So that my time attribution stays accurate even when I context-switch quickly.

## Acceptance Criteria

1. **Given** a live Claude Code session (Story 3.1)
   **When** a `git checkout` happens mid-session
   **Then** the live session's `SessionStart`/`SessionEnd` boundaries govern time-slice accounting
   **And** the checkout re-points which story current activity counts toward, without itself opening or closing a session-level slice (AD-7 precedence rule)

## Tasks / Subtasks

- [x] Task 1: Add live-session tracking + a mid-session-safe repoint to `tools/hooks/_events.py` (AC: 1)
  - [x] Subtask 1.1 (RED): write failing tests in `tests/hooks/test_active_story.py` for three new functions:
    - `mark_session_active(root, session_id)` — writes a `.active-claude-session` marker (atomic, via `write_atomic_json`); `is_session_active(root)` then returns `True`
    - `mark_session_inactive(root)` — removes the marker if present; a missing marker is a no-op (no error); `is_session_active(root)` then returns `False`
    - `repoint_active_story(root, incoming_story_id)` — when a pointer exists and `incoming_story_id` differs from the pointer's current `story_id`, rewrites *only* `story_id` in the `.active-story` JSON, leaving `opened_at`/`last_activity_at` untouched, and emits **no** `time.slice_closed`/`time.slice_opened` events; when `incoming_story_id` matches the current pointer, or `incoming_story_id` is `None`, or no pointer exists yet, it is a no-op (nothing to repoint)
  - [x] Subtask 1.2 (GREEN): implement all three using the existing `read_active_story()`/`write_atomic_json()` helpers — no new I/O pattern
  - [x] Subtask 1.3 (RED then GREEN): write failing tests, then implement `close_active_story_slice(root)`: when a pointer exists, emits `time.slice_closed` (`{opened_at, closed_at, duration_seconds}`, attributed to the pointer's story_id, computed the same way `update_active_story()` already computes `duration_seconds`) and then **deletes** the `.active-story` file (the slice is conclusively over — nothing left to repoint into); when no pointer exists, it is a no-op (no event, no error)

- [x] Task 2: Make `git post-checkout` precedence-aware (AC: 1)
  - [x] Subtask 2.1 (RED): extend `tests/hooks/test_git_hooks.py` — a branch checkout while `is_session_active()` is true calls `repoint_active_story()` (pointer's `story_id` changes, `opened_at` is preserved from before the checkout, no `time.slice_closed`/`time.slice_opened` emitted); a branch checkout while no session is active behaves exactly as Story 3.1 left it (calls `update_active_story()`, full slice accounting) — this must not regress any existing Story 3.1 `post-checkout` test
  - [x] Subtask 2.2 (GREEN): in `post-checkout.py`, after the existing `git.checkout` emission, branch on `_events.is_session_active(root)`: if true, call `_events.repoint_active_story(root, incoming)`; else call `_events.update_active_story(root, incoming)` (today's behavior, unchanged) — where `incoming = _events.story_id(root)`, read post-checkout exactly as Story 3.1 established

- [x] Task 3: Wire session boundaries to own the live-session marker and the slice's actual close (AC: 1)
  - [x] Subtask 3.1 (RED): extend `tests/hooks/test_claude_hooks.py` — `session_start` now also calls `mark_session_active()` (verify via `is_session_active()` reading `True` afterward), in addition to its existing `update_active_story()` call (unchanged from Story 3.1); `session_end` now calls `close_active_story_slice()` (emits `time.slice_closed` for whatever story the pointer currently names, deletes the pointer) followed by `mark_session_inactive()` — verify both the emitted event and that `.active-story` no longer exists afterward, and that a `session_end` with no prior pointer is a clean no-op (no event, no crash)
  - [x] Subtask 3.2 (GREEN): wire `session_start.py` (`mark_session_active` alongside its existing `update_active_story` call) and `session_end.py` (`close_active_story_slice` then `mark_session_inactive`)
  - [x] Subtask 3.3: update the shared `ALL_HOOKS`-loop test (`test_event_types_are_namespaced_per_hook`) and the always-fails-append test (`test_every_claude_hook_returns_0_even_on_total_append_failure`) in `tests/hooks/test_claude_hooks.py` for the new `time.slice_closed` event `session_end` now emits when a pointer is live at that point in the loop — this is a legitimate behavior change (AC 1), extend the assertions, don't weaken them (same category of update Story 3.1/3.2 already made to these two tests)

- [x] Task 4: Full regression, live E2E, and documentation parity (AC: 1)
  - [x] Subtask 4.1: run the full test suite (`uv run pytest`) and `uv run ruff format --check tools tests` + `uv run ruff check tools tests` — **both** format and lint, per the Story 3.2 PR #17 CI lesson (format-only failures previously slipped past a lint-only local check)
  - [x] Subtask 4.2: live E2E in a real temp git repo: start a session (`session_start.py` via `uv run --script`) for story A, `git checkout` to a branch whose `.story.yaml` names story B while the session marker is still present, confirm `.active-story`'s `story_id` is now B with `opened_at` unchanged from the original session start and **no** `time.slice_closed`/`time.slice_opened` in the event log for this repoint, then fire `session_end.py` and confirm exactly one `time.slice_closed` now appears, attributed to story B, and `.active-story` no longer exists
  - [x] Subtask 4.3: add `.active-claude-session` to `.gitignore` (mirrors the Story 3.1 `.active-story` addition — this is local machine state, never committed)
  - [x] Subtask 4.4: update `ARCHITECTURE-SPINE.md`'s AD-7 section with the concrete precedence-implementation mechanics: the `.active-claude-session` marker, `repoint_active_story()` vs. `update_active_story()`, and that `close_active_story_slice()` (wired to `SessionEnd`) is what actually closes a slice now, rather than a slice only ever closing lazily the next time the pointer needs to change to a different story

## Dev Notes

- **This is the last story in Epic 3** — Stories 3.1 and 3.2 (`_bmad-output/implementation-artifacts/3-1-*.md`, `3-2-*.md`) are direct predecessors and this story completes AD-7. Read both in full before starting.
- **Previous story intelligence (Stories 3.1 & 3.2):**
  - `.active-story` is currently `{"story_id": str, "opened_at": iso8601, "last_activity_at": iso8601 (optional, Story 3.2)}`, read via `read_active_story()`, written via `write_atomic_json()`. This story adds a **second** small pointer file, `.active-claude-session` — do not fold live-session tracking into `.active-story` itself; they answer different questions ("which story" vs. "is a Claude session currently open") and conflating them would make `update_active_story()`/`record_activity()` harder to reason about.
  - `update_active_story()` (Story 3.1) and `record_activity()` (Story 3.2) are **unchanged by this story** — do not modify their behavior. This story adds new, narrower-purpose siblings (`repoint_active_story()`, `close_active_story_slice()`, `mark_session_active()`/`mark_session_inactive()`/`is_session_active()`) for the one new concern: precedence when a checkout happens while a session is already live.
  - `emit()`'s `story_override` parameter (added Story 3.1, reused by Story 3.2) is what `close_active_story_slice()` needs too, for the same reason: attribute `time.slice_closed` to the pointer's story_id, not whatever `.story.yaml` says by the time the event is built.
  - **This is exactly the gap the ARCHITECTURE-SPINE.md AD-7 rule already named before any of Epic 3 was implemented**: "A session-level slice only opens/closes on `SessionStart`/`SessionEnd`." Story 3.1 implemented the *opening* half (via `update_active_story()` at `SessionStart`) but never wired an explicit *closing* action to `SessionEnd` — slices only ever closed lazily, the next time the pointer needed to switch to a different story (at the next `SessionStart` or an off-session `post-checkout`). This story is what finally wires `SessionEnd` to actually close the slice via `close_active_story_slice()`. This is not scope creep — it is required for the AC's own wording ("the live session's `SessionStart`/`SessionEnd` boundaries govern time-slice accounting") to mean anything concrete.
  - Story 3.2's PR #17 review caught a real defect: a malformed `STORY_IDLE_THRESHOLD_SECONDS` env var raised at module import time, which would have broken every hook including `commit-msg.py` (which must always exit 0). No comparable env-var/config surface is introduced by this story, but the general lesson holds: anything evaluated at module import time in `_events.py` must degrade gracefully, never raise.
  - **Process lesson from Story 3.2's PR #17**: CI runs `ruff format --check` as a *separate* gate from `ruff check` (lint). A prior push passed lint locally but failed CI on formatting. Run both `uv run ruff format --check tools tests` and `uv run ruff check tools tests` before pushing this story's branch (see Task 4.1).
- **Precedence logic, precisely:** `post-checkout.py`'s branch-checkout handling must branch on whether a Claude Code session is currently open (`is_session_active()`):
  - **Session live:** call `repoint_active_story()` — only the pointer's `story_id` changes; the slice's `opened_at` (and any `last_activity_at` idle-tracking from Story 3.2) is preserved untouched, and no `time.slice_closed`/`time.slice_opened` fires. The ongoing session's activity now counts toward the new story, but the session itself isn't considered to have "switched slices" at the git level.
  - **No session live:** call `update_active_story()` exactly as Story 3.1 left it — a checkout with nobody's AI session running is the normal "I'm starting fresh work on a different story" case, and should close/open slices exactly as before. **This branch must not regress a single existing Story 3.1 `post-checkout` test** — those tests never create a `.active-claude-session` marker, so `is_session_active()` naturally reads `False` for them, and they should need zero changes.
- **Why `close_active_story_slice()` deletes the pointer rather than leaving it in place:** once a session ends, there is nothing live to attribute further activity to until either a new `SessionStart` or a `post-checkout` (with no session live) opens a fresh slice — leaving a stale pointer around risks a later, unrelated activity signal being silently misattributed to a session that already ended. Deleting it is the same "no pointer = nothing to attribute" philosophy Stories 3.1/3.2 already established for `record_activity()`/`update_active_story()`'s `None`-story no-op cases.
- **Testing standards (project-context.md §5/§6):** no real git operations, no real Claude Code process, no real sleeps — same `monkeypatch` fixture pattern established in Stories 3.1/3.2 (`events.repo_root`, `events.read_stdin_json`, `events._now`, `events.RETRY_DELAY_SECONDS`). One behavior per test.

### Project Structure Notes

- Extends (does not create new modules): `tools/hooks/_events.py`, `tools/hooks/git/post-checkout.py`, `tools/hooks/claude/session_start.py`, `tools/hooks/claude/session_end.py`.
- Extends existing test files: `tests/hooks/test_active_story.py`, `tests/hooks/test_git_hooks.py`, `tests/hooks/test_claude_hooks.py`.
- New git-ignored runtime artifact: `.active-claude-session` at repo root (add to `.gitignore` alongside the existing `.active-story` entry).
- No conflicts with the unified project structure; surface area stays inside `tools/hooks/` and `tests/hooks/`, consistent with all of Epic 3 so far.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3: Mid-Session Checkout Doesn't Double-Count Time] — AC text
- [Source: _bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md#AD-7 — Time-on-task via an explicit active-story pointer] — the precedence rule this story implements, plus the Story 3.1/3.2-added wire-format notes this story extends
- [Source: _bmad-output/implementation-artifacts/3-1-active-story-pointer-tracks-time-automatically.md] — `update_active_story()`, `.active-story` shape, `emit()`'s `story_override`
- [Source: _bmad-output/implementation-artifacts/3-2-idle-time-doesnt-inflate-a-storys-active-time.md] — `record_activity()`, `_now()`, the Story 3.2 PR #17 CI/env-var lessons
- [Source: project-context.md#2. Code Standards] — atomic writes, small single-purpose functions, no premature abstraction
- [Source: project-context.md#6. Unit Testing Standards] — one behavior per test, every AC maps to a test
- [Source: tools/hooks/_events.py] — `read_active_story()`, `write_atomic_json()`, `emit()` (with `story_override`), `update_active_story()`, `record_activity()`, `_now()` to reuse as-is
- [Source: tools/hooks/git/post-checkout.py] — existing `branch_checkout` gating and `update_active_story()` call this story branches around
- [Source: tools/hooks/claude/session_start.py, tools/hooks/claude/session_end.py] — existing hook structure and unconditional `return 0` convention
- [Source: tests/hooks/test_active_story.py, tests/hooks/test_git_hooks.py, tests/hooks/test_claude_hooks.py] — existing fixture/monkeypatch pattern to follow

## Dev Agent Record

### Agent Model Used

claude-sonnet-5

### Debug Log References

- Live E2E: real temp git repo, two committed branches (story-a, story-b), real hooks via `uv run --script`. `session_start` (story-a) → opens slice. Mid-session `git checkout` to story-b via real `post-checkout.py` → pointer's `story_id` becomes `story-b`, `opened_at` unchanged, no `time.slice_closed`/`time.slice_opened` for the repoint (confirmed via the full event log — only `git.checkout` logged). `session_end` → exactly one `time.slice_closed` appears, attributed to `story-b` (the story the pointer named at that moment), `.active-story` deleted afterward.

### Completion Notes List

- Added a second small pointer file, `.active-claude-session` (`{"session_id"}`), tracking whether a Claude Code session is currently live — deliberately separate from `.active-story` (different question: "is a session open" vs. "which story"), matching Stories 3.1/3.2's one-function-one-concern discipline.
- `update_active_story()` (3.1) and `record_activity()` (3.2) are completely unchanged. New, narrower siblings added: `repoint_active_story()` (story_id-only rewrite, no events, used by a mid-session checkout), `close_active_story_slice()` (emits `time.slice_closed` and deletes the pointer, wired to `SessionEnd`), `mark_session_active()`/`mark_session_inactive()`/`is_session_active()`.
- `post-checkout.py` now branches on `is_session_active()`: live session → `repoint_active_story()`; no session → `update_active_story()` unchanged from Story 3.1. All of Story 3.1's original `post-checkout` tests pass unmodified (no session marker exists in those fixtures, so they naturally take the unchanged branch).
- `session_end.py` gets real behavior for the first time since Story 2.3: it now actually closes the active slice via `close_active_story_slice()` (previously, a slice only ever closed lazily, the next time the pointer needed to switch to a different story) — this completes the AD-7 rule ("a session-level slice only opens/closes on SessionStart/SessionEnd") that was written into the architecture before Epic 3 was ever implemented.
- Updated 3 existing tests (`test_event_types_are_namespaced_per_hook`, the always-fails-append count, `test_branch_checkout_*` was extended, not altered) whose event-count/type-list assertions were invalidated by `session_end` now emitting `time.slice_closed` — legitimate behavior change (AC 1), assertions extended not weakened, same pattern Stories 3.1/3.2 already established.
- Ran both `ruff format --check` and `ruff check` before pushing this time (Story 3.2's PR #17 CI lesson) — caught and fixed 2 files needing reformatting locally, before any CI round-trip.
- Full suite: 215 passed, 0 regressions. `ruff format --check` and `ruff check` both clean.

### File List

- `tools/hooks/_events.py` (modified — `is_session_active()`, `mark_session_active()`, `mark_session_inactive()`, `repoint_active_story()`, `close_active_story_slice()`, `ACTIVE_SESSION_FILE`)
- `tools/hooks/git/post-checkout.py` (modified — branches on `is_session_active()`)
- `tools/hooks/claude/session_start.py` (modified — calls `mark_session_active()`)
- `tools/hooks/claude/session_end.py` (modified — calls `close_active_story_slice()` then `mark_session_inactive()`)
- `tests/hooks/test_active_story.py` (modified — 10 new tests for the marker + repoint + close functions)
- `tests/hooks/test_git_hooks.py` (modified — 2 new tests for post-checkout precedence)
- `tests/hooks/test_claude_hooks.py` (modified — 3 new tests; 2 existing assertions extended for the new `time.slice_closed` on session_end)
- `.gitignore` (modified — added `.active-claude-session`)
- `_bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md` (modified — AD-7 precedence-implementation documentation)
