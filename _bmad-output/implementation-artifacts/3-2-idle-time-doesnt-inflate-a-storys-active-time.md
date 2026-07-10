---
baseline_commit: 59bd46a4eb82b9422ee2ce57247c5c973b19ebd5
---

# Story 3.2: Idle Time Doesn't Inflate a Story's Active Time

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want idle periods (meetings, breaks) excluded from my active time,
So that time-on-task reflects real work, not an open session.

## Acceptance Criteria

1. **Given** an active time slice from Story 3.1
   **When** there is no `PostToolUse`/prompt activity for a configurable idle threshold (default: exactly 15 minutes)
   **Then** the active slice auto-pauses (AD-7)

## Tasks / Subtasks

- [x] Task 1: Extend the shared active-story pointer with activity tracking + idle detection in `tools/hooks/_events.py` (AC: 1)
  - [x] Subtask 1.1 (RED): write failing tests in `tests/hooks/test_active_story.py` for a new `record_activity(root)` function: first-ever activity call (pointer exists from Story 3.1, no `last_activity_at` yet) just stamps `last_activity_at = now` on the pointer, no `time.slice_paused` event; a second activity call within the idle threshold of the previous `last_activity_at` just re-stamps `last_activity_at`, still no event; a call where the gap since `last_activity_at` *exceeds* the idle threshold emits exactly one `time.slice_paused` event (payload: `quiet_since`, `resumed_at`, `idle_seconds`) attributed to the current pointer's story_id, then re-stamps `last_activity_at = now` (the slice keeps running under the same story — no story switch, no pointer file story_id change); a call with no active-story pointer at all (nothing to pause) is a no-op — no file write, no event
  - [x] Subtask 1.2: **boundary-test the threshold exactly at 14/15/16 minutes** (project-context.md §6) — 14:59 gap does not emit, 15:00 gap is the implementation's own choice of boundary (document whichever side you land on: `>` vs `>=`), 15:01 gap emits. Freeze "now" and the stored `last_activity_at` via literal ISO timestamps in the test (not real sleeps) so the test suite stays fast and deterministic
  - [x] Subtask 1.3 (GREEN): implement `record_activity(root)` in `_events.py`. Add `IDLE_THRESHOLD_SECONDS = 900` (15 minutes) as a module constant, overridable via the `STORY_IDLE_THRESHOLD_SECONDS` environment variable — this is what makes the threshold "configurable" per the AC, and needs no new config-loading mechanism (stdlib `os.environ`, consistent with project-context.md §1's stdlib-only rule). Extend the `.active-story` JSON pointer with an optional `last_activity_at` field (added by this story; `opened_at`/`story_id` are unchanged from Story 3.1). Reuse `read_active_story()`, `write_atomic_json()`, and `emit()` (with `story_override` — same pattern Story 3.1 introduced for `time.slice_closed`/`time.slice_opened`) — do not reimplement any pointer I/O or event-append logic
  - [x] Subtask 1.4 (REFACTOR): confirm `record_activity()` never changes the pointer's `story_id` and never emits `time.slice_closed`/`time.slice_opened` — pausing is a distinct concept from switching stories (Story 3.1's territory); this function owns exactly one new pair of concerns: "was there a gap" and "stamp the latest activity time"

- [x] Task 2: Wire activity signals — `tools/hooks/claude/post_tool_use.py` and `tools/hooks/claude/user_prompt_submit.py` (AC: 1)
  - [x] Subtask 2.1 (RED): extend `tests/hooks/test_claude_hooks.py` — after an open slice (from a prior `session_start`), a `post_tool_use` call more than the idle threshold after the pointer's `last_activity_at` appends a `time.slice_paused` event; the same for `user_prompt_submit`; a call within the threshold appends no such event; a call with no prior active-story pointer is a no-op (mirrors `record_activity`'s own no-op case)
  - [x] Subtask 2.2 (GREEN): call `_events.record_activity(_events.repo_root())` unconditionally in both hooks' `main()`, alongside (not replacing) their existing `ai.claude-code.tool_use` / `ai.claude-code.prompt` emissions. Keep both hooks' unconditional `return 0` exit behavior

- [x] Task 3: Full regression and documentation parity (AC: 1)
  - [x] Subtask 3.1: run the full test suite (`uv run pytest`) — confirm no regression in `test_active_story.py` (Story 3.1) or elsewhere
  - [x] Subtask 3.2: update `ARCHITECTURE-SPINE.md`'s AD-7 section with the concrete idle-detection mechanics this story introduces: the extended `.active-story` shape (`last_activity_at`), the `time.slice_paused` event shape, the `IDLE_THRESHOLD_SECONDS` default/override mechanism, and the fact that idle detection is event-driven/retrospective (checked on the *next* activity signal) rather than a running timer — this project has no background service (AD-2), so there is no daemon watching the clock in real time; the "15 minutes of silence" is only detectable in arrears, the next time something happens

