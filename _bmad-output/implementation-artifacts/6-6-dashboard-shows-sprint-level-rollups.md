---
baseline_commit: 5ab1158
---

# Story 6.6: Dashboard Shows Sprint-Level Rollups

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As someone reviewing the leadership dashboard,
I want to see each sprint's name, start/end dates, story count, and overall status alongside the per-story table,
so that I don't have to manually group stories by sprint myself to understand sprint-level progress.

## Acceptance Criteria

1. **Given** `tools/dashboard/main.py` renders `dashboard.html`
   **When** at least one discovered snapshot carries a non-null `pm_metrics.sprint` value
   **Then** a new sprint-rollup section/table appears (in addition to the existing per-story table, not replacing it), with one row per distinct sprint present, showing: Sprint Name, Start Date, End Date, Story Count, and an Overall Status of `Ended` / `Active or upcoming` / `Unknown`, computed from that sprint's own end date vs. today (never from a story-done/open count — see Dev Notes correction below)

2. **Given** a story has no sprint value (`pm_metrics.sprint` is null)
   **When** the rollup is built
   **Then** those stories are grouped into an honest "No Sprint" row showing their count, appended after the real sprint rows — never silently dropped (AD-10 philosophy)

3. **Given** Story 6.5 didn't capture a start/end date for a given sprint (older snapshots predating it, or the JIRA instance doesn't expose them)
   **When** that sprint's row renders
   **Then** the missing date(s) show "unknown" rather than blank/fabricated, and Overall Status shows "Unknown" if the end date specifically is missing — same null-with-reason posture as every other optional field in this dashboard

4. **Given** no discovered snapshot carries a non-null sprint at all (an all-docs-only shop, or no data yet)
   **When** the dashboard renders
   **Then** the whole rollup section is omitted, not shown empty — additive only, never a confusing empty table

5. **Given** this story only adds a new section
   **When** the existing per-story table/stat-tiles render
   **Then** they are completely unchanged — additive only, same precedent as Story 5.11's `field_guide`

## Tasks / Subtasks

- [ ] Task 0: `tools/snapshot-assembler/main.py` — real gap found during authoring: wire Story 6.5's `sprint_start_date`/`sprint_end_date` into `pm_metrics` (AC: 1, 3)
  - [ ] Subtask 0.1 (RED): add a test alongside `test_pm_metrics_come_from_the_manifest` asserting `pm_metrics["sprint_start_date"]`/`["sprint_end_date"]` round-trip from `.story.yaml` when present, and a second test asserting both are `None` when the manifest doesn't carry them (older manifests, or docs-only/confluence stories) — confirm RED first (`KeyError`, since `pm_metrics` doesn't have these keys at all today)
  - [ ] Subtask 0.2 (GREEN): add `manifest.get("sprint_start_date")`/`manifest.get("sprint_end_date")` to the `pm_metrics` dict literal, same pattern as every other manifest-sourced field there
  - [ ] Subtask 0.3: update `ENVELOPE_KEYS`-adjacent fixtures/tests if the exact-equality `pm_metrics` dict assertions elsewhere in the test file need the two new always-present keys added (mirror how Story 6.5 fixed `test_success_ack_contains_the_normalized_shape` in `test_jira.py`)

- [ ] Task 1: `tools/hooks/_field_guide.py` — document the two new `pm_metrics` fields (AC: 1, 3)
  - [ ] Subtask 1.1: add `"pm_metrics.sprint_start_date"` / `"pm_metrics.sprint_end_date"` entries, mirroring the existing `"pm_metrics.sprint"` entry's style — state they're null when the story predates Story 6.5, isn't JIRA-backed, or the chosen sprint hadn't started yet

