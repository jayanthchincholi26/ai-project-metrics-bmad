---
baseline_commit: eabe892
---

# Story 3.5: Raw-Span Fallback Excludes Bookkeeping Events

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As someone reviewing the dashboard,
I want the raw-span fallback duration to reflect real developer activity, not administrative/bookkeeping actions,
so that a story's reported duration/cost isn't inflated by an unrelated later command that happens to touch the same story_id.

## Acceptance Criteria

1. **Given** the raw-span fallback is in effect for a story (no completed `time.slice_*` sequence exists — `active_time_seconds_of()` returned `active_seconds: None`)
   **When** `estimated_cost_of()` computes the fallback span
   **Then** only genuine bookkeeping event types are excluded from the timestamp scan — `opsx.*`, `ai.<tool>.session_start`, `ai.<tool>.session_end`, `time.*` — every other event type (`git.*` and all remaining `ai.<tool>.*` activity, e.g. `prompt`/`tool_use`/`tool_start`/`stop`/`defect_compile`/`defect_test`/`defect_review`) still counts, so genuine activity signals are never undercounted

2. **Given** a story whose *only* events are bookkeeping ones (e.g. a kickoff immediately followed by an archive, no real work event in between at all)
   **When** the assembler computes the raw-span fallback
   **Then** it degrades to `estimated_cost.usd: null` with `reason: "no events to compute duration from"` (the existing AD-10 null-with-reason path, reused, not a new one) rather than a fabricated zero or a misleading span computed from bookkeeping-only timestamps

3. **Given** this fix
   **When** a re-run of the assembler/wrapper happens well after a story's real work concluded (the exact scenario that surfaced this finding — an `opsx.archive` event landing hours after real work stopped)
   **Then** `estimated_cost`/`duration_minutes` for that story are unaffected by the timing of that later re-run

4. **Given** Story 3.4's real-slice path (a completed `time.slice_*` sequence exists, `active_time_seconds_of()` returns a real `active_seconds`)
   **When** the assembler computes duration
   **Then** behavior is unchanged — this story only narrows the *fallback* path's event selection; it never touches `active_time_seconds_of()` or the idle-aware active-time calculation