## Dev Notes

- **This is the second story in Epic 3** — Story 3.1 (`_bmad-output/implementation-artifacts/3-1-active-story-pointer-tracks-time-automatically.md`) is the direct predecessor and established everything this story builds on. Read it in full before starting; the summary below is not a substitute.
- **Previous story intelligence (Story 3.1):**
  - `update_active_story(root, incoming_story_id)` in `tools/hooks/_events.py` (currently at line ~201) is the story-switch mechanism — **do not touch its behavior**. This story adds a sibling function, `record_activity()`, for a different trigger (idle gap, not story switch).
  - `.active-story` is currently `{"story_id": str, "opened_at": iso8601}`, written via `write_atomic_json()` (line ~181) and read via `read_active_story()` (line ~191). This story is the one that gets to extend that shape — Story 3.1's dev notes explicitly deferred `last_activity_at` to "whichever story needs it next," which is this one. Add the field; do not restructure the existing two.
  - `emit()` (line ~158) already supports an explicit `story_override` parameter (added in Story 3.1 specifically so `time.*` events could be attributed to a story that isn't necessarily what `.story.yaml` currently says) — reuse it exactly the same way for `time.slice_paused`.
  - Story 3.1 also established the "no real git/no real Claude Code process" test fixture pattern in `tests/hooks/test_active_story.py` and `tests/hooks/test_claude_hooks.py` (`monkeypatch` on `events.repo_root`, `events.read_stdin_json`, `events.RETRY_DELAY_SECONDS`) — follow it exactly, do not introduce a different mocking style.
  - Story 3.1's PR review (Gemini, PR #16) surfaced one **misattributed finding** (a bullet about binary-file `git show --stat` parsing that actually belonged to Story 2.6, not 3.1) — worth remembering that this reviewer has previously produced content not about the diff in front of it; grep-verify any finding against this story's actual changed files before acting on it.
- **What this story is explicitly NOT** (scope boundary, avoid drift into Story 3.3's territory): this story never switches the active story_id and never touches `git post-checkout`/`session_start`'s calls to `update_active_story()`. It only adds a *second*, independent signal path (`record_activity`) that can emit a `time.slice_paused` marker while the *same* story stays active. Story 3.3 (mid-session checkout precedence) is the one that changes how `post-checkout` and Claude session boundaries interact — don't pre-solve it here.
- **Idle detection is inherently retrospective, not real-time** (important framing for the dev agent): per AD-2, there is no running background service/daemon in this architecture — every producer only runs when a hook fires. This means "15 minutes of silence" can only ever be *detected* the next time some activity happens (a `PostToolUse` or a prompt), by comparing "now" to the stored `last_activity_at`. There is no mechanism (and none is needed for this AC) to proactively pause a slice the instant the 15-minute mark passes with nobody touching the keyboard — the pause is recorded, with an honest `quiet_since`/`resumed_at`/`idle_seconds` payload, as soon as the developer's next action reveals how long the gap actually was.
- **Why `record_activity()` is a new function, not folded into `update_active_story()`:** the two answer different questions — "should the active story change" (Story 3.1) vs. "has enough silence passed since the last activity signal that the elapsed time shouldn't count as active" (this story). Keeping them as separate single-purpose functions matches project-context.md §2's "small, single-purpose functions" rule and avoids the one function growing branches for two unrelated triggers.
- **Configurability via environment variable, not a new config file:** AD-4's `source_of_truth` project-config pattern exists for PM-tool adapter selection, not for hook-runtime tuning knobs — inventing a parallel project-config file just for one threshold would be the kind of premature abstraction project-context.md §2 warns against. An environment variable (`STORY_IDLE_THRESHOLD_SECONDS`, defaulting to 900) is the minimal mechanism that satisfies "configurable," is stdlib-only (project-context.md §1), and is trivially testable via `monkeypatch.setenv`.
- **Testing standards (project-context.md §5/§6):** no real sleeps, no real clocks — freeze timestamps as literal ISO strings passed into the pointer fixture and compare against a monkeypatched or literal "now." One behavior per test. Boundary-test the exact threshold (14/15/16 minutes) per §6's explicit example for this exact AD-7 threshold.

### Project Structure Notes

- Extends (does not create new modules): `tools/hooks/_events.py`, `tools/hooks/claude/post_tool_use.py`, `tools/hooks/claude/user_prompt_submit.py`.
- Extends existing test files (no new test file needed this time, unlike Story 3.1's `test_active_story.py` which already exists and is the right home for `record_activity()`'s own unit tests): `tests/hooks/test_active_story.py`, `tests/hooks/test_claude_hooks.py`.
- No conflicts with the unified project structure; surface area stays inside `tools/hooks/` and `tests/hooks/`, consistent with Stories 2.x and 3.1.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2: Idle Time Doesn't Inflate a Story's Active Time] — AC text
- [Source: _bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md#AD-7 — Time-on-task via an explicit active-story pointer] — idle-timeout rule, PostToolUse/prompt activity signals, and the Story 3.1-added wire-format note this story extends
- [Source: _bmad-output/implementation-artifacts/3-1-active-story-pointer-tracks-time-automatically.md] — predecessor story; `update_active_story()`, `.active-story` shape, `emit()`'s `story_override`, test fixture conventions
- [Source: project-context.md#1. Language & Framework Standards] — stdlib-only rule (env var over new config mechanism)
- [Source: project-context.md#2. Code Standards] — atomic writes, small single-purpose functions, no premature abstraction
- [Source: project-context.md#6. Unit Testing Standards] — explicit boundary-testing example for this exact 15-minute threshold
- [Source: tools/hooks/_events.py] — `read_active_story()`, `write_atomic_json()`, `emit()` (with `story_override`) to reuse as-is
- [Source: tools/hooks/claude/post_tool_use.py, tools/hooks/claude/user_prompt_submit.py] — existing hook structure and unconditional `return 0` convention
- [Source: tests/hooks/test_active_story.py, tests/hooks/test_claude_hooks.py] — existing fixture/monkeypatch pattern to follow

## Dev Agent Record

### Agent Model Used

claude-sonnet-5

### Debug Log References

- Live E2E #1: real hooks (`session_start.py`, `post_tool_use.py`) via `uv run --script` against a real repo directory, immediate succession (no idle gap) — confirmed `last_activity_at` stamps correctly with no spurious `time.slice_paused`.
- Live E2E #2: same, with `STORY_IDLE_THRESHOLD_SECONDS=1` and a real 2-second `sleep` between `session_start` and `user_prompt_submit` — confirmed a real `time.slice_paused` event with an accurate real `idle_seconds`, proving the env-var override path end-to-end, not just the mocked-clock unit tests.

### Completion Notes List

- Implemented `record_activity()` as a sibling to Story 3.1's `update_active_story()` — same `.active-story` pointer, same `emit()`/`write_atomic_json()` reuse, but a distinct concern (idle gap vs. story switch); it never touches `story_id` and never emits `time.slice_closed`/`time.slice_opened`.
- Extracted a small `_now()` wrapper (`datetime.now().astimezone()`) in `_events.py` so both `update_active_story()` and `record_activity()` share one mockable time source for tests — a minor refactor of Story 3.1's code, behavior-preserving (verified: all of Story 3.1's original tests still pass unchanged).
- `IDLE_THRESHOLD_SECONDS` defaults to 900 (15 min), overridable via `STORY_IDLE_THRESHOLD_SECONDS` env var — deliberately not a new project-config file (would be premature abstraction for one tuning knob).
- Boundary chosen: gap must be strictly *greater than* the threshold to pause (a gap of exactly 900s does not pause) — boundary-tested at 14:59/15:00/15:01-equivalent gaps.
- Wired into `post_tool_use.py` and `user_prompt_submit.py` only (per AD-7's named signals); `pre_tool_use.py`/`session_end.py`/`stop.py` are untouched.
- Full suite: 198 passed (11 new in `test_active_story.py`, 4 new in `test_claude_hooks.py`), 0 regressions. `ruff check` clean on all touched files.

### File List

- `tools/hooks/_events.py` (modified — `record_activity()`, `_now()`, `IDLE_THRESHOLD_SECONDS`; `update_active_story()` refactored to use `_now()`)
- `tools/hooks/claude/post_tool_use.py` (modified — calls `record_activity()`)
- `tools/hooks/claude/user_prompt_submit.py` (modified — calls `record_activity()`)
- `tests/hooks/test_active_story.py` (modified — 6 new tests for `record_activity()`)
- `tests/hooks/test_claude_hooks.py` (modified — 4 new tests for the idle-detection wiring)
- `_bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md` (modified — AD-7 idle-detection documentation)