- [ ] Task 2: `tools/dashboard/main.py` — group snapshots by sprint and compute each row (AC: 1, 2, 3, 4)
  - [ ] Subtask 2.1 (RED): write tests for a new `group_by_sprint(snapshots)` helper — returns sprint name → list of snapshots (insertion order or sorted, developer's choice, but document it), plus a separate count of no-sprint stories. Cover: two distinct sprints, a single-story sprint, an empty no-sprint bucket (count 0), a non-empty one
  - [ ] Subtask 2.2 (GREEN): implement `group_by_sprint()`
  - [ ] Subtask 2.3 (RED): write tests for a small ISO-8601 date parser helper (JIRA's real dates carry a trailing `Z` and millisecond fractions, e.g. `"2026-06-26T06:19:49.000Z"` — confirmed real shape from Story 6.5's own live research; Python's `datetime.fromisoformat` does not accept a trailing `Z` before 3.11, and this project's scripts declare `requires-python = ">=3.8"`) — cover a real-shaped string, a malformed string (returns `None`, never raises), and `None` input
  - [ ] Subtask 2.4 (GREEN): implement the parser (e.g. `_parse_iso(value)`, replacing a trailing `Z` with `+00:00` before calling `datetime.fromisoformat`, wrapped in try/except)
  - [ ] Subtask 2.5 (RED): write tests for a `sprint_status(end_date)` helper — a past date → `"Ended"`, a future date → `"Active or upcoming"`, `None`/unparsable → `"Unknown"`. Use dates far enough in the past/future (e.g. year 2000 / year 2099) that the test stays valid regardless of when it's run — no mocking `datetime.now()`
  - [ ] Subtask 2.6 (GREEN): implement `sprint_status()`
  - [ ] Subtask 2.7 (RED): write tests for a `sprint_rollup_row(sprint_name, snapshots)` helper (or equivalent) — Start/End Date taken from the first non-null value found among that sprint's snapshots, "unknown" if none found; Story Count is `len(snapshots)`; Overall Status from `sprint_status()` on the resolved end date
  - [ ] Subtask 2.8 (GREEN): implement it

- [ ] Task 3: `tools/dashboard/main.py` — render the new section (AC: 1, 2, 4, 5)
  - [ ] Subtask 3.1 (RED): write tests asserting: the section is present with a non-null-sprint snapshot and absent with none (AC4); a "No Sprint" row appears only when that count is non-zero; each distinct sprint gets exactly one row regardless of story count; the existing stat-tiles/per-story table output is unchanged (a regression check — same assertions as an existing passing test, run again after this story's change)
  - [ ] Subtask 3.2 (GREEN): add a `render_sprint_rollups(snapshots)` function producing an HTML `<table>` (own heading, e.g. `<h2>Sprint Rollups</h2>`), wired into `render_dashboard()` between the stat tiles and the existing per-story table; returns `""` when there are no non-null-sprint snapshots (AC4), which naturally renders nothing
  - [ ] Subtask 3.3: extend the column-tooltip convention (Story 5.11) to the new table's headers — Sprint Name/Start Date/End Date reuse the `pm_metrics.sprint`/`sprint_start_date`/`sprint_end_date` `FIELD_GUIDE` entries (Task 1); Story Count and Overall Status have no snapshot-field analog, so add two new `FIELD_GUIDE` entries under a `dashboard.sprint_rollup.*` prefix describing the aggregation/computation in plain language, and adjust `_field_guide.py`'s module docstring's one sentence claiming dotted keys "mirror the snapshot envelope's own nesting exactly" to note this one dashboard-only exception

- [ ] Task 4: live/manual verification (AC: 1, 2, 3, 4, 5)
  - [ ] Subtask 4.1: build a scratch repo with several snapshots (reusing the real snapshot-assembler run pattern from prior Epic 6 stories) — at least two distinct sprints (one with a real past end date → "Ended", one with a real future end date → "Active or upcoming"), one sprint with only a single story, one story with `sprint: null`, and one sprint with a name but no captured dates (predating Story 6.5) → "Unknown". Run the real `tools/dashboard/main.py` and open the actual generated `dashboard.html` to confirm every row renders correctly and the existing per-story table/tiles are untouched
  - [ ] Subtask 4.2: confirm a docs-only-only scratch repo (no sprint values at all) produces no rollup section (AC4)
  - [ ] Subtask 4.3: run the full test suite (`uv run pytest -q`) to confirm no regressions

## Dev Notes

### Scope — what this story is and is not

- **Do NOT touch `tools/metrics-report/main.py`** — the epic's own scoping (and this story's title) is dashboard-only; the per-day markdown reports are unaffected. `discover_snapshots()` is reused via the existing bridge-import, not duplicated.
- **Do NOT invent a "committed vs. closed" chart** — that's Story 6.7, explicitly deferred by the user. This story is a table/section, same form as the existing per-story table (per this project's own `dataviz` guidance, already cited when Story 5.5 chose a table over a chart).
- **Do NOT try to compute "how many stories in this sprint are done vs. still open."** This is impossible to do honestly with this pipeline's own data: a snapshot only exists once a story has been *closed* (AD-3) — there is no "still open, has a snapshot" state in this data model at all. Every story-count number in this rollup is inherently "closed stories known locally for this sprint," never "all stories in the sprint." "Overall Status" is about the **sprint's own timeline** (has its end date passed?), not story completion — see the acceptance criteria correction below.

