---
baseline_commit: 2c380e7
---

# Story 5.3: `metrics-<date>.md` Generator

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer or lead reviewing project metrics,
I want a plain, human-readable markdown report generated from the JSON snapshots, grouped by day,
so that I (or leadership) can read "what happened and what it cost" without opening raw JSON, the same way this project's own hand-maintained `docs/metrics.md` does today — but generated automatically from real snapshot data instead of hand-written.

## Acceptance Criteria

1. **Given** one or more snapshot files exist under `snapshots/*.json`
   **When** a new tool, `tools/metrics-report/main.py --repo-root .`, is run
   **Then** it reads **every** snapshot file, groups stories by the calendar date portion of `engineering_metrics.last_event_at` (the day the story's most recent captured activity happened — i.e., effectively the day it closed), and writes/overwrites one file per represented date at `metrics-reports/metrics-<MMDDYYYY>.md` (e.g. `metrics-07142026.md`) — **not** a `docs/` path, since a target project adopting this tool may not have a `docs/` folder at all; `metrics-reports/` is a new top-level output directory, parallel to `snapshots/`

2. **Given** a story has multiple snapshot revisions (`story_id.v1.rev1.json`, `.rev2.json`, ...)
   **When** the report is generated
   **Then** only the **highest revision** is rendered for that story (AD-3b: latest revision is current, priors are audit history) — never render multiple revisions of the same story as separate entries

3. **Given** the report's per-story format
   **When** a story's snapshot is rendered
   **Then** it follows the same structure as this repo's own hand-maintained `docs/metrics.md` (title, Date, Duration, Story Points, Estimated Cost, AI Token Cost, Notes) — populated from real snapshot fields:
   - Title: the manifest's `name` if present, else the bare `story_id`
   - Date: the date portion of `pm_metrics.created`
   - Duration: computed from `estimated_cost.duration_minutes` (already computed by Story 5.2), rendered as a human string (e.g. "~37 minutes" or "~2 hours 15 minutes")
   - Story Points: `pm_metrics.points`, with `story_point_cost.phase1_points`/`phase2_points`/`variance` shown when not null
   - Estimated Cost: `estimated_cost.usd` formatted as USD, or **"not tracked — {reason}"** honestly when null (never omit the line or show a fake `$0.00`)
   - AI Token Cost: `token_cost.cost_usd` formatted as USD plus the raw `input_tokens`/`output_tokens`, or **"not tracked — {reason}"** when null
   - Notes: a short summary line built from `engineering_metrics` (commits, AI sessions, tool uses, prompts) and `story_point_cost.reduced_confidence_reasons` when `reduced_confidence` is true

4. **Given** defect/testing/review-efficiency fields exist in `docs/metrics.md`'s format but nothing in this pipeline captures them yet (Story 5.4, not started)
   **When** the report is generated
   **Then** those fields are shown as **"not yet tracked"**, never omitted silently and never a fabricated `0` — same null-with-reason philosophy as every other honest gap in this pipeline. This section must be trivially extendable once Story 5.4 lands (a single field lookup, not a structural rewrite)

5. **Given** the generator is run more than once (e.g. after new stories close on a day already reported, or simply re-run without new data)
   **When** it runs
   **Then** each date's file is **fully regenerated from scratch** each time (not appended to) — safe because the JSON snapshots are the sole source of truth and are immutable; the markdown file is purely a derived, disposable rendering. Running it twice with no new snapshots produces byte-identical output

## Tasks / Subtasks

- [x] Task 0 (prerequisite, found during story creation): `pm_metrics.name` is missing from the snapshot envelope
  - [x] Subtask 0.1: `tools/snapshot-assembler/main.py`'s `pm_metrics` dict never includes `manifest.get("name")` — the human-readable story name `.story.yaml` has carried since Story 1.7 (docs-only kickoff) is silently dropped at snapshot time, even though `points`/`goal`/`sprint`/`source_of_truth`/`ai_tool`/`created` are all preserved. Add `"name": manifest.get("name")` to the `pm_metrics` dict — this is a field addition **within** the already-fixed `pm_metrics` sub-object (not a new top-level envelope key), so it does **not** require an AD-3a update, unlike Story 5.2's `estimated_cost` addition
  - [x] Subtask 0.2 (RED then GREEN): add a test in `tests/snapshot_assembler/test_reduce.py` confirming `pm_metrics.name` round-trips from the manifest into the snapshot (and is `null` when the manifest has no `name`, e.g. JIRA/Confluence stories, which never set it)
  - [x] Subtask 0.3: this is a genuine, real fix, not scope creep — Story 5.3's AC 3 (title = manifest name if present) cannot be satisfied without it, and it's a one-line addition in the same section of the same file Story 5.2 just touched

- [x] Task 1: snapshot discovery, revision selection, date grouping (AC: 1, 2)
  - [x] Subtask 1.1 (RED): add a test with 3 snapshot files for 2 different `story_id`s (one story with `rev1`+`rev2`, another with only `rev1`), each with a distinct `last_event_at` date, plus a manifest name in one case and none in the other — assert the discovery step selects exactly the two *highest*-revision snapshots and groups them by their `last_event_at` date correctly
  - [x] Subtask 1.2 (GREEN): implement discovery — glob `snapshots/*.json`, parse each, group by `(story_id)`, keep only the max `revision` per `story_id` (reuse the existing `{story_id}.v{schema}.rev{N}.json` naming convention already established in `tools/snapshot-assembler/main.py`'s `next_revision()` — don't invent a second revision-parsing scheme), then bucket the surviving one-per-story snapshots by the date portion of `engineering_metrics.last_event_at`
  - [x] Subtask 1.3 (GREEN): write/overwrite `metrics-reports/metrics-<MMDDYYYY>.md` per date bucket found, creating the `metrics-reports/` directory if absent

- [x] Task 2: per-story markdown rendering (AC: 3, 4)
  - [x] Subtask 2.1 (RED): add tests for the per-story block covering: all fields present and real; `estimated_cost.usd`/`token_cost.cost_usd` both null with distinct reasons (must show "not tracked — {reason}", not blank/omitted); a story with no `name` (falls back to `story_id` as the title); `reduced_confidence: true` surfacing its reason in Notes
  - [x] Subtask 2.2 (GREEN): implement the per-story renderer, matching `docs/metrics.md`'s structural conventions (bullet list under a `## <title>` header, one section per story, separated by `---`) — the defect/efficiency fields render as a fixed "not yet tracked" placeholder block (AC 4), written so that Story 5.4 can later replace that placeholder with real per-field lookups without restructuring the renderer

- [x] Task 3: idempotent regeneration (AC: 5)
  - [x] Subtask 3.1 (RED): add a test that runs the generator twice with the same snapshot set and asserts the output file is byte-identical both times
  - [x] Subtask 3.2 (GREEN): confirm the implementation naturally satisfies this (full regeneration from scratch, not append) — if it doesn't already, fix rather than special-case

- [x] Task 4: full regression, live E2E, and doc parity (AC: 1-5)
  - [x] Subtask 4.1: `uv run pytest` full suite green; `uv run ruff check .`; `uv run ruff format --check tools tests`
  - [x] Subtask 4.2: live E2E — run the generator against this project's own real accumulated `snapshots/*.json` files (there are several from today's and yesterday's pilot testing referenced in memory/story files) in a scratch copy, inspect the resulting `metrics-reports/metrics-*.md` files for sane, correctly-grouped, correctly-formatted output — not just unit-tested in isolation
  - [x] Subtask 4.3: add a step to `tools/build-release/INSTALL.md`'s "Daily use" flows (both docs-only and JIRA) noting the optional `uv run tools/metrics-report/main.py --repo-root .` step after archiving, and a one-line mention in the Prerequisites/Daily-use area that `metrics-reports/` is a new generated-output directory (should probably be `.gitignore`d or committed — **decide and document explicitly**, don't leave it ambiguous; recommendation: commit it, since it's meant to be shared/read by a team the same way `snapshots/` already is, unlike the genuinely-local `.story-events.jsonl` family)

## Dev Notes

### Scope — what this story is and is not

- This adds a **new, independent read-only tool** (`tools/metrics-report/main.py`) that consumes existing `snapshots/*.json` files — it does not change the snapshot assembler, the manifest, or any capture producer. `snapshots/*.json` remains the sole canonical, machine-readable source of truth (AD-3); this story only adds a human-readable rendering on top.
- **Do NOT build in this story:** any defect/testing/review-efficiency capture (that's Story 5.4, explicitly not started and blocked on a capture-mechanism decision) — this story only reserves an honest "not yet tracked" placeholder for those fields. Any HTML/dashboard output (that's Story 5.5, depends on this story's output). Any change to how/when snapshots are produced.
- **Do NOT try to update a markdown file in place / diff against the previous version.** Full regeneration from scratch (AC 5) is simpler, always correct, and avoids an entire class of "stale entry never got removed" bugs — resist the temptation to optimize this into an incremental update.

### Why `metrics-reports/` and not `docs/` (a resolved decision, not open for reinterpretation)

`docs/metrics.md` is *this specific repo's own* hand-maintained dogfooding ledger — a special, one-off artifact documenting explore-jira-ai-metrics's own development, not a convention every target project already has. A project adopting this tool via the release zip may have no `docs/` folder at all, or one used for unrelated purposes. `metrics-reports/` is a new, dedicated, top-level output directory this story introduces — parallel in spirit to `snapshots/` (another top-level output directory this pipeline already owns) — so the generated reports don't collide with or presuppose anything about a target project's existing docs structure.

### The `docs/metrics.md` format to mirror (read this before writing the renderer)

```markdown
## Story: 1.1 — Create the Story Manifest via Docs-Only Kickoff

- **Date**: 2026-07-09
- **Duration**: ~60 minutes (story creation ~17:20 → merged 18:19 IST, incl. one LLM review round)
- **Story Points**: 5 SP (retroactive AD-6 Phase-1: 6 tasks → base 3; volatility +0, full spec/architecture existed; novelty ×1.5 first-time pattern → 4.5 ≈ 5)
- **Total Defects**: 1
  - Compile Defects: 0
  - Unit Test Defects: 0
  - Peer Review Defects: 1 (...)
- **Testing Efficiency**: 0%
- **Review Efficiency**: 100%
- **Notes**: ...
```
This story's generated output mirrors this shape but is driven entirely by real snapshot fields, not hand-written narrative — where `docs/metrics.md` has rich prose (because a human wrote it), the generated report has whatever the snapshot can honestly support, explicitly marked "not yet tracked" where it can't (AC 4). Don't try to make the generated notes as rich as the hand-written original; that's not this story's job.

### Architecture compliance (binding invariants)

- **AD-3/AD-3b** — snapshots are the sole canonical source, immutable, revision-numbered, latest-is-current. This story's discovery logic (Task 1) must respect "latest revision wins" exactly as the assembler's own consumers are expected to.
- **AD-10** — null-with-reason, never a bare zero/omission. Every "not tracked" placeholder in this report must say *why*, using the `reason` string already present in the snapshot's `estimated_cost`/`token_cost` sections — don't invent new reason text when the snapshot already has one.
- **NFR3-adjacent**: this tool only *reads* `snapshots/*.json`; it must never write to that directory or mutate any snapshot file.

### Source tree touched

```text
tools/metrics-report/main.py          NEW    reads snapshots/*.json, groups by date, renders metrics-reports/metrics-<MMDDYYYY>.md
tests/metrics_report/test_report.py   NEW    tests for discovery/revision-selection/grouping, per-story rendering, idempotent regeneration
tools/build-release/INSTALL.md        UPDATE optional metrics-report step added to both Daily-use flows; metrics-reports/ directory noted
```

No existing files under `tools/snapshot-assembler/`, `tools/hooks/`, or `tools/adapters/` are touched.

### Project Structure Notes

New tool directory `tools/metrics-report/`, following the exact same structure/pattern as `tools/snapshot-assembler/` and `tools/opsx-wrapper/` (a single `main.py`, PEP 723 inline script header, stdlib-only).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.3] — the ask and its rationale
- [Source: docs/metrics.md] — the exact hand-maintained format this story's output mirrors (structure only, not the hand-written prose)
- [Source: tools/snapshot-assembler/main.py#next_revision, SCHEMA_VERSION] — the exact snapshot filename/revision convention this story's discovery logic must parse consistently with
- [Source: ARCHITECTURE-SPINE.md#AD-3, AD-3a, AD-3b, AD-10] — canonical-source, envelope-shape, revision-immutability, and null-with-reason invariants this story must respect
- [Source: project-context.md] — §1 stdlib-only, §2 no premature abstraction, §5-6 testing standards, §8-12 branch/PR/DoD

## Dev Agent Record

### Agent Model Used

claude-sonnet-5 (create-story context engineering + dev-story implementation)

### Debug Log References

- Task 0: added a test confirming `pm_metrics.name` round-trips from the manifest into the snapshot — confirmed failing (`KeyError`) before adding the field, passing after
- RED: 13 new tests in `tests/metrics_report/test_report.py` — confirmed failing (module didn't exist, then wrong assertions) before/during implementation
- GREEN: `uv run pytest tests/metrics_report/test_report.py tests/snapshot_assembler/test_reduce.py -q` → all passed after implementation
- Full suite: `uv run pytest -q` → 269 passed; `uv run ruff check .` clean; `uv run ruff format --check tools tests` flagged 1 file, fixed via `ruff format`, then clean
- **Live E2E against this project's own real accumulated snapshots** (not synthetic fixtures) — copied the two real snapshots from yesterday's docs-only and JIRA pilot tests (`story-20260713-ad362a`, `story-20260713-aebc40`) into a scratch repo and ran the generator. This caught two real gaps, both fixed before finalizing:
  1. `render_story()` never surfaced `pm_metrics.goal` anywhere in the output — a real content gap (not just a wrong test assumption), since goal is exactly the "what is this story about" information a report needs. Added a `**Goal**` line.
  2. Both real test snapshots predate Story 5.2's `estimated_cost` section entirely (they were generated before that story existed), so `Duration` showed "unknown duration" even though `engineering_metrics.first_event_at`/`last_event_at` were right there. Added `duration_minutes_of()` as a fallback that computes duration directly from `engineering_metrics` when `estimated_cost.duration_minutes` is unavailable — a real backward-compatibility gap for older-schema snapshots, not something the synthetic unit tests (which always included a full `estimated_cost` section) would have caught.
- Re-ran the E2E after both fixes — confirmed real, correct output: `~14 minutes`/`~20 minutes` durations, both goals now visible, `Total Defects`/efficiency fields honestly "not yet tracked"

### Completion Notes List

- Task 0: `pm_metrics.name` now round-trips from `.story.yaml` into every snapshot — a real, previously-undiscovered gap (present since Story 1.7 added `name` to the manifest, never carried into the snapshot). One-line fix, no AD-3a impact (within the existing `pm_metrics` sub-object, not a new top-level key).
- Task 1: `tools/metrics-report/main.py` discovers `snapshots/*.json`, keeps only the highest revision per `story_id` (AD-3b), and groups the survivors by the date portion of `engineering_metrics.last_event_at` (falling back to `pm_metrics.created` when the event log is empty). Writes to a new top-level `metrics-reports/` directory — deliberately not `docs/`, since a target project may not have one (Dev Notes explains the reasoning).
- Task 2: per-story rendering mirrors `docs/metrics.md`'s structure (Date, Goal, Duration, Story Points with Phase-1/Phase-2/variance when known, Estimated Cost, AI Token Cost, Notes) populated from real snapshot fields; null cost fields render as `"not tracked — {reason}"`, reusing the reason string the snapshot already carries rather than inventing new text. Defect/efficiency fields render as a fixed `"not yet tracked"` placeholder (Story 5.4 not started) via three flat literal lines — trivially replaceable with real lookups later, no structural rework needed.
- Task 3: regeneration is a full rewrite from scratch every run (glob + rebuild, never append) — confirmed idempotent (byte-identical on a repeat run with no new snapshots) and confirmed correctly dropping a stale entry once a story's snapshot is superseded by a newer revision.
- Task 4: full regression green; live E2E against real production snapshot data (not just fixtures) found and fixed 2 real gaps (missing Goal line; missing duration fallback for pre-5.2-schema snapshots) — both now covered by regression tests. `INSTALL.md` updated: an optional `metrics-report` step added to both Daily-use flows, plus an explicit note that `metrics-reports/` (like `snapshots/`) is meant to be **committed**, not `.gitignore`d — resolving the ambiguity the story flagged rather than leaving it undocumented.
- No new dependencies. No deviation from the story's design decisions (full regeneration, `metrics-reports/` over `docs/`, highest-revision-only rendering).

### File List

- tools/snapshot-assembler/main.py (modified — Task 0: `pm_metrics` dict gains `"name": manifest.get("name")`)
- tests/snapshot_assembler/test_reduce.py (modified — Task 0: updated the existing pm_metrics test, added a new name-round-trip test)
- tools/metrics-report/main.py (new — the generator: discovery/revision-selection/date-grouping, per-story rendering, full-regeneration write)
- tests/metrics_report/test_report.py (new — 13 tests covering discovery, revision selection, date grouping/fallback, per-story rendering including the Goal-line and old-schema-duration-fallback fixes found via live E2E, idempotent regeneration)
- tools/build-release/INSTALL.md (modified — optional `metrics-report` step added to both Daily-use flows; `metrics-reports/` documented as committed, not gitignored)
- _bmad-output/implementation-artifacts/5-3-metrics-date-md-generator.md (this file — task checkboxes, Dev Agent Record, status)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — story status transitions)
