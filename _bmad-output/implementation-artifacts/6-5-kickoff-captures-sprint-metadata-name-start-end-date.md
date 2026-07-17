---
baseline_commit: 0dd5a7c
---

# Story 6.5: Kickoff Captures Sprint Metadata (Name, Start/End Date)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As someone who will later want sprint-level rollups,
I want a JIRA-backed story's sprint name and its start/end dates captured at kickoff time,
so that a later dashboard feature has real dates to show, not just a bare sprint name string.

## Acceptance Criteria

1. **Given** `source_of_truth: jira` and a successful kickoff fetch (either the MCP path, `story-kickoff/SKILL.md` step 4a, or the Story 1.3 script fallback, `tools/adapters/jira/main.py`)
   **When** the sprint field's raw value is inspected (not just today's extracted name string)
   **Then** if the *same chosen sprint item* `extract_sprint()` already selects (active wins, else the last entry) carries `startDate`/`endDate`, persist them into `.story.yaml` as `sprint_start_date`/`sprint_end_date` alongside the existing `sprint` name — additive only, `sprint`'s own existing meaning/format is unchanged

2. **Given** the chosen sprint item has no dates (a `"future"` sprint that hasn't started yet, a plain string/legacy Greenhopper format, or a JIRA instance/plan that doesn't expose this)
   **When** kickoff runs
   **Then** `sprint_start_date`/`sprint_end_date` are simply absent/null — never fabricated, and kickoff is not blocked either way (FR5)

3. **Given** `source_of_truth: confluence` or `docs-only`
   **When** kickoff runs
   **Then** nothing changes — no sprint dates exist to capture for either backend

## Tasks / Subtasks

- [x] Task 1: `tools/adapters/jira/main.py` — extract dates from the same chosen sprint item (AC: 1, 2)
  - [x] Subtask 1.1 (RED): add tests mirroring the existing sprint-selection tests exactly (`test_sprint_active_object_wins_over_closed`, `test_sprint_falls_back_to_last_when_none_active`) but asserting `sprint_start_date`/`sprint_end_date` in the ack — using the real confirmed shape (`startDate`/`endDate` ISO strings) from this story's live research
  - [x] Subtask 1.2 (RED): add a test for a `"future"`-state sprint item with no `startDate`/`endDate` keys at all — assert both come back `None`, not a `KeyError`
  - [x] Subtask 1.3 (RED): add a test for the legacy Greenhopper string format and the plain-string sprint value — assert both dates are `None` (no structured data to extract from either shape)
  - [x] Subtask 1.4 (GREEN): refactor `extract_sprint()`'s existing "active wins, else last" list-selection logic into a small shared helper (e.g. `_select_sprint_item(value)`) — used by both `extract_sprint()` (unchanged behavior, verified by the full existing test suite still passing) and a new `extract_sprint_dates(value)` that reads `startDate`/`endDate` off the same chosen item. Do not duplicate the selection logic in two places — that's exactly the kind of drift this story's own research (multiple sprint entries per issue) warns against
  - [x] Subtask 1.5 (GREEN): wire `extract_sprint_dates()`'s result into `normalize()`'s returned ack dict as `sprint_start_date`/`sprint_end_date`

- [x] Task 2: `tools/adapters/docs-only/main.py` — the manifest writer (AC: 1, 2, 3)
  - [x] Subtask 2.1 (RED): add tests mirroring the existing `jira_issue_key` field tests (defaults to null when omitted; recorded when provided) for two new fields
  - [x] Subtask 2.2 (GREEN): add `--sprint-start-date`/`--sprint-end-date` optional arguments, written into the manifest as `sprint_start_date`/`sprint_end_date` (null when omitted) — placed immediately after the existing `sprint` field in the manifest's fixed key order; update `MANIFEST_KEYS` in the test file to match the new order

- [x] Task 3: `story-kickoff/SKILL.md` — the MCP path (AC: 1, 2, 3)
  - [x] Subtask 3.1: extend step 4a.3's existing sprint-extraction paragraph to also extract `sprint_start_date`/`sprint_end_date` from the *same* chosen sprint object (active wins, else last — the rule is already stated there for the name; don't restate it as a second, potentially-diverging rule) — no new MCP call, the same `getJiraIssue` fetch already requests the sprint field
  - [x] Subtask 3.2: extend step 5's manifest-writer invocation line to pass `--sprint-start-date`/`--sprint-end-date` when present

- [x] Task 4: live verification (AC: 1, 2, 3)
  - [x] Subtask 4.1: real kickoff-equivalent run — fetched `AI-126` live (`getJiraIssue`), ran the manifest writer with the correctly-selected values, confirmed `.story.yaml` matches. Additionally fed the real fetched payload directly through `tools/adapters/jira/main.py`'s own `normalize()`, and a second real-shaped payload using the actual `AI Sprint 19` dates from the same fetch as the chosen (active) entry — confirmed real dates flow through correctly, not just via hand-written test fixtures
  - [x] Subtask 4.2: confirmed live — `AI-126`'s real sprint field has no active sprint (one closed, one future); the reused "last wins" rule correctly selects the future sprint, which genuinely carries no date keys at all — both fields null in the resulting manifest, not fabricated

