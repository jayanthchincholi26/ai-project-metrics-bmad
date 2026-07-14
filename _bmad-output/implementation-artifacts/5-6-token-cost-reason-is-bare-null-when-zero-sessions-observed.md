---
baseline_commit: 276f86a
---

# Story 5.6: `token_cost.reason` Is Bare `null` When Zero Sessions Observed

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer reading a story's snapshot, report, or dashboard,
I want `token_cost.reason` to always explain why `token_cost` is null when it is null,
so that a zero-AI-sessions-observed story doesn't look like an unexplained data gap (violating AD-10's "null-with-reason, never a bare null" guarantee).

## Background

Logged as a post-implementation finding in `epics.md` on 2026-07-11 (commit `8f480a3`), not yet turned into a story. Confirmed with a real, live repro during pilot testing on 2026-07-14: a real snapshot (`story-20260714-abfa46`) showed `engineering_metrics.ai_sessions: 1` (one `SessionStart` fired) but `token_cost.sessions_observed: 0` (zero `SessionEnd` events captured, because the developer closed VS Code abruptly instead of running `/exit` or `Ctrl+C` first — see `tools/setup-hooks.py`'s wiring and the Claude Code hooks reference: `SessionEnd` is not guaranteed to fire on an abrupt window close). Both the generated `dashboard.html` and `metrics-<date>.md` rendered "not tracked — no reason given" for AI Token Cost, confirming the gap surfaces all the way to the leadership-facing outputs, not just the raw JSON.

**Important — this story does NOT fix the `ai_sessions` vs `sessions_observed` count mismatch itself.** These two fields intentionally measure different things (`ai_sessions` = sessions *started*; `sessions_observed` = sessions that *ended cleanly with token data*) and will legitimately differ whenever a session doesn't end gracefully. That's real, useful information — not a bug. The only bug is that the null `reason` in the zero-observed case doesn't explain itself.

## Acceptance Criteria

1. **Given** a story where zero `ai.<tool>.session_end` events exist in the event log (`sessions_observed` would be `0`)
   **When** the snapshot assembler computes `token_cost`
   **Then** `token_cost.reason` is a real explanatory string (e.g. `"no AI session_end event observed for this story"`), never a bare `null` — matching AD-10's rule that every null in a snapshot carries a reason

2. **Given** at least one `session_end` event exists but token counts still came back null (e.g. a transcript read failure)
   **When** `token_cost` is computed
   **Then** behavior is **unchanged** from today — `reason` still surfaces the first session's own `token_cost_reason` (e.g. `"no transcript_path in hook payload"`), exactly as `tools/snapshot-assembler/main.py`'s existing tests already cover (`test_token_cost_null_with_reason_propagates`)

3. **Given** real token counts were successfully captured
   **When** `token_cost` is computed
   **Then** `reason` stays `null` — this story only changes the *zero-sessions* null case, nothing else

4. **Given** this is a one-line logic change in an existing, well-tested function
   **When** Definition of Done is evaluated
   **Then** a new test (`sessions_observed == 0` → real reason string) is added alongside the existing `token_cost_of` tests in `tests/snapshot_assembler/test_reduce.py`, and all existing tests in that file continue to pass unmodified

## Tasks / Subtasks

- [ ] Task 1: fix `token_cost_of()` (AC 1, 2, 3)
  - [ ] Subtask 1.1 (RED): add `test_token_cost_reason_explains_zero_sessions_observed` to `tests/snapshot_assembler/test_reduce.py` — a story with a `session_start` but no `session_end` event at all; assert `token_cost["sessions_observed"] == 0` and `token_cost["reason"]` is a non-null, non-empty string
  - [ ] Subtask 1.2 (GREEN): in `tools/snapshot-assembler/main.py`'s `token_cost_of()`, change the `reason` computation so the zero-`session_ends` case gets its own explanatory string, distinct from the existing "use the first session's own `token_cost_reason`" path — don't collapse the two cases into one, they mean different things
  - [ ] Subtask 1.3: run the full existing `token_cost_of`-related test suite (`test_token_cost_null_with_reason_propagates`, `test_token_cost_sums_real_tokens_across_sessions`, `test_cost_usd_computed_when_tokens_and_rates_are_both_known`) and confirm all still pass unmodified

- [ ] Task 2: full regression and live E2E (AC 1-4)
  - [ ] Subtask 2.1: `uv run pytest` full suite green; `uv run ruff check .`; `uv run ruff format --check tools tests`
  - [ ] Subtask 2.2: live E2E — reuse the real scratch repo/snapshot from the 2026-07-14 pilot test that surfaced this bug (or reproduce fresh): kick off a story, do some work, end the session *without* `/exit` (so `session_end` never fires), archive, confirm the new snapshot's `token_cost.reason` is now a real string instead of `null`; re-run `metrics-report`/`dashboard` and confirm the rendered "not tracked" line now shows the real reason instead of "no reason given"

- [ ] Task 3: close the loop on the original finding (AC: none — bookkeeping)
  - [ ] Subtask 3.1: remove or update the 2026-07-11 finding note in `epics.md` (near Story 2.4/2.5) to point at this story rather than leaving it as a dangling "worth a quick look" note

## Dev Notes

### Scope — what this story is and is not

- A narrow, one-function fix to `tools/snapshot-assembler/main.py`'s `token_cost_of()` — no change to `session_end.py`, no change to how `sessions_observed`/`ai_sessions` are counted, no change to any other snapshot field.
- **Do NOT try to make `ai_sessions` and `sessions_observed` match.** They measure genuinely different things (see Background) — forcing them to agree would be incorrect, not a fix.
- **Do NOT change the existing "session exists but its own token_cost_reason explains a null" path** (AC 2) — only the *zero-session_end* case is currently under-specified.

### The exact code to change

`tools/snapshot-assembler/main.py`, `token_cost_of()`, current line:
```python
"reason": (reasons[0] if reasons else None) if input_tokens is None else None,
```
This only ever surfaces a reason when `reasons` (collected from existing `session_end` events' own `token_cost_reason` payload) is non-empty — which is impossible to populate when `session_ends` itself is empty. Distinguish the two null cases explicitly:
```python
if input_tokens is not None:
    reason = None
elif session_ends:
    reason = reasons[0] if reasons else None
else:
    reason = "no AI session_end event observed for this story"
```
(`session_end.py`'s own contract guarantees every `session_end` event with null tokens carries a `token_cost_reason` — see its docstring — so the `session_ends and not reasons` sub-case shouldn't occur in practice, but the `reasons[0] if reasons else None` fallback keeps that branch safe regardless.)

### Architecture compliance (binding invariants)

- **AD-10** ("null-with-reason, never bare zero/null") is the invariant this story closes a gap in — the fix makes the zero-sessions case comply with a rule the rest of the snapshot already follows.
- No other AD is touched.

### Testing standards (project-context.md §5/§6)

- Standard `pytest` RED→GREEN — this function already has good test coverage (`tests/snapshot_assembler/test_reduce.py`); follow the exact same `event()`/`write_events()`/`run()` test helpers already used there, don't reinvent a new pattern.

### Source tree touched

```text
tools/snapshot-assembler/main.py         UPDATE  token_cost_of()'s reason computation
tests/snapshot_assembler/test_reduce.py  UPDATE  new test for the zero-sessions-observed case
_bmad-output/planning-artifacts/epics.md UPDATE  close out the 2026-07-11 finding note
```

### References

- [Source: tools/snapshot-assembler/main.py#token_cost_of] — the function this story fixes; also read `reduce_events()`'s `ai_sessions` count (line ~175) to confirm the two counts' genuinely different definitions before touching anything
- [Source: tools/hooks/claude/session_end.py] — confirms every `session_end` event with null tokens already carries a `token_cost_reason`, which is why the zero-`session_ends` case needed its own explicit branch
- [Source: tests/snapshot_assembler/test_reduce.py] — existing `token_cost_of` test coverage this story extends, not replaces
- [Source: _bmad-output/planning-artifacts/epics.md] — the original 2026-07-11 finding note this story closes out (Task 3)
- [Source: project-context.md §AD-10 reference in ARCHITECTURE-SPINE.md] — the "null-with-reason, never bare zero" rule this story brings this one field into compliance with

## Dev Agent Record

### Agent Model Used

_to be filled by dev-story_

### Debug Log References

_to be filled by dev-story_

### Completion Notes List

_to be filled by dev-story_

### File List

_to be filled by dev-story_
