---
baseline_commit: eca6162962847ef3ae2efe5db4d7d5efda8f3611
---

# Story 3.4: Snapshot Assembler Reduces Idle-Aware Time Slices into Real Active-Time Duration

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As someone reviewing the dashboard,
I want a story's reported duration to reflect actual active work time, not the calendar span between its first and last commit,
So that a story left open across days (or interleaved with meetings/other stories) doesn't report a wildly inflated duration and cost.

## Acceptance Criteria

1. **Given** a story's event log contains one or more `time.slice_opened` → `time.slice_paused`(0+) → `time.slice_closed` sequences
   **When** the snapshot assembler reduces the story at close time
   **Then** `estimated_cost.duration_minutes` is computed from the sum of each slice's `duration_seconds` minus that slice's own `slice_paused.idle_seconds` — not the raw first/last-event span
2. **Given** a story is closed while an AI session is still open (a dangling `time.slice_opened` with no matching `time.slice_closed` yet)
   **When** the assembler runs
   **Then** it falls back to the existing raw-span calculation — never a fabricated or silently-wrong active-time number
3. **Given** an older snapshot or an `ai_tool` whose hooks don't emit `time.slice_*` events (i.e. zero `time.slice_closed` events observed for this story)
   **When** the assembler reduces it
   **Then** behavior is unchanged from today (raw first/last-event span) — this story only improves the calculation when the richer signal exists, it never removes the existing fallback
4. **And** `INSTALL.md`'s "Known limitations" entry for `Duration`/`estimated_cost` is narrowed to describe only the remaining caveat (a mid-session story switch via `repoint_active_story()` still attributes a slice's whole time to whichever story was active when the AI session finally closes — the same session-vs-story blending `token_cost` already has, for time instead of dollars)

## Tasks / Subtasks