## Dev Notes

### Scope — what this story is and is not

- **Do NOT touch `tools/adapters/confluence/main.py`** — Confluence's sprint value always comes from a page label (a plain string), never structured date data; AC 3 confirms this story doesn't touch it at all.
- **Do NOT invent a new selection rule for dates** — reuse `extract_sprint()`'s existing "active wins, else last" logic exactly, via the shared helper (Task 1, Subtask 1.4). This story's own research finding (an issue can carry multiple sprint entries) is exactly why a second, independently-written selection rule would risk disagreeing with the name's own choice.
- **Do NOT add a dedicated "get sprint details" MCP call** — none exists in this project's available Atlassian tool surface; the data comes from the *same* `getJiraIssue`/REST fetch that already retrieves the sprint field for the name.
- **`sprint`'s own existing field/format is completely unchanged** — this story only adds two new, purely additive manifest fields alongside it.

### Real research finding, confirmed live before implementation (not assumed)

`searchJiraIssuesUsingJql` against a real project confirmed the sprint field's actual shape: a list of sprint objects, each potentially carrying `id`/`name`/`state`/`boardId`/`goal`/`startDate`/`endDate`/`completeDate`. Two things this proves, concretely:
1. **Dates only exist once a sprint has started.** A `"future"`-state sprint (not yet begun) has no `startDate`/`endDate` keys at all — confirmed on a real issue (`AI-145`, sprint `"AI Sprint 20"`, state `"future"`, no date keys present).
2. **An issue can carry more than one sprint entry** — its full sprint history, not just "the current one." Confirmed on real issues (`AI-126`, `AI-122`, `AI-121`) each carrying both a closed sprint (`"AI Sprint 19"`, with real dates: `startDate: "2026-06-08T06:03:51.792Z"`, `endDate: "2026-06-26T06:19:49.000Z"`) *and* a future one (`"AI Sprint 20"`, no dates). This is exactly why the existing active-wins-else-last selection rule matters for dates too, not just the name.

### Architecture compliance (binding invariants)