5. **Given** `engineering_metrics.first_event_at`/`last_event_at` (the whole-story span, any event type, used elsewhere — e.g. `metrics-report`'s own duration fallback for pre-Story-5.2 snapshots)
   **When** this fix ships
   **Then** those two fields are **unchanged** — this story adds a separate, activity-only span computed *only* inside `estimated_cost_of()`'s fallback branch; it does not redefine what `engineering_metrics.first_event_at`/`last_event_at` mean

## Tasks / Subtasks

- [ ] Task 1: activity-only span helper (AC: 1, 2, 5)
  - [ ] Subtask 1.1 (RED): add a test with a `standard_log()`-style real activity window (a `prompt` at T0, a `tool_use` at T0+2min, a `git.commit` at T0+5min — no `time.slice_*` events at all, so the fallback triggers) **plus** an `opsx.archive` event injected at T0+2 hours; assert `estimated_cost.duration_minutes` reflects only the T0→T0+5min activity window (~5 minutes), not the ~2-hour span including the `opsx.archive` timestamp — this is the exact live-reproduced bug (2026-07-16 pilot finding)
  - [ ] Subtask 1.2 (RED): a second test with `session_start`/`session_end` events bracketing the same real activity window with wider timestamps than the activity itself (e.g. `session_start` 10 min before the first prompt, `session_end` 10 min after the last commit) — assert the computed span still uses only the activity timestamps, not the wider session bracket
  - [ ] Subtask 1.3 (GREEN): add `activity_span_of(events: "list[dict]") -> "tuple[Optional[str], Optional[str]]"` near `reduce_events()` — mirrors its own `timestamps = sorted(...)` pattern exactly, but filters `events` first: keep an event if its `type` does NOT start with `"opsx."` and does NOT start with `"time."` and does NOT end with `".session_start"` or `".session_end"` (reuse the existing `t.startswith("ai.") and t.endswith(...)` idiom already used throughout `reduce_events()`/`token_cost_of()` for the session-type checks, don't hand-roll a new matching style). Return `(timestamps[0], timestamps[-1])` or `(None, None)` if the filtered list is empty
  - [ ] Subtask 1.4 (GREEN): in `estimated_cost_of()`'s `else` branch (the raw-span fallback), replace `first_at = engineering_metrics.get("first_event_at")` / `last_at = engineering_metrics.get("last_event_at")` with a call to `activity_span_of(events)` — `estimated_cost_of()` already receives `events` as its third parameter, no new argument needed. The rest of the branch (the `datetime.fromisoformat`/subtraction/`TypeError`-guard block) is unchanged — only the *source* of `first_at`/`last_at` changes

- [ ] Task 2: bookkeeping-only-story degradation (AC: 2)
  - [ ] Subtask 2.1 (RED): a test with only an `opsx.archive` event and a `session_start`/`session_end` pair for a story (no `git.*`, no real `ai.*` activity at all); assert `estimated_cost.usd is None` and `reason == "no events to compute duration from"` — confirms `activity_span_of()` returning `(None, None)` flows into the existing `duration_minutes is None` branch correctly, no new reason string needed

- [ ] Task 3: regression guards (AC: 4, 5)
  - [ ] Subtask 3.1: confirm the existing Story 3.4 tests (`test_estimated_cost_uses_active_time_when_time_slices_present`, `test_estimated_cost_falls_back_to_raw_span_when_no_time_slices`) still pass unmodified — the second one specifically exercises the fallback path with a "clean" event set (only real activity, no bookkeeping noise) and must produce the identical `duration_minutes`/`usd` as before this story, proving the filter is a no-op when there's nothing to filter out
  - [ ] Subtask 3.2 (RED then GREEN): add a test asserting `engineering_metrics.first_event_at`/`last_event_at` in the final snapshot are unaffected by this change — same story/events as Subtask 1.1's test, assert those two fields still reflect the full event span (including the `opsx.archive` timestamp), proving Task 1 only affects `estimated_cost`'s internal calculation, not the separately-reported whole-story span

- [ ] Task 4: full regression, live E2E, and doc parity (AC: 1-5)
  - [ ] Subtask 4.1: `uv run pytest` full suite green; `uv run ruff check .`; `uv run ruff format --check tools tests`
  - [ ] Subtask 4.2: live E2E reproduction against the actual pilot repo that surfaced this finding (`d:\mywork\myPOCs\test-metrics\v0.9.2-docs-only`, story `story-20260716-c260cc` / "Hello World 2") **if still accessible and safe to touch** — re-run `uv run tools/snapshot-assembler/main.py --repo-root .` (a fresh revision, never overwriting the existing `rev1`/`rev2`) against the fixed assembler code and confirm the newly computed `estimated_cost.duration_minutes` drops from the previously-recorded ~117.6 to something close to the real ~15-20 minutes of actual work. If that repo isn't available or touching it isn't appropriate, construct an equivalent scratch repo reproducing the same event shape (real git commits + hook-shaped events + a deliberately late `opsx.archive`-equivalent event) instead — the live-E2E requirement is non-negotiable per this project's established pattern (every prior Epic 2/3/5 story caught real bugs this way that unit tests alone missed), the *specific* repo used is not
  - [ ] Subtask 4.3: update `tools/build-release/INSTALL.md`'s "Known limitations" section — the existing `Duration`/`estimated_cost` paragraph (added by Story 3.4) should gain a sentence noting the raw-span fallback now also excludes bookkeeping events from its span, so a later administrative command never inflates a story's reported duration

## Dev Notes

### Scope — what this story is and is not

- This is a narrow, surgical fix inside one function (`estimated_cost_of()`) plus one small new sibling helper (`activity_span_of()`), both in `tools/snapshot-assembler/main.py` — the same file Story 3.4 already modified for the real-slice path.
- **Do NOT touch** `active_time_seconds_of()` (the real-slice, idle-aware calculation from Story 3.4) — this story only narrows the *fallback* branch's input, never the preferred real-slice path.
- **Do NOT change** `reduce_events()`'s own `first_event_at`/`last_event_at` computation, or `engineering_metrics`'s shape — those fields keep their existing "first/last event of any kind" meaning, used elsewhere (`metrics-report/main.py`'s `duration_minutes_of()` fallback for pre-5.2 snapshots) and reported for its own sake (auditing when kickoff-to-last-activity happened, regardless of cost). This story adds a **second, separate, narrower span** computed only for `estimated_cost_of()`'s own internal use — do not conflate the two or try to unify them into one field.
- **Do NOT build** a general "filter events by category" utility reused across multiple functions — `activity_span_of()` is a small, single-purpose sibling to `reduce_events()`, not a new abstraction layer (project-context.md §7, no premature abstraction).

### Why this matters (severity context)

Found live during pilot testing (2026-07-16), immediately downstream of Story 3.4's own known gap (this epic's 2026-07-11 finding: a completed time slice is often unavailable). In `test-metrics/v0.9.2-docs-only`, story `story-20260716-c260cc` ("Hello World 2") had no completed `time.slice_*` sequence at all (traced to `SessionEnd` firing unreliably in that repo — a separate, already-documented gap), so `estimated_cost_of()` fell back to the raw first/last-event span. That span's *end* turned out to be an `opsx.archive` event emitted by re-running the archiver/assembler roughly two hours after the story's real work had actually finished — inflating a genuinely ~15-20-real-minute story to a reported `duration_minutes: 117.6` / `estimated_cost.usd: $19.60`. This is worse than Story 3.4's already-known "no idle exclusion" gap: that one under-*precises* the number (counts real idle time within a real work session); this one can inflate the number with time that was never spent working on the story *at all*. Confirmed via direct inspection of the pilot repo's own `.story-events.jsonl` — the `opsx.archive` event's timestamp (`15:57:22`) exactly matched the inflated `last_event_at` used in the buggy calculation.

### Architecture compliance (binding invariants)

- **AD-7** — this epic's whole premise ("switching between stories never corrupts time attribution... nobody manually starts or stops a timer") is undermined if a non-work bookkeeping action can silently inflate a story's reported time. This story closes that specific gap without touching AD-7's actual time-slice mechanics (`update_active_story`/`record_activity`/`repoint_active_story`/`close_active_story_slice` in `tools/hooks/_events.py` — **none of those are touched by this story**, it's purely a snapshot-assembler-side reducer fix).
- **AD-10** — "a signal Claude Code cannot report is emitted null-with-reason, never defaulted to zero." AC 2's bookkeeping-only-story case reuses the *existing* `"no events to compute duration from"` null-with-reason path rather than fabricating a zero-minute duration — no new reason string, no new null-handling pattern, just making the existing one reachable from one more (rare) input shape.
- **project-context.md §7 "no premature abstraction"** — `activity_span_of()` is one small function mirroring `reduce_events()`'s existing style (`sorted(...)`, the same `t.startswith("ai.") and t.endswith(...)` idiom already used three times in this file), not a new filtering framework.

### Exact event-type filter (do not narrow this further)

Exclude only: event `type` starting with `"opsx."`, OR ending with `".session_start"` / `".session_end"` (matching the existing `ai_sessions`/`token_cost_of()` type-matching idiom), OR starting with `"time."`. **Everything else counts as real activity** — this specifically includes `ai.<tool>.tool_start`, `ai.<tool>.stop`, `ai.<tool>.defect_compile`, `ai.<tool>.defect_test`, `ai.<tool>.defect_review`, not just `prompt`/`tool_use`. An earlier draft of this story (in `epics.md`'s originally-logged finding) used a narrower *include-list* (`git.*` + `prompt`/`tool_use` only) — that was corrected before implementation began specifically because it would have wrongly excluded real activity like defect-capture events from the span. Do not reintroduce the narrower include-list.

### Source tree touched

```text
tools/snapshot-assembler/main.py              UPDATE  new activity_span_of() helper near reduce_events(); estimated_cost_of()'s fallback branch reads from it instead of engineering_metrics
tests/snapshot_assembler/test_reduce.py       UPDATE  new tests for bookkeeping-event exclusion, bookkeeping-only degradation, and the engineering_metrics-unchanged regression guard
tools/build-release/INSTALL.md                UPDATE  Known Limitations note: raw-span fallback now excludes bookkeeping events
```

`tools/hooks/_events.py` (the AD-7 time-slice producer side) and `active_time_seconds_of()` (the real-slice reducer) are **not** touched — this story is scoped entirely to the fallback branch of one function.

### Project Structure Notes

No conflicts with the unified project structure — this story extends the same file (`tools/snapshot-assembler/main.py`) Stories 2.4/2.6/5.2/5.4/3.4 have each already modified.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.5] — the pilot-testing incident this story fixes, and the corrected (exclude-list, not include-list) filter design
- [Source: tools/snapshot-assembler/main.py#estimated_cost_of] — exact fallback branch to modify (the `else:` block reading `engineering_metrics.get("first_event_at")`/`get("last_event_at")`)
- [Source: tools/snapshot-assembler/main.py#reduce_events] — the sibling function `activity_span_of()` should mirror in style (`sorted(...)` over `timestamps`, the existing `t.startswith("ai.") and t.endswith(...)` idiom)
- [Source: tools/snapshot-assembler/main.py#active_time_seconds_of] — Story 3.4's real-slice path, confirmed untouched by this story
- [Source: tests/snapshot_assembler/test_reduce.py] — existing `run()`/`write_manifest()`/`write_events()`/`read_snapshot()`/`standard_log()`/`event()` helpers, and `test_estimated_cost_falls_back_to_raw_span_when_no_time_slices` / `test_estimated_cost_uses_active_time_when_time_slices_present` as the regression baseline
- [Source: tools/build-release/INSTALL.md#Known limitations] — the existing Story-3.4-authored `Duration`/`estimated_cost` paragraph to extend
- [Source: ARCHITECTURE-SPINE.md#AD-7, AD-10] — the binding invariants this story must not violate
- [Source: project-context.md] — §7 no-premature-abstraction

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
