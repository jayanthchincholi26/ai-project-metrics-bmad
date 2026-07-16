---
baseline_commit: 8cd42db
---

# Story 5.11: Snapshot and Report Fields Explain Their Own Purpose

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As someone reading a generated snapshot, markdown report, or dashboard,
I want each field to explain what it means and how it's calculated right next to where I'm reading it,
so that I don't have to go find `tools/snapshot-assembler/main.py`'s docstrings or `INSTALL.md` every time I get confused.

## Acceptance Criteria

1. **Given** a single shared, static field-descriptions source (one dotted-path-keyed dict, covering every field currently emitted by the six snapshot sections)
   **When** it's authored
   **Then** each description states both the field's purpose and — where the value is computed rather than copied verbatim from a source system — a one-line summary of the calculation, in plain language a non-author can follow

2. **Given** the snapshot assembler writes a snapshot (real or `--dry-run`)
   **When** the JSON is produced
   **Then** it includes a `field_guide` section (sourced from the shared descriptions in AC1) directly in the snapshot itself — no external doc lookup needed to understand any field in the file you're already looking at

3. **Given** `tools/metrics-report/main.py` generates a `metrics-<date>.md` file
   **When** the report is rendered
   **Then** it includes a "Field Guide" appendix (sourced from the same shared descriptions) explaining every field that appears in each story's block above it

4. **Given** `tools/dashboard/main.py` generates `dashboard.html`
   **When** the table/stat-tiles are rendered
   **Then** each column header and stat tile carries a hover tooltip (sourced from the same shared descriptions) explaining that field — no separate legend page needed, and no new script/CDN dependency introduced

5. **Given** this story only adds documentation-carrying fields/attributes
   **When** existing consumers (tests, other tools) read a snapshot
   **Then** nothing that reads specific data fields today breaks — `field_guide` is strictly additive, same precedent as `estimated_cost`/`defect_metrics` being added without a `schema_version` bump

## Tasks / Subtasks

- [x] Task 1: shared field-descriptions source (AC: 1)
  - [x] Subtask 1.1: create `tools/hooks/_field_guide.py` with a module-level `FIELD_GUIDE: dict[str, str]` — one entry per field currently emitted across `pm_metrics`/`engineering_metrics`/`story_point_cost`/`token_cost`/`estimated_cost`/`defect_metrics`, plus `schema_version`/`story_id`/`revision`. Bridge-import style (same pattern as `tools/hooks/_events.py`, already reused by the snapshot assembler)

- [x] Task 2: snapshot JSON carries the field guide (AC: 2, 5)
  - [x] Subtask 2.1 (RED): add a test asserting a real (non-dry-run) snapshot's top-level `field_guide` key exists, is a dict, and contains an entry for `"token_cost.reason"` with non-empty string content
  - [x] Subtask 2.2 (RED): add a test asserting `--dry-run`'s printed snapshot also carries `field_guide` (same content, since both paths share the same `snapshot` dict construction)
  - [x] Subtask 2.3 (RED): add a regression test asserting every existing envelope key from `ENVELOPE_KEYS` is still present and unaffected — `field_guide` is additive only, no existing key removed or reshaped
  - [x] Subtask 2.4 (GREEN): bridge-import `_field_guide` in `tools/snapshot-assembler/main.py` (same `sys.path.insert(... / "hooks")` already used for `_events`) and add `"field_guide": _field_guide.FIELD_GUIDE` to the `snapshot` dict built in `main()`

- [x] Task 3: markdown report Field Guide appendix (AC: 3)
  - [x] Subtask 3.1 (RED): add a test asserting a generated `metrics-<date>.md` file contains a "## Field Guide" heading and at least one field's description text (e.g. the `token_cost.reason` description)
  - [x] Subtask 3.2 (GREEN): bridge-import `_field_guide` in `tools/metrics-report/main.py`; add a `render_field_guide()` function producing a grouped appendix (one subsection per top-level snapshot section), appended once at the end of `render_report()`'s output

- [x] Task 4: dashboard tooltips (AC: 4)
  - [x] Subtask 4.1 (RED): add a test asserting each `<th>` in the rendered table carries a non-empty `title="..."` attribute, and each stat tile carries one too
  - [x] Subtask 4.2 (GREEN): bridge-import `_field_guide` in `tools/dashboard/main.py`; add `title` attributes to `render_table()`'s header cells and `render_stat_tiles()`'s tile divs, sourced from the shared descriptions (best-fit field per column/tile — e.g. the Duration header ties to `estimated_cost.duration_minutes`)