- [x] Task 1: add the idle-aware active-time reducer to `tools/snapshot-assembler/main.py` (AC: 1, 2, 3)
  - [x] Subtask 1.1 (RED): write failing tests in `tests/snapshot_assembler/test_reduce.py` for a new function `active_time_seconds_of(events) -> dict`:
    - Returns `{"active_seconds": float, "reason": None}` when at least one `time.slice_closed` event exists for the story: walk all `time.*` events sorted by `timestamp`; for each `time.slice_opened` → (0+) `time.slice_paused`) → `time.slice_closed` run, take that `slice_closed`'s own `duration_seconds` payload field and subtract the sum of `idle_seconds` from every `slice_paused` seen since the matching `slice_opened`; sum this across every completed run in the log (a story can have multiple sessions, hence multiple runs)
    - A dangling `time.slice_opened` with no later `time.slice_closed` contributes nothing to the sum (its time isn't lost, just not yet observed — same "not lost, just absent until session ends" philosophy `token_cost` already documents) and does **not** by itself cause a `reason` — the function only reports a `reason` when it has **zero** usable data
    - Returns `{"active_seconds": None, "reason": "no completed time slice observed for this story"}` when zero `time.slice_closed` events exist at all (covers both "no time-tracking hooks ever fired" and "session never closed")
    - Malformed/missing `duration_seconds` or `idle_seconds` on an individual event degrades that one contribution to 0 rather than raising (matches this codebase's existing null-safety style — see `token_cost_of`'s `usage.get(...) or 0` pattern)
  - [x] Subtask 1.2 (GREEN): implement `active_time_seconds_of()` — pure function over the already-filtered `ours` event list, no new I/O, no new files, sibling to `token_cost_of`/`defect_metrics_of` in the same module
  - [x] Subtask 1.3 (RED then GREEN): extend `estimated_cost_of()`'s existing tests (`test_estimated_cost_computed_when_hourly_rate_is_configured` and neighbors) plus new tests: when `active_time_seconds_of()` returns a non-null `active_seconds`, `duration_minutes` is computed from it (`active_seconds / 60`), not from `first_event_at`/`last_event_at`; when it returns `None` (no completed slices), `estimated_cost_of()` falls back to today's raw-span calculation exactly as-is, unchanged — no new `reason` string is introduced for this fallback path, since it is silent-by-design (same as the tool's behavior before this story existed)
  - [x] Subtask 1.4: wire `active_time_seconds_of(ours)`'s result into the existing `estimated_cost_of(engineering_metrics, config)` call site — either pass the events list into `estimated_cost_of` directly (its signature currently only takes `engineering_metrics`, so this is a signature change: add an `events` parameter) or compute `active_time_seconds_of()` once at the call site in `main()`/`build_snapshot()` and pass the result in; pick whichever keeps `estimated_cost_of()`'s existing tests (rate-absent, no-events, offset-naive/aware) passing unmodified except for the new duration source — do not change the `estimated_cost` envelope's key set (`usd`, `hourly_rate`, `duration_minutes`, `reason`), only how `duration_minutes` is derived

- [x] Task 2: full regression, live E2E (AC: 1, 2, 3)
  - [x] Subtask 2.1: run `uv run pytest` (337 passing today — confirm no regressions) plus `uv run ruff format --check tools tests` and `uv run ruff check tools tests` (both gates, per the Story 3.2 PR #17 CI lesson repeated in every Epic 3 story since)
  - [x] Subtask 2.2: live E2E in a real temp git repo — kick off a story, do a short burst of activity (a commit, a couple of tool uses), let the AI session close (`session_end.py` via `uv run --script`) so a real `time.slice_closed` lands in the log, then run `snapshot-assembler` and confirm `estimated_cost.duration_minutes` matches the slice's own `duration_seconds` (not the full first/last-event span, which should now differ if there was any gap between event capture and session close)
  - [x] Subtask 2.3: live E2E for the fallback path — a story whose event log has git/AI activity events but **no** `time.slice_closed` at all (e.g. hooks fired but the session was killed abruptly, never hitting `SessionEnd`) — confirm `estimated_cost.duration_minutes` still equals the old raw first/last-event span, unchanged

- [x] Task 3: documentation parity (AC: 4)
  - [x] Subtask 3.1: in `tools/build-release/INSTALL.md`'s "Known limitations" section, replace the `Duration`/`estimated_cost` entry added in v0.9.1 with a narrower one describing only the remaining caveat: a mid-session story switch (`repoint_active_story()`, Story 3.3) still attributes a slice's *entire* duration to whichever story was active when the session finally closes — Story A worked first, then repointed to Story B without closing the session, gets `0` seconds of that session's active time; Story B gets all of it. This is the same session-vs-story blending limitation `token_cost` already documents, just for time instead of dollars — word it as a sibling of that existing paragraph, don't duplicate the whole explanation
  - [x] Subtask 3.2: `_bmad-output/planning-artifacts/epics.md`'s Story 3.4 entry gets the same "✅ Complete" treatment as 3.1-3.3 once done, with a PR link

## Dev Notes

### Why this story exists

Found live during leadership Q&A prep (2026-07-15), not a customer-reported bug: `tools/snapshot-assembler/main.py`'s `estimated_cost_of()` computes `duration_minutes` as a raw `last_event_at - first_event_at` span. Epic 3 (Stories 3.1-3.3) already built exactly the idle-aware signal needed to do this properly — `time.slice_opened`, `time.slice_paused` (gap > `IDLE_THRESHOLD_SECONDS`, default 900s/15min), `time.slice_closed` (carries its own `duration_seconds`) — but nothing downstream ever reads those events. The capture side is complete; this is purely a reducer gap. Documented as a stopgap "Known limitation" in `INSTALL.md` when `v0.9.1` shipped; this story is the actual fix.

### Current state of the two files this story touches

**`tools/hooks/_events.py`** (read-only for this story — do not modify; Stories 3.1-3.3 already close this out):
- `update_active_story(root, incoming_story_id)` (Story 3.1): on a story switch (no live session), closes the outgoing story's slice — emits `time.slice_closed` with `{opened_at, closed_at, duration_seconds}`, `story_override` set to the **outgoing** story's id — then opens a new slice for the incoming story, emitting `time.slice_opened` with `{opened_at}`.
- `record_activity(root)` (Story 3.2): on every `PostToolUse`/prompt signal, if the gap since `last_activity_at` exceeds `IDLE_THRESHOLD_SECONDS`, emits `time.slice_paused` with `{quiet_since, resumed_at, idle_seconds}`, `story_override` set to the pointer's **current** story id. Does not close or open a slice — the story stays "active," just flags an idle gap that already happened.
- `repoint_active_story(root, incoming_story_id)` (Story 3.3): mid-session checkout while a Claude Code session is live — rewrites only the pointer's `story_id`, preserves `opened_at`, emits **no** `time.slice_*` event at all. This is the mechanism behind the "remaining caveat" this story's AC 4 documents (not something to fix here).
- `close_active_story_slice(root)` (Story 3.3): wired to `SessionEnd` — emits one final `time.slice_closed` for whatever story the pointer currently names, then deletes `.active-story`.

Net effect on the event log: for a given story, you'll see zero or more complete `(slice_opened, [slice_paused...], slice_closed)` runs — one run per AI session that had this story active for at least part of its lifetime. **Read all three Epic 3 story files in full before starting** (`3-1-*.md`, `3-2-*.md`, `3-3-*.md`, especially 3.3's Dev Notes on `story_override` and the precedence rule) — this story's entire job is correctly consuming what those three already built.

**`tools/snapshot-assembler/main.py`** (the only file this story actually changes):
- `reduce_events(events)` (~line 166): produces `engineering_metrics`, including `first_event_at`/`last_event_at` from **all** event types, not just `time.*` — this function is unrelated to this story's change and must not be touched.
- `token_cost_of(events, config)` (~line 186): sibling reducer this story's new function should match in style — same "collect known values, compute only when all required inputs are present, otherwise null-with-reason" shape (AD-10).
- `estimated_cost_of(engineering_metrics, config)` (~line 288): **this is what changes**. Today: `duration_minutes = (last_event_at - first_event_at) / 60` (with the existing `except (ValueError, TypeError)` guard for offset-naive/aware mismatches — a real review-caught defect from PR #26, do not regress this guard). This story adds a second data source (the new `active_time_seconds_of()`) that takes priority when available, with the existing raw-span math staying as the fallback path, unchanged.
- `defect_metrics_of(events)` (~line 249): another sibling reducer to match in style (null-with-reason on zero-data, real fields otherwise).
- Where reducers are called: `main()`/`build_snapshot()` around line 452-472 — `engineering_metrics = reduce_events(ours)`, then `token_cost_of(ours, config)`, `estimated_cost_of(engineering_metrics, config)`, `defect_metrics_of(ours)`. `ours` is the full filtered event list for this story — `active_time_seconds_of()` should be called the same way (`active_time_seconds_of(ours)`), then its result threaded into `estimated_cost_of()`.

### Design decisions already made (don't re-litigate these)

- **No new envelope field.** `estimated_cost` keeps its existing four keys (`usd`, `hourly_rate`, `duration_minutes`, `reason`) — this story only changes how `duration_minutes` is computed internally, matching AC 1-3's wording exactly. Adding a new top-level key would be scope creep and isn't needed for the AC.
- **The fallback path is silent, not a new `reason`.** When zero `time.slice_closed` events exist for a story, `duration_minutes` falls back to the pre-existing raw-span calculation exactly as before — this is not an error state (plenty of real snapshots, including every pilot one captured before this story, will never have `time.slice_*` events and are expected to keep working exactly as today). Only genuine "can't compute at all" cases (no `hourly_rate` configured, no events at all) keep their existing `reason` strings.
- **A dangling open slice at close time is not a `reason` either.** If a story is closed via CLI while the AI session is still open, there is a real `time.slice_opened` with no matching `time.slice_closed` yet. That run's time is simply not counted — not lost forever, just not observable at this point in time (identical philosophy to `token_cost`'s existing "not lost, just absent until session ends" handling). If *some* other run for this story did close, use that partial sum; only report the "no completed time slice observed" reason when there are truly zero completed runs.
- **AD-7's "remaining caveat" (AC 4) is explicitly out of scope to fix, only to document.** A mid-session repoint (Story 3.3) still means one AI session's *entire* slice duration lands on whichever story was active at `SessionEnd` time, not split proportionally across the stories actually touched during that session. Splitting that fairly would need per-repoint sub-slice tracking — a real feature, not something to sneak into this story. This story's job is only to make the *already-closed, already-attributed* slices sum correctly into a real active-time number; the attribution-across-stories question stays exactly where Story 3.3 left it.

### Testing standards (project-context.md §5/§6)

One behavior per test. No real git operations, no real Claude Code process, no real sleeps. Follow `tests/snapshot_assembler/test_reduce.py`'s existing fixture pattern exactly:
- `event(event_type, story_id=STORY_ID, ts=..., **payload)` builds a single event dict (source is inferred from the type prefix — note `time.*` events aren't `git.`/`ai.` prefixed, so check how `event()`'s `source` inference handles that; `time.*` events use `source="time"` per `_events.py`'s `emit("time", ...)` calls — you may need to extend the test helper's source-inference branch for the `time.` prefix, it currently only branches on `git.`/`ai.` vs. everything-else-is-`opsx`)
- `write_events(root, events)` writes the `.story-events.jsonl` fixture
- `run(root)` invokes the assembler's `main()`
- `read_snapshot(root)` reads back the written snapshot JSON
- Reuse `write_story_config(root, hourly_rate=10)` for the cost-computation tests

Boundary-test the idle threshold the same way Story 3.2 did for its own idle-pause logic (14/15/16-minute-equivalent `idle_seconds` values), even though the threshold itself is computed and enforced upstream in `_events.py` (unchanged) — this story's own new tests should at minimum confirm that whatever `idle_seconds` a `time.slice_paused` event carries gets subtracted correctly, regardless of its specific value.

### Project Structure Notes

- Extends (does not create new modules): `tools/snapshot-assembler/main.py`.
- Extends existing test file: `tests/snapshot_assembler/test_reduce.py`.
- Updates existing docs: `tools/build-release/INSTALL.md` ("Known limitations"), `_bmad-output/planning-artifacts/epics.md` (Story 3.4 entry, mark complete on done).
- No new runtime artifacts, no new hooks, no new git-ignored state files — this story is entirely inside the reducer, `tools/hooks/_events.py` is untouched.
- No conflicts with the unified project structure; surface area stays inside `tools/snapshot-assembler/` and `tests/snapshot_assembler/`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.4: Snapshot Assembler Reduces Idle-Aware Time Slices into Real Active-Time Duration] — AC text
- [Source: _bmad-output/implementation-artifacts/3-1-active-story-pointer-tracks-time-automatically.md], [3-2-idle-time-doesnt-inflate-a-storys-active-time.md], [3-3-mid-session-checkout-doesnt-double-count-time.md] — the full mechanics `time.slice_*` events are emitted under; read all three before starting
- [Source: tools/hooks/_events.py] — `update_active_story()`, `record_activity()`, `repoint_active_story()`, `close_active_story_slice()`, `IDLE_THRESHOLD_SECONDS` — read-only reference, not modified by this story
- [Source: tools/snapshot-assembler/main.py] — `reduce_events()`, `token_cost_of()`, `defect_metrics_of()` (sibling reducers to match in style), `estimated_cost_of()` (the function this story changes)
- [Source: tests/snapshot_assembler/test_reduce.py] — existing fixture pattern (`event()`, `write_events()`, `run()`, `read_snapshot()`, `write_story_config()`), and the existing `test_estimated_cost_*` tests this story extends
- [Source: tools/build-release/INSTALL.md#Known limitations] — the v0.9.1 stopgap entry this story narrows (AC 4)
- [Source: _bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md#AD-7 — Time-on-task via an explicit active-story pointer] — the architecture rule this story's calculation ultimately serves
- [Source: project-context.md#2. Code Standards] — atomic writes n/a here (no I/O added), small single-purpose functions, no premature abstraction
- [Source: project-context.md#6. Unit Testing Standards] — one behavior per test, every AC maps to a test, boundary-test numeric thresholds

## Dev Agent Record

### Agent Model Used

claude-sonnet-5

### Debug Log References

- Full suite: 343 passed (up from 337; +6 new tests), 0 regressions. `ruff format --check` and `ruff check` both clean after one auto-format pass.
- Live E2E (real hook subprocess calls via `uv run --script`, not unit tests): a real temp git repo, real `session_start.py` → `pre_tool_use.py`/`post_tool_use.py` → `session_end.py` sequence produced a genuine `time.slice_closed` event (`duration_seconds: 6.406252`). Running the real `snapshot-assembler` against that log produced `estimated_cost.duration_minutes == 0.10677086666666667`, exactly `6.406252 / 60` — confirming the new active-time path is actually wired end-to-end, not just unit-tested.
- Live E2E for the fallback path: a second temp repo with `session_start.py` + one `post_tool_use.py` call but **no** `session_end.py` (simulating an abrupt session kill — no `time.slice_closed` ever recorded). `snapshot-assembler` correctly fell back to the raw `first_event_at`/`last_event_at` span (`duration_minutes == 0.05`, matching the real 3-second gap between the two real events) — confirming the pre-existing behavior is genuinely unchanged when no completed slice exists.

### Completion Notes List

- Added `active_time_seconds_of(events)` to `tools/snapshot-assembler/main.py`, a pure reducer sibling to `token_cost_of`/`defect_metrics_of`: walks `time.slice_opened`/`time.slice_paused`/`time.slice_closed` events in timestamp order, subtracting each `slice_paused`'s `idle_seconds` from its enclosing slice's `duration_seconds`, summing across every completed run for the story. Returns `active_seconds: None` with a reason only when zero `time.slice_closed` events exist at all — a dangling open slice at story-close time contributes 0 for that run but doesn't trigger the null-reason path if another run for the same story did complete.
- `estimated_cost_of()` gained an `events` parameter; it now prefers `active_time_seconds_of()`'s result when non-null, falling back to the original raw first/last-event span calculation (byte-for-byte the same code path as before this story) when it's null. The `estimated_cost` envelope's key set is unchanged (`usd`, `hourly_rate`, `duration_minutes`, `reason`) — only how `duration_minutes` is derived changed. The existing offset-naive/offset-aware `TypeError` guard (PR #26 review finding) is preserved verbatim in the fallback branch.
- Test helper `event()` in `tests/snapshot_assembler/test_reduce.py` gained a `time.` → `source: "time"` branch (previously fell through to `opsx`, harmless for reducer logic since reducers key off `type` not `source`, but incorrect and worth fixing while touching this file).
- 6 new tests: idle-excluded summation across multiple slices, null-with-reason on zero completed slices, dangling-open-slice-contributes-zero, malformed `duration_seconds` degrades to 0 without raising, `estimated_cost_of` prefers active time when slices exist, `estimated_cost_of` falls back to raw span when they don't (this last one already passed before any code change, confirming the fallback truly is byte-identical to pre-3.4 behavior).
- Narrowed `INSTALL.md`'s "Known limitations" `Duration`/`estimated_cost` entry (added in v0.9.1 as a stopgap) to describe only the remaining caveat: a mid-session story switch via `repoint_active_story()` (Story 3.3) still attributes a whole session's active time to whichever story was active when the session finally closes, mirroring `token_cost`'s existing session-vs-story blending limitation. Splitting time proportionally across a mid-session repoint is a real feature, deliberately out of scope for this story (see Dev Notes' "design decisions already made").

### File List

- `tools/snapshot-assembler/main.py` (modified — new `active_time_seconds_of()`, `estimated_cost_of()` signature and duration-source logic changed, call site updated to pass `ours`)
- `tests/snapshot_assembler/test_reduce.py` (modified — `event()` helper's source inference extended for `time.*`; 6 new tests added)
- `tools/build-release/INSTALL.md` (modified — "Known limitations" `Duration`/`estimated_cost` entry narrowed)
- `_bmad-output/planning-artifacts/epics.md` (modified — Story 3.4 marked complete, pending PR link)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified — `3-4-*` and `epic-3` status updates)