### Real gap found during story authoring (2026-07-17, confirmed by re-reading the file fresh, not assumed)

`tools/snapshot-assembler/main.py`'s `pm_metrics` construction (around its `main()` function) still reads only:
```python
"pm_metrics": {
    "name": manifest.get("name"),
    "points": as_number(manifest.get("points")),
    "goal": manifest.get("goal"),
    "sprint": manifest.get("sprint"),
    "source_of_truth": manifest.get("source_of_truth"),
    "ai_tool": manifest.get("ai_tool"),
    "created": manifest.get("created"),
},
```
Story 6.5 added `sprint_start_date`/`sprint_end_date` to `.story.yaml` (the manifest) but never touched this file — those two fields are silently dropped at close time and never reach a snapshot. This story's Task 0 closes that gap first; without it, there is no real data for Task 2/3 to group or render.

### Acceptance-criteria correction found during story authoring (see epics.md for the full note)

The original epic draft asked for an "overall status" meaning "how many of that sprint's known stories are done vs. still open." That framing cannot be honestly computed from this pipeline's data (every snapshot is already a closed story — see Scope above). The corrected, shippable meaning: **Overall Status describes the sprint itself**, not its stories — `Ended` once the sprint's own end date has passed, `Active or upcoming` otherwise, `Unknown` if no end date was ever captured. This only needs the two dates Story 6.5/Task 0 already provide; no new data source.

Similarly, the original draft's "two or more" rollup threshold was ambiguous (per-sprint minimum? total sprints represented?) and added complexity without a clear benefit — dropped in favor of: the whole section appears whenever at least one non-null sprint exists anywhere in the data; every distinct sprint gets a row, even one with a single story.

### Design notes for Task 2/3

- **Date comparison needs a `Z`-safe parser.** JIRA's real dates (confirmed live during Story 6.5's research) look like `"2026-06-26T06:19:49.000Z"`. `datetime.fromisoformat()` only accepts a trailing `Z` from Python 3.11 onward; this project's tool scripts declare `requires-python = ">=3.8"` (see the `# /// script` header in `tools/dashboard/main.py`), so the parser must strip/replace the `Z` itself (e.g. `value.replace("Z", "+00:00")`) before calling `fromisoformat`, wrapped in a `try/except` that returns `None` on anything unparsable — never a crash on a malformed or hand-edited snapshot (same defensive posture as `metrics_report.date_key_of()`'s own guards).
- **Comparing against "now" is fine and needs no mocking in tests.** Unlike the Workflow-tool scripting sandbox referenced elsewhere in this project's tooling notes, this is plain Python run as a real script — `datetime.now(timezone.utc)` is unrestricted here. Tests should simply use dates safely in the past (e.g. year 2000) or future (e.g. year 2099) rather than mocking the clock, keeping the test suite simple and still valid indefinitely.
- **Which date wins when a sprint's stories disagree?** In practice every story sharing a sprint name should carry the same start/end date, but a snapshot predating Story 6.5 (no dates captured at all) could sit in the same group as one that does. Take the first non-null value found among that sprint's snapshots — same pragmatic "first available wins" posture `metrics_report.date_key_of()` already uses elsewhere in this codebase, not a new pattern.
- **`FIELD_GUIDE` gets two dashboard-only keys.** `tools/hooks/_field_guide.py`'s docstring currently states dotted keys "mirror the snapshot envelope's own nesting exactly" — Story Count and Overall Status have no snapshot-envelope analog (they're computed only at render time), so Task 3 adds them under a `dashboard.sprint_rollup.*` prefix and updates that one docstring sentence to note the exception, rather than either breaking the stated invariant silently or inventing a second, parallel tooltip-description dict for just two entries.

