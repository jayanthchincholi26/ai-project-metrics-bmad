---
baseline_commit: 8cd42db
---

# Story 5.10: `token_cost.reason` Doesn't Distinguish "Never Closed" From "Closed But Failed"

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As someone reading a story's `token_cost`,
I want the surfaced `reason` to reflect what actually happened to the session that did the real work,
so that a null token cost isn't explained by an unrelated, near-empty session's own failure reason.

## Acceptance Criteria

1. **Given** a story where every `ai.<tool>.session_start` has a matching `ai.<tool>.session_end`, and none of the `session_end` events yield real token counts
   **When** the assembler computes `token_cost`
   **Then** `reason` is unchanged from today — `reasons[0]` (the first closed session's own `token_cost_reason`) — no regression to the already-tested Story 5.2/5.6 behavior

2. **Given** a story where zero `session_end` events exist at all
   **When** the assembler computes `token_cost`
   **Then** `reason` is unchanged from today — `"no AI session_end event observed for this story"` — no regression to Story 5.6

3. **Given** a story where at least one `session_end` event exists (so AC2's zero-session_end case doesn't apply), but the count of `ai.<tool>.session_start` events is strictly greater than the count of `session_end` events
   **When** the assembler computes `token_cost`
   **Then** `reason` explicitly states that N of M sessions never sent `session_end`, instead of surfacing an unrelated closed session's own `reasons[0]`

4. **Given** any story
   **When** the assembler computes `token_cost`
   **Then** the returned dict also includes a `sessions_started` count (alongside the existing `sessions_observed`) — the raw count of `ai.<tool>.session_start` events for this story, so the gap between "sessions that began" and "sessions that cleanly ended" is visible directly in the snapshot, not just inferable from the reason text

5. **Given** real token data actually exists (`input_tokens is not None`)
   **When** the assembler computes `token_cost`
   **Then** `reason` stays `None` regardless of any start/end mismatch — real data is never shadowed by a reason about an unrelated session (existing Story 5.2 guarantee, unaffected by this story)

6. **Given** this fix
   **When** `tools/build-release/INSTALL.md`'s "Known limitations" section is reviewed
   **Then** it gains one sentence noting `token_cost.reason` now distinguishes an unclosed session from a closed-but-failed one, and that `sessions_started`/`sessions_observed` together make the gap visible in the snapshot itself

## Tasks / Subtasks

- [x] Task 1: `sessions_started` count (AC: 4)
  - [x] Subtask 1.1 (RED): add a test asserting `token_cost.sessions_started` equals the count of `ai.<tool>.session_start` events for the story, independent of how many `session_end` events exist (e.g. 3 starts, 1 end → `sessions_started == 3`)
  - [x] Subtask 1.2 (GREEN): in `token_cost_of()`, compute `session_starts = [e for e in events if (e.get("type") or "").startswith("ai.") and (e.get("type") or "").endswith(".session_start")]` (mirrors the existing `session_ends` filter one line above it) and add `"sessions_started": len(session_starts)` to the returned dict

- [x] Task 2: smarter reason when some sessions never closed (AC: 1, 2, 3, 5)
  - [x] Subtask 2.1 (RED): reproduce the exact live pilot scenario — 3 `session_start` events (two for the same `session_id`, one for a different one), 2 `session_end` events (both from short/unrelated sessions, each carrying its own `token_cost_reason`), and no `session_end` at all for the session that has all the real activity; assert `token_cost.reason` mentions that sessions never sent `session_end` (e.g. contains "never" or "session_end"), NOT the first closed session's own `token_cost_reason` string verbatim
  - [x] Subtask 2.2 (RED): confirm AC1's case still passes unmodified — same count of `session_start` and `session_end` (e.g. 2 and 2), neither with real tokens; assert `reason == reasons[0]` exactly as today
  - [x] Subtask 2.3 (RED): confirm AC2's case still passes unmodified — zero `session_end` events; assert `reason == "no AI session_end event observed for this story"` exactly as today
  - [x] Subtask 2.4 (GREEN): in `token_cost_of()`, insert a new branch between the existing `elif session_ends:` and its preceding `if input_tokens is not None:` check — when `session_ends` is non-empty AND `len(session_starts) > len(session_ends)`, set `reason` to a new string naming the count of unclosed sessions (e.g. `f"{missing} of {len(session_starts)} AI session(s) for this story never sent session_end (still open, or closed without firing it) — token usage for that session is not reflected here"`); otherwise fall through to the existing `reasons[0]` / `"no AI session_end event observed..."` branches unchanged

- [x] Task 3: full regression, live-data-shaped verification, and doc parity (AC: 1-6)
  - [x] Subtask 3.1: `uv run pytest` full suite green; `uv run ruff check .`; `uv run ruff format --check tools tests`
  - [x] Subtask 3.2: construct a scratch event log shaped exactly like the real pilot repo that surfaced this finding (`D:\mywork\myPOCs\test-metrics\v0.9.3-jira-only`, story `story-20260716-ea94fb`: 3 `session_start`s, 2 `session_end`s, real git/defect activity attributed to the session that never closed) and run the real (non-dry-run) assembler against it — confirm `token_cost.reason` now names the unclosed-session count instead of surfacing the unrelated blip session's `"no assistant usage data found in transcript"` reason
  - [x] Subtask 3.3: update `tools/build-release/INSTALL.md`'s "Known limitations" section — the existing `token_cost.reason: "no AI session_end event observed..."` paragraph gains one sentence on the new `sessions_started`-vs-`sessions_observed` distinction and the smarter reason text for the partially-closed case

## Dev Notes

### Scope — what this story is and is not

- Narrow, surgical fix inside one function (`token_cost_of()`) in `tools/snapshot-assembler/main.py` — the same function Stories 5.2/5.6 already built.
- **Do NOT touch** `active_time_seconds_of()`, `estimated_cost_of()`, or any other reducer — this is scoped entirely to `token_cost_of()`'s reason-selection logic and its returned dict shape (one new key: `sessions_started`).
- **Do NOT attempt to make `sessions_started` and `sessions_observed` always match** — same explicit non-goal Story 5.6 already documented for `ai_sessions` vs. `sessions_observed`: they measure genuinely different things, and a mismatch is expected and informative, not a bug to "fix away."
- **Do NOT try to identify *which* session did the real work** (e.g. by cross-referencing tool_use/prompt counts per `session_id`) — that's a materially bigger feature (per-session activity attribution) this story doesn't attempt. This story only makes the existing reason string honest about *how many* sessions never closed, not which one mattered more.

### Why this matters (severity context)

Found live during JIRA-flow pilot testing (2026-07-16, story `story-20260716-ea94fb` in `D:\mywork\myPOCs\test-metrics\v0.9.3-jira-only`). Direct inspection of `.story-events.jsonl` showed 3 `session_start` events (`session_id`s `58af4d1c...` twice, `311a6897...` once) but only 2 `session_end` events — both from short, near-empty sessions (a ~2-minute reconnect blip that reported `"no assistant usage data found in transcript"`, and a ~1-second blip that reported `"transcript file not found or unreadable"`). The session that did essentially all the real work (96 of 98 session-tagged events, including the story's actual git commit and a `defect_review` event with a real JIRA subtask) never sent `session_end` at all — the already-documented VS Code "x"-button `SessionEnd` gap (see `INSTALL.md`'s existing Known Limitations entry). `token_cost_of()`'s existing `reasons[0]` logic surfaced the *first* blip's reason, which is technically true for that blip but tells the reader nothing about what actually happened to the real work session's tokens — worse, it looks like a definitive explanation when it isn't one.

### Architecture compliance (binding invariants)

- **AD-10** — null-with-reason, never a fabricated default. This story doesn't change *whether* `cost_usd`/`reason` go null, only *which* reason string is chosen when multiple session_ends exist and none produced real tokens — still never fabricating a number, still always giving an honest reason.
- **project-context.md §7 "no premature abstraction"** — the fix is one new `elif` branch plus one new filtered list (`session_starts`), directly mirroring the existing `session_ends` filter already in the function. No new helper module, no generic "session reconciliation" framework.

### Exact reason-selection precedence (do not reorder)

1. `input_tokens is not None` → `reason = None` (real data always wins, unchanged from today)
2. `session_ends` non-empty AND `len(session_starts) > len(session_ends)` → **new**: name the unclosed-session count
3. `session_ends` non-empty (and start/end counts match) → `reasons[0]` (unchanged from today — Story 5.2/5.6 behavior)
4. `session_ends` empty → `"no AI session_end event observed for this story"` (unchanged from today — Story 5.6 behavior)

Branch 2 must sit strictly between branches 1 and 3 in the code, and must NOT fire when `session_ends` is empty (that's branch 4's case, already correctly worded for the "zero ever closed" scenario — don't reword it to also cover "some closed, some didn't").

### Source tree touched

```text
tools/snapshot-assembler/main.py              UPDATE  token_cost_of(): new session_starts count, new sessions_started return key, new reason branch
tests/snapshot_assembler/test_reduce.py       UPDATE  new tests for sessions_started, the partially-closed-sessions reason, and regression guards for the two unchanged existing cases
tools/build-release/INSTALL.md                UPDATE  Known Limitations note: sessions_started/sessions_observed distinction, smarter partially-closed reason text
```

### Project Structure Notes

No conflicts with the unified project structure — extends the same file (`tools/snapshot-assembler/main.py`) Stories 2.4/2.6/5.2/5.4/5.6/3.4/3.5 have each already modified.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.10] — the pilot-testing incident this story fixes
- [Source: tools/snapshot-assembler/main.py#token_cost_of] — exact function and existing `reasons[0]`/`session_ends` logic to extend
- [Source: tests/snapshot_assembler/test_reduce.py] — existing `run()`/`write_manifest()`/`write_events()`/`read_snapshot()`/`event()` helpers, and Story 5.2/5.6's own token_cost tests as the regression baseline
- [Source: tools/build-release/INSTALL.md#Known limitations] — the existing `token_cost.reason: "no AI session_end event observed..."` paragraph to extend
- [Source: ARCHITECTURE-SPINE.md#AD-10] — the binding null-with-reason invariant this story must not violate

## Dev Agent Record

### Agent Model Used

claude-sonnet-5 (create-story context engineering + dev-story implementation)

### Debug Log References

- RED: 5 new tests failing pre-fix, all with `KeyError: 'sessions_started'` — confirmed via `uv run pytest tests/snapshot_assembler/test_reduce.py -k "sessions_started or unclosed_sessions or reason_unchanged or real_tokens_still_shadow" -q`.
- GREEN: `uv run pytest tests/snapshot_assembler/ -q` → 58/58 passed after implementation.
- Full suite: `uv run pytest -q` → 358 passed; `uv run ruff check .` clean; `uv run ruff format --check tools tests` clean.
- Live-data-shaped E2E (real assembler invocation, not just unit tests): built a scratch repo with `.story-events.jsonl` shaped exactly like the real pilot bug (`D:\mywork\myPOCs\test-metrics\v0.9.3-jira-only`, story `story-20260716-ea94fb` — 3 `session_start`s, 2 `session_end`s from short unrelated blips, real activity attributed to the session that never closed). Real (non-dry-run) close produced `token_cost.reason: "1 of 3 AI session(s) for this story never sent session_end (still open, or closed without firing it) - token usage for that session is not reflected here"` — confirming the fix replaces the misleading `"no assistant usage data found in transcript"` (the unrelated blip's own reason) with an honest statement of what actually happened. Scratch repo removed after the run.

### Completion Notes List

- Task 1: new `session_starts` filter in `token_cost_of()` (mirrors the existing `session_ends` filter one line below it); `sessions_started` added to the returned dict alongside the existing `sessions_observed`.
- Task 2: new reason branch inserted between the existing `if input_tokens is not None` and `elif session_ends` checks — fires only when `session_ends` is non-empty AND `len(session_starts) > len(session_ends)`, naming the exact count of unclosed sessions. Confirmed via dedicated regression tests that AC1 (all sessions closed), AC2 (zero sessions closed), and AC5 (real tokens present) are all byte-for-byte unchanged from pre-story behavior — the new branch only fires in the specific partially-closed scenario it targets.
- Task 3: full regression green; live-data-shaped E2E directly reproduces and disproves the original pilot-testing bug (see Debug Log). `INSTALL.md`'s existing `token_cost.reason` Known Limitations paragraph gained a new paragraph explaining `sessions_started`/`sessions_observed` and the smarter partially-closed reason text.
- No new dependencies. `estimated_cost_of()`, `active_time_seconds_of()`, and every other reducer are untouched, as required.

### File List

- tools/snapshot-assembler/main.py (modified — `token_cost_of()`: new `session_starts` filter, new `sessions_started` return key, new reason branch for the partially-closed-sessions case)
- tests/snapshot_assembler/test_reduce.py (modified — 5 new tests: `sessions_started` count, the partially-closed-sessions reason reproducing the real pilot bug, and 3 regression guards for the unchanged existing cases)
- tools/build-release/INSTALL.md (modified — one added paragraph in the existing `token_cost.reason` Known Limitations section)
- _bmad-output/implementation-artifacts/5-10-token-cost-reason-doesnt-distinguish-never-closed-from-failed.md (this file — task checkboxes, Dev Agent Record, status)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — story status transitions)