- **AD-5** — `.story.yaml` remains the sole source of story identity; this story only adds two new, optional, purely descriptive fields to it, nothing that changes identity semantics.
- **AD-10 (null-with-reason)** — AC 2 is a direct application: a `"future"` sprint's missing dates are never fabricated, just left null, same philosophy as everywhere else in this pipeline.
- **FR5 (never block kickoff)** — missing/absent sprint dates never gate, delay, or fail kickoff in any way.
- **project-context.md §7 (no premature abstraction, but no duplication either)** — the shared `_select_sprint_item()` helper (Task 1) is the narrow, correct middle ground: not a generic "field extraction framework," just the one small piece of logic (`extract_sprint()`'s own selection rule) that two functions now both need, extracted once rather than copy-pasted and risking drift.

### Source tree touched

```text
tools/adapters/jira/main.py                    UPDATE  new _select_sprint_item() helper (extract_sprint() refactored to use it); new extract_sprint_dates(); normalize() returns sprint_start_date/sprint_end_date
tests/adapters/test_jira.py                     UPDATE  new tests for date extraction, future-sprint/no-dates case, legacy-string/no-dates case
tools/adapters/docs-only/main.py                UPDATE  new --sprint-start-date/--sprint-end-date args, written into the manifest
tests/adapters/test_docs_only.py                UPDATE  new tests for the two fields; MANIFEST_KEYS updated to the new fixed order
.claude/skills/story-kickoff/SKILL.md           UPDATE  step 4a.3's sprint-extraction paragraph extended; step 5's writer invocation line extended
```

`tools/adapters/confluence/main.py` and its tests are **not** touched (AC 3).

### Testing standards (project-context.md §5/§6)

Real RED/GREEN pytest surface this time (Tasks 1-2), unlike Stories 6.1/6.2's core skill-instruction work — this story touches two actual Python adapters. Task 3 (the `SKILL.md` extension) has no pytest surface, same as every other Epic 6 skill-instruction change. Definition of Done for Task 3/4 is live verification against the real confirmed sprint-field shape from this story's own research.

### Project Structure Notes

Extends `tools/adapters/jira/main.py` and `tools/adapters/docs-only/main.py` — both already modified by multiple prior stories (1.3, 1.6, 1.7, 5.4) — plus `story-kickoff/SKILL.md` (modified by nearly every Epic 1/6 story by now). Builds on the `epic-6-jira-lifecycle-sync` integration branch, not `main` — this story's own branch (`story/6.5-...`) should be cut from it and merged back into it, not `main`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.5] — the ask, including the live-verified real sprint-field shape found during story authoring
- [Source: tools/adapters/jira/main.py#extract_sprint] — the exact existing selection logic (active wins, else last) this story's new `extract_sprint_dates()` must reuse, not reinvent
- [Source: tools/adapters/docs-only/main.py] — the manifest writer's existing field-ordering convention (`MANIFEST_KEYS` in its test file enumerates the fixed order)
- [Source: tests/adapters/test_jira.py] — existing sprint-selection test patterns (`test_sprint_active_object_wins_over_closed`, `test_sprint_falls_back_to_last_when_none_active`, the legacy-Greenhopper-string test) to mirror for the new date tests
- [Source: .claude/skills/story-kickoff/SKILL.md#4a.3] — the exact paragraph this story extends (already documents the active-wins-else-last rule for the name)
- [Source: project-context.md] — AD-5, AD-10, FR5, §7

## Dev Agent Record

### Agent Model Used

claude-sonnet-5 (create-story context engineering + dev-story implementation)

### Debug Log References

- Task 1: RED confirmed (6 new tests failing with `KeyError`), GREEN after refactoring `extract_sprint()` to use a shared `_select_sprint_item()` helper and adding `extract_sprint_dates()`. Also fixed the pre-existing exact-equality test (`test_success_ack_contains_the_normalized_shape`) to include the two new always-present keys. `uv run pytest tests/adapters/test_jira.py -q` → 24/24 passed.
- Task 2: RED confirmed (2 new tests failing, plus 2 pre-existing `MANIFEST_KEYS`-order tests correctly failing once the constant was updated first), GREEN after adding `--sprint-start-date`/`--sprint-end-date` to the writer. `uv run pytest tests/adapters/test_docs_only.py -q` → 43/43 passed.
- Full regression after Tasks 1-2: `uv run pytest -q` → 375 passed (up from 367, +8 new tests).
- Task 4 (live verification, no JIRA mutation needed — pure read + local write):
  1. `getJiraIssue` on `AI-126` (real data from this story's own research) confirmed its real sprint field: `AI Sprint 19` (closed, real dates) and `AI Sprint 20` (future, no dates) — no active sprint, so the reused selection rule correctly picks the **last** entry (`AI Sprint 20`).
  2. Ran the real manifest writer with these values — confirmed `.story.yaml` shows `sprint: "AI Sprint 20"`, `sprint_start_date: null`, `sprint_end_date: null` — exactly matching the real fetch's implication (a future sprint has no dates).
  3. Additionally fed the *actual* fetched JSON payload directly through `tools/adapters/jira/main.py`'s own `normalize()` (not just hand-written test fixtures) — confirmed the same correct result.
  4. Constructed a second real-shaped payload using the actual `AI Sprint 19` dates from the same fetch, as the chosen (active) entry — confirmed real ISO date strings flow through unmodified to the ack.
  5. Scratch repo removed after the run.

### Completion Notes List

- Task 1: `extract_sprint()` refactored (behavior-preserving, verified by its own full existing test suite still passing) to share a new `_select_sprint_item()` helper with the new `extract_sprint_dates()` — avoiding exactly the kind of two-independent-selection-rules drift this story's own research (an issue can carry multiple sprint entries) warned against.
- Task 2: two new optional manifest fields, defaulting to `null`, following the exact same `clean()`/`or None` pattern as every other optional string field in this writer.
- Task 3: `story-kickoff/SKILL.md`'s step 4a.3 extended to extract dates from the *same* chosen sprint object already used for the name (no new MCP call, no second selection rule stated); step 5's invocation line and its explanatory paragraph both extended.
- Task 4: live-verified against real JIRA data end to end, including both the null-dates case (a real future sprint) and the real-dates case (real ISO strings from an actual closed sprint) — the latter constructed from genuine field values captured during this story's own research, not synthetic data.
- No changes to `tools/adapters/confluence/main.py` — confirmed untouched, per AC 3's scope boundary.

### File List

- tools/adapters/jira/main.py (modified — new `_select_sprint_item()` helper; `extract_sprint()` refactored to use it; new `extract_sprint_dates()`; `normalize()` returns `sprint_start_date`/`sprint_end_date`)
- tests/adapters/test_jira.py (modified — 6 new tests; 1 existing exact-equality test updated for the new always-present keys)
- tools/adapters/docs-only/main.py (modified — new `--sprint-start-date`/`--sprint-end-date` args, written into the manifest)
- tests/adapters/test_docs_only.py (modified — 2 new tests; `MANIFEST_KEYS` updated to the new fixed order)
- .claude/skills/story-kickoff/SKILL.md (modified — step 4a.3's sprint-extraction paragraph extended; step 5's writer invocation line and explanation extended)
- _bmad-output/implementation-artifacts/6-5-kickoff-captures-sprint-metadata-name-start-end-date.md (this file — task checkboxes, Dev Agent Record, status)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — story status transitions)

## Change Log

- 2026-07-17: Story implemented and live-verified end to end (real sprint field shape from `AI-126`, both the null-dates and real-dates cases confirmed against genuine JIRA data). Status: ready-for-dev → review.