### Architecture compliance (binding invariants)

- **AD-3 / AD-3b** — this story only ever reads the highest-revision snapshot per story via the existing `discover_snapshots()`; no new write path, no new mutation of snapshots.
- **AD-10 (null-with-reason)** — AC 3's "unknown" dates/status and AC 2's honest "No Sprint" count are direct applications; nothing is fabricated or silently dropped.
- **project-context.md §7 (no premature abstraction, but no duplication either)** — reuses `metrics_report.discover_snapshots()` via the existing bridge-import (unchanged); the new `_parse_iso()`/`sprint_status()`/`group_by_sprint()` helpers are the narrow, local pieces of logic this one new section actually needs, not a generic new framework.
- **Story 5.5's own precedent** — no chart, a table; fully self-contained HTML, no CDN/network calls; dark/light theme CSS already in place and untouched.
- **Story 5.11's own precedent** — every rendered column gets a `title=` tooltip sourced from the shared `FIELD_GUIDE` dict, not a one-off inline string.

### Source tree touched

```text
tools/snapshot-assembler/main.py      UPDATE  pm_metrics gains sprint_start_date/sprint_end_date (Task 0, real gap)
tests/snapshot_assembler/test_reduce.py UPDATE  new tests for the two new pm_metrics keys
tools/hooks/_field_guide.py           UPDATE  two new pm_metrics.* entries; two new dashboard.sprint_rollup.* entries; one docstring sentence adjusted
tools/dashboard/main.py               UPDATE  group_by_sprint(), _parse_iso(), sprint_status(), sprint_rollup_row(), render_sprint_rollups(); wired into render_dashboard()
tests/dashboard/test_dashboard.py     UPDATE  new tests for grouping, date parsing, status computation, and the rendered section (present/absent/No-Sprint row), plus a regression check on existing output
```

`tools/metrics-report/main.py` and its tests are **not** touched (out of scope — see Scope above).

### Testing standards (project-context.md §5/§6)

Real RED/GREEN pytest surface across three files this time (Task 0, Task 2, Task 3) — the first Epic 6 story since 6.5 with substantial new Python logic rather than only a `SKILL.md`/`project-context.md` change. Definition of Done for Task 4 is a real scratch-repo run of `tools/dashboard/main.py` with genuinely varied sprint data, plus a full-suite regression run.

### Project Structure Notes

Builds on the `epic-6-jira-lifecycle-sync` integration branch (already checked out), not `main` — this story's own branch (`story/6.6-...`) should be cut from it and merged back into it, not `main`. This is the last of the three stories ("6.4, 6.5, 6.6") the user asked to be built before cutting a new release from the integration branch for their own end-to-end testing.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.6] — the ask, plus the corrections found during authoring (real `pm_metrics` gap, the impossible "done vs. open" framing, the ambiguous threshold)
- [Source: tools/snapshot-assembler/main.py] — the exact `pm_metrics` dict this story's Task 0 extends
- [Source: tools/dashboard/main.py] — existing `aggregate_stats()`/`render_stat_tiles()`/`render_table()`/`render_dashboard()` conventions this story's new functions must match (present-but-null guards via `(s.get("key") or {})`, `COLUMN_FIELD_GUIDE_KEYS`-style tooltip lookups, inline CSS only)
- [Source: tools/metrics-report/main.py#discover_snapshots] — reused unchanged; also `date_key_of()`'s "first available wins, never raise" posture, mirrored by this story's date parser
- [Source: tools/hooks/_field_guide.py] — the shared tooltip-description dict this story extends
- [Source: tests/dashboard/test_dashboard.py] — existing test conventions (`write_snapshot()` fixture with `**overrides`, `dashboard_html()` helper) to extend, not reinvent
- [Source: _bmad-output/implementation-artifacts/6-5-kickoff-captures-sprint-metadata-name-start-end-date.md] — this story's direct data dependency; the real confirmed sprint-date shape from its live research
- [Source: project-context.md] — AD-3, AD-3b, AD-10, §7

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

## Change Log

- 2026-07-17: Story drafted from epics.md's Epic 6 section, with a real `pm_metrics` gap and two acceptance-criteria corrections found and fixed during authoring (see Dev Notes). Status: backlog → ready-for-dev.