- [x] Task 5: full regression and doc parity (AC: 1-5)
  - [x] Subtask 5.1: `uv run pytest` full suite green; `uv run ruff check .`; `uv run ruff format --check tools tests`
  - [x] Subtask 5.2: live-shaped run of all three tools (assembler, metrics-report, dashboard) against a real scratch repo — visually confirm the field guide/tooltips render as expected in the actual generated files
  - [x] Subtask 5.3: add a one-sentence pointer in `tools/build-release/INSTALL.md` noting that snapshots/reports/dashboard now explain their own fields, so the "Known limitations" prose is a deeper reference, not the only place to look

## Dev Notes

### Scope — what this story is and is not

- One new shared module (`tools/hooks/_field_guide.py`, a static dict — no functions, no computed content) plus small additive changes to the three existing render/output points: `tools/snapshot-assembler/main.py`, `tools/metrics-report/main.py`, `tools/dashboard/main.py`.
- **Do NOT build a generic "documentation framework"** — this is one dict, reused verbatim by three consumers, exactly mirroring how `tools/hooks/_events.py`'s `git_out()` helper is already bridge-imported by the assembler (project-context.md §7, no premature abstraction).
- **Do NOT bump `SCHEMA_VERSION`** — `field_guide` is a new, purely additive top-level snapshot key, same precedent as `estimated_cost` (Story 5.2) and `defect_metrics` (Story 5.4), neither of which bumped it either.
- **Cross-story note, resolved:** Story 5.10 (PR #49) merged first and added `token_cost.sessions_started` to the snapshot. This branch was rebased onto `main` after that merge, and the flagged one-entry follow-up (a `FIELD_GUIDE["token_cost.sessions_started"]` description, plus a regression test) was added here to close the gap before this story itself merges.

### Why this matters

Reported directly by the user after a full day of reading generated snapshots and reports during pilot testing (2026-07-16): repeated confusion over fields like `phase1_points`/`phase2_points`/`variance`, `sessions_observed` vs. `ai_sessions`, and `duration_minutes`'s active-vs-raw-span distinction. The explanations already exist — in `tools/snapshot-assembler/main.py`'s docstrings and `INSTALL.md`'s prose — but neither sits next to the artifact actually being read day to day.

### Architecture compliance (binding invariants)

- **AD-3 / AD-3a** — the envelope is not "fixed" in the sense of never gaining new top-level keys; Stories 5.2/5.4 already added `estimated_cost`/`defect_metrics` post-hoc. `field_guide` follows the same precedent: additive, no version bump, no change to any existing key's meaning.
- **project-context.md §7 "no premature abstraction"** — `_field_guide.py` is a static dict, not a templating engine or i18n system; the three consumers each render it in their own native format (JSON key, markdown appendix, HTML `title` attribute) rather than sharing a rendering layer.

### Source tree touched

```text
tools/hooks/_field_guide.py                   NEW     shared FIELD_GUIDE dict
tools/snapshot-assembler/main.py              UPDATE  bridge-import _field_guide; add field_guide key to the snapshot dict
tools/metrics-report/main.py                  UPDATE  bridge-import _field_guide; new render_field_guide(), appended to render_report()
tools/dashboard/main.py                       UPDATE  bridge-import _field_guide; title="" tooltips on table headers and stat tiles
tests/snapshot_assembler/test_reduce.py       UPDATE  new tests for field_guide presence (real + dry-run) and additive-only regression guard
tests/metrics_report/ (or equivalent)         UPDATE  new test for the Field Guide appendix
tests/dashboard/ (or equivalent)              UPDATE  new test for header/tile tooltips
tools/build-release/INSTALL.md                UPDATE  one-sentence pointer to the new in-artifact field guide
```

### Project Structure Notes

No conflicts with the unified project structure — extends `tools/snapshot-assembler/main.py`, `tools/metrics-report/main.py`, and `tools/dashboard/main.py`, each already modified by multiple prior stories, plus one new small shared module under `tools/hooks/` (the same directory `_events.py` already lives in).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.11] — the pilot-testing finding this story addresses
- [Source: tools/snapshot-assembler/main.py] — envelope construction in `main()`, the exact insertion point for `field_guide`
- [Source: tools/metrics-report/main.py#render_report] — exact appendix insertion point
- [Source: tools/dashboard/main.py#render_table, #render_stat_tiles] — exact tooltip insertion points
- [Source: tools/hooks/_events.py] — the existing bridge-import precedent `_field_guide.py` follows
- [Source: project-context.md] — §7 no-premature-abstraction

## Dev Agent Record

### Agent Model Used

claude-sonnet-5 (create-story context engineering + dev-story implementation)

### Debug Log References

- RED: 2 new snapshot-assembler tests failed pre-fix (`KeyError: 'field_guide'`), plus the pre-existing exact-envelope-keys test failed once renamed/expanded to 10 keys, confirming it as a real regression check, not a tautology. 2 new metrics-report tests failed (`## Field Guide` absent). 2 new dashboard tests failed (no `title=` attributes present).
- GREEN: `uv run pytest tests/snapshot_assembler/ -q` → 56/56; `uv run pytest tests/metrics_report/ -q` → 19/19; `uv run pytest tests/dashboard/ -q` → 21/21, all after implementation.
- Full suite: `uv run pytest -q` → 360 passed; `uv run ruff check .` clean; `uv run ruff format --check tools tests` flagged one file (`tools/dashboard/main.py`, whitespace only), fixed via `ruff format`, then clean.
- Live E2E (real subprocess calls, not just unit tests, in a scratch repo with a real `git init`): ran the real snapshot assembler, `metrics-report`, and `dashboard` tools in sequence against one real story. Confirmed by direct inspection: the snapshot JSON's `field_guide` key contains all documented entries; the markdown report's tail shows the grouped "## Field Guide" appendix rendering every section's fields with their descriptions; the dashboard's `<th title="...">` and `<div class="tile" title="...">` attributes carry the matching descriptions (stat tiles additionally append "This tile sums the value across every story with a known figure."). Scratch repo removed after the run.

### Completion Notes List

- Task 1: new `tools/hooks/_field_guide.py` — a single static `FIELD_GUIDE` dict (dotted-path keys mirroring the snapshot envelope's own nesting), bridge-imported the same way `_events.py` already is.
- Task 2: `tools/snapshot-assembler/main.py` bridge-imports `_field_guide` and adds `"field_guide": _field_guide.FIELD_GUIDE` as the first key of the `snapshot` dict — shared by both the real-write and `--dry-run` paths since they build the same dict. `ENVELOPE_KEYS`/its exact-match test updated from nine to ten keys; a separate frozen `PRE_FIELD_GUIDE_ENVELOPE_KEYS` constant backs the additive-only regression guard so it doesn't just restate the (now-mutated) `ENVELOPE_KEYS`.
- Task 3: `tools/metrics-report/main.py` bridge-imports `_field_guide`; new `render_field_guide()` groups entries by their dotted-path prefix (falling back to "top level" for bare keys like `schema_version`) in the same order they're defined in `FIELD_GUIDE`, and `render_report()` appends it once per report file (not once per story).
- Task 4: `tools/dashboard/main.py` bridge-imports `_field_guide`; `COLUMN_FIELD_GUIDE_KEYS`/`TILE_FIELD_GUIDE_KEYS` map each table column/stat tile to its best-fit `FIELD_GUIDE` entry, rendered as native `title="..."` tooltips (no JS/CSS framework, no CDN dependency) on `<th>` cells and `.tile` divs. "Total Stories" has no single matching snapshot field, so it gets a bespoke one-line description instead of a `FIELD_GUIDE` lookup.
- Task 5: full regression green; live E2E across all three tools confirms real rendering (see Debug Log). `INSTALL.md` gained one sentence (docs-only flow's step 8) plus a shorter cross-reference (JIRA flow's step 8) pointing at the new in-artifact explanations.
- **Cross-story note:** Story 5.10 (PR #49, opened the same day) adds `token_cost.sessions_started` to the snapshot; this story's `FIELD_GUIDE` doesn't describe it yet since this branch was built independently off `main` before 5.10 merged. Flagged in Dev Notes as a trivial one-entry follow-up for whichever of the two stories merges second.
- No new dependencies (no templating library, no JS framework) — every render stays in the same plain-string style already used by each of the three tools.

### File List

- tools/hooks/_field_guide.py (new — shared `FIELD_GUIDE` static dict)
- tools/snapshot-assembler/main.py (modified — bridge-import `_field_guide`; `field_guide` key added to the snapshot dict)
- tools/metrics-report/main.py (modified — bridge-import `_field_guide`; new `render_field_guide()`, appended to `render_report()`)
- tools/dashboard/main.py (modified — bridge-import `_field_guide`; `title=` tooltips on table headers and stat tiles)
- tests/snapshot_assembler/test_reduce.py (modified — 3 new tests: field_guide present on a real close, on a `--dry-run`, and an additive-only regression guard; `ENVELOPE_KEYS`/its exact-match test updated to 10 keys)
- tests/metrics_report/test_report.py (modified — 2 new tests: Field Guide appendix present, appears once per report not once per story)
- tests/dashboard/test_dashboard.py (modified — 2 new tests: table header tooltips, stat tile tooltips)
- tools/build-release/INSTALL.md (modified — one added sentence in the docs-only flow, a shorter cross-reference in the JIRA flow)
- _bmad-output/implementation-artifacts/5-11-snapshot-and-report-fields-explain-their-own-purpose.md (this file — task checkboxes, Dev Agent Record, status)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — story status transitions)
