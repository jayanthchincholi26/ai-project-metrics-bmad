---
baseline_commit: ffc694efa49bb565b3e8b0d5caef38fc8895a515
---

# Story 1.7: Docs-Only Kickoff Reads a Requirements Doc and Relaxes Sprint for Ad Hoc Teams

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer on a project with no PM tool,
I want kickoff to optionally read a requirements document I point it to, and to not force a fake sprint number on a team that doesn't run sprints,
so that docs-only kickoff is genuinely adapted to "no PM tool," not just "no JIRA/Confluence," and points/goal aren't guessed blind when a PRD already describes the work.

## Acceptance Criteria

1. **Given** `source_of_truth: docs-only` at kickoff
   **When** the skill runs
   **Then** it asks whether the developer has a requirements document (PRD) and, if so, its path
   **And** it reads `.md`/`.txt`/`.pdf`/`.docx` directly; a legacy binary `.doc` or unreadable file is not fatal — the skill says so plainly and falls back to the plain ask
   **And** the document's content is summarized, never dumped verbatim into the manifest or chat

2. **Given** a requirements document was read
   **When** the skill elicits points and goal
   **Then** it presents a document-derived suggestion for both, as a second advisory signal alongside any Phase-1 estimate (never silently written — same "suggest, human confirms" pattern as Phase-1; CAP-1 points confirmation stays human)

3. **Given** the skill elicits points, goal, and sprint
   **When** it prompts the developer
   **Then** it uses `AskUserQuestion` (structured options + freeform "Other") for **points** and **sprint**; **goal** is asked as free text (optionally pre-filled with a document-derived candidate) since a one-line objective doesn't fit a small options set
   **And** the goal question is phrased in plain language (e.g. "What does done look like for this story?"), never the bare word "Goal"

4. **Given** `source_of_truth: docs-only` specifically (JIRA/Confluence unaffected — they have a real sprint concept to pull from)
   **When** the developer has no milestone/release/sprint concept to give
   **Then** an explicit "none"/"N/A" answer is accepted as valid — the skill does not re-prompt forever demanding a fabricated value, and the manifest's `sprint` field is written as `null`
   **And** the elicitation wording reflects this (e.g. "Milestone, release, or time period this belongs to — say 'none' if you don't track this")
   **And** the manifest's `sprint` field itself stays named `sprint` regardless of backend (AD-4 normalized shape unchanged); JIRA/Confluence keep `sprint` required exactly as today — this relaxation is docs-only-only

5. **Given** `source_of_truth: docs-only` at kickoff (decided 2026-07-11: docs-only-only for now, not a cross-backend AD-4 shape change — see Held for later)
   **When** the skill elicits the required fields
   **Then** it additionally asks for a short, human-readable **Story Name** (e.g. "Auth Module Implementation") as free text, asked *before* goal/points/sprint
   **And** the manifest gains a new field `name`, inserted in the fixed key order immediately after `story_id`; it is `null` when absent (JIRA/Confluence calls to the shared writer never pass it in this story, so their manifests carry `name: null` — this is expected, not a bug)
   **And** the kickoff completion summary shown to the developer displays **Name** immediately after **Story ID**, so the summary is human-legible instead of only showing the opaque generated `story_id`

6. **Given** a developer has just completed docs-only kickoff
   **When** they aren't sure what to do next
   **Then** `INSTALL.md`'s "Daily use" section documents the real sequence with a concrete example: `/opsx:propose <change-name>` (a separate kebab-case name **the developer invents** — never the `story_id`) to start proposal/design/tasks artifacts, ideally run *before* kickoff so the Phase-1 estimator has a real `tasks.md` to read; then normal work; then `/opsx:apply`; then `/opsx:archive` to close the openspec change (git/Claude hooks capture continuously throughout, independent of this sequence)
   **And** when kickoff's Phase-1 estimate comes back null specifically because no openspec change was found (`phase1_points_reason` mentions "no openspec change found"), the skill adds a one-line, non-blocking nudge: something like "if this project uses openspec SDD, run `/opsx:propose <name>` before kickoff next time for an automatic estimate" (FR5 — informational only, never gates kickoff)

## Tasks / Subtasks

- [x] Task 1: Make `sprint` optional in the docs-only writer, backend-conditionally (AC: 4)
  - [x] Subtask 1.1 (RED): rewrote `test_blank_sprint_exits_2_and_writes_nothing` → `test_blank_sprint_exits_2_and_writes_nothing_for_jira`, `test_missing_sprint_argument_exits_2_and_writes_nothing` → `test_missing_sprint_exits_2_and_writes_nothing_for_jira` (both now pass `source-of-truth="jira"`, and the missing-sprint one now asserts `exit_code == 2` directly instead of `pytest.raises(SystemExit)`); added `test_blank_sprint_exits_2_and_writes_nothing_for_confluence`, `test_blank_sprint_is_null_for_docs_only`, `test_missing_sprint_is_null_for_docs_only`
  - [x] Subtask 1.2 (GREEN): `--sprint` is no longer `required=True` in `tools/adapters/docs-only/main.py`; validation is backend-conditional — `jira`/`confluence` still `fail()` on empty/missing, `docs-only` writes `sprint: None`
  - [x] Subtask 1.3: module docstring updated with the Story 1.7 sprint-nullability note

- [x] Task 2: PRD-read capability in the kickoff skill's docs-only path (AC: 1, 2)
  - [x] Subtask 2.1: SKILL.md step 4.1 asks once for a PRD path; "no"/no path skips to 4.2 unmodified
  - [x] Subtask 2.2: Read tool for `.md`/`.txt`/`.pdf`/`.docx`; unreadable/missing/legacy `.doc` falls back to 4.2, never fatal (FR5)
  - [x] Subtask 2.3: summarize only, never paste raw content into chat or `.story.yaml`; no new script/library (Read tool suffices)
  - [x] Subtask 2.4: document-derived points/goal suggestions, distinct from Phase-1, never silently written (CAP-1)

- [x] Task 3: Restructure points/sprint elicitation onto `AskUserQuestion`; reword goal and sprint (AC: 3, 4)
  - [x] Subtask 3.1: step 4.2 (points) and 4.4 (sprint) use `AskUserQuestion`; step 4.3 (goal) stays free text
  - [x] Subtask 3.2: points options = Phase-1/doc suggestion(s) + {1,2,3,5,8} + Other
  - [x] Subtask 3.3: sprint reworded to "Milestone, release, or time period"; explicit "None" option; selecting it omits `--sprint` (never passes literal "none")
  - [x] Subtask 3.4: goal reworded to "What does done look like for this story?"; manifest field/CLI flag name unchanged
  - [x] Subtask 3.5: re-prompt rule unchanged for points/goal; sprint's "none" is a valid complete answer for docs-only, never re-prompted

- [x] Task 4: Full regression, live E2E, and documentation parity (AC: 1-4)
  - [x] Subtask 4.1: `uv run pytest` (228 passed), `uv run ruff check .` (clean), `uv run ruff format --check tools tests` (clean)
  - [ ] Subtask 4.2: manual E2E in a real Claude Code session — **deferred to the user's own testing pass per their explicit request** (see Dev Agent Record); scenarios (a)-(d) are specified and ready to run
  - [x] Subtask 4.3: Boundaries section gained a line: PRD content is summarized only, never written to any tracked file
  - [x] Subtask 4.4: INSTALL.md updated (Task 6)

- [x] Task 5: Add an optional `name` field to the docs-only writer and its kickoff elicitation (AC: 5)
  - [x] Subtask 5.1 (RED): added `test_name_defaults_to_null`, `test_name_recorded_when_provided`, `test_multiline_name_collapses_to_one_line`, `test_name_is_null_for_jira_calls_that_do_not_pass_it`; updated `MANIFEST_KEYS` to insert `"name"` after `"story_id"` (both key-order assertions in the file use this one constant, so both are covered)
  - [x] Subtask 5.2 (GREEN): added optional `--name` argparse argument to `tools/adapters/docs-only/main.py`, cleaned like `goal`, inserted into the manifest dict immediately after `story_id`
  - [x] Subtask 5.3: SKILL.md step 4.0 asks for Story Name first, free text; passed via `--name`; 4a/4b (JIRA/Confluence) unchanged
  - [x] Subtask 5.4: step 5's completion relay now shows Name immediately after Story ID

- [x] Task 6: Document the kickoff → openspec/opsx sequencing (AC: 6)
  - [x] Subtask 6.1: `INSTALL.md` "Daily use" gained a concrete worked example (propose → kickoff → work → apply → archive → snapshot), explicit that the change name and `story_id` are unrelated
  - [x] Subtask 6.2: step 3's null-estimate message now includes the one-line `/opsx:propose` nudge

## Dev Notes

### Scope — what this story is and is not

- This story touches the **docs-only kickoff path only**. JIRA (Story 1.6) and Confluence (Story 1.4) variants are explicitly unaffected — their `sprint` stays required, and neither gets a document-read capability in this story (Held for later, below).
- **Do NOT build in this story:** structured extraction of a formal task list from a PRD (this story only supports human-facing summarization to *inform* a developer's own estimate, never automated point calculation from document content); a new adapter script for document reading (it's conversational, using the Read tool already available to the skill); extending document-read to JIRA/Confluence kickoffs; a `name` field for JIRA/Confluence (decided 2026-07-11 — docs-only-only for now; see Held for later).
- The `points`/`goal`/`description` manifest fields and their validation in `tools/adapters/docs-only/main.py` are **unchanged** by this story — `--sprint`'s requiredness changes conditionally on `--source-of-truth` (Task 1), and a new optional `--name` is added (Task 5, defaults `null`, docs-only-only elicitation).

### Held for later (explicitly out of scope, decided 2026-07-11)

- **Cross-backend `name` field.** JIRA's `summary` (already mapped to `goal` today) could plausibly also populate a normalized `name` field for JIRA/Confluence, giving every backend a consistent short title — but that changes the AD-4 shape for all three adapters, not just docs-only, and needs its own design pass (does `goal` then change meaning for JIRA too, or does `name` become a genuinely new *additional* fetched field?). Revisit as a dedicated story if story names are wanted across backends, not folded in here.

### Architecture compliance (binding invariants)

- **AD-4** — the adapter contract's normalized `{points, goal, sprint, description}` shape does not change. `sprint` becoming nullable for docs-only is a *value* relaxation, not a shape change — JIRA/Confluence already sometimes produce a `null` sprint internally (Story 1.3/1.6's `extract_sprint()` returns `None` when absent), but the kickoff skill's re-prompt rule has always forced a human-provided value before the writer is called for those two backends. This story is the first time a genuine `null` sprint is allowed to reach `.story.yaml` at all, and only via the docs-only path.
- **AD-5** — unaffected; `.story.yaml` remains the sole source of story identity, `story_id` generation is untouched.
- **AD-6 / AD-6a** — the document-derived points suggestion is a **third** advisory signal (alongside the developer's own judgment and the Phase-1 estimator), never a replacement for either, and never silently written. `points_estimated` continues to carry only the raw AD-6 Phase-1 number — do not repurpose it for the document-derived suggestion; if you want to preserve the document-derived number for later comparison, that is explicitly **out of scope** for this story (Held for later) since AD-6a's contract is specifically about the Phase-1/Phase-2 pair, not a third estimate source.
- **CAP-1** — points confirmation stays human regardless of how many advisory suggestions exist.
- **FR5** — nothing about a missing, unreadable, or malformed PRD may ever gate, skip, or block kickoff. Same principle already established for the Phase-1 estimator's failure path (SKILL.md step 3) — mirror that fallback pattern exactly for the PRD-read failure path.

### Sprint-optionality design (the one production-code decision this story makes)

Two designs were considered for AC 4; the writer-level `null` design was chosen over a "developer types the literal word 'none'" design:

- **Chosen: true `null`.** The skill omits `--sprint` entirely when the developer has no sprint concept; the writer (Task 1) treats an omitted/empty `--sprint` as valid *only* when `--source-of-truth docs-only`, writing `sprint: null`. This matches how JIRA/Confluence already represent "no sprint data" internally and keeps downstream consumers (any future per-sprint rollup) from having to special-case a fake sprint name.
- **Rejected: literal string `"none"`.** Would require zero script changes (just pass the literal text through), but creates a fake "none" bucket in any future sprint-based aggregation instead of a clean absence — judged not worth the shortcut given the writer change is one conditional, well-tested.

If the dev agent finds a reason to prefer the rejected design during implementation (e.g. a hidden assumption elsewhere in the codebase that `sprint` is always a non-null string), flag it in the PR rather than silently switching approaches.

### AskUserQuestion usage notes

- The tool requires 2-4 concrete options per question (plus its own built-in free-text "Other" the user can always select) — it is not a plain open-ended prompt. Design the points and sprint option sets accordingly (see Task 3.2/3.3); do not attempt to force `goal` through it, since a one-line free objective doesn't decompose into a small option set.
- Multiple questions can be asked in a single `AskUserQuestion` call (up to 4) — consider whether points and sprint can be combined into one call for a smoother flow, but this is a UX judgment call for the dev agent, not a hard requirement.

### Source tree touched

```text
.claude/skills/story-kickoff/SKILL.md   UPDATE  docs-only elicitation (step 4): name, PRD read, AskUserQuestion, rewording; step 3's null-estimate message (Task 6.2)
tools/adapters/docs-only/main.py        UPDATE  --sprint conditionally optional (Task 1); new optional --name (Task 5)
tests/adapters/test_docs_only.py        UPDATE  sprint-optionality tests + name-field tests + updated key-order assertions
tools/build-release/INSTALL.md          UPDATE  kickoff -> openspec/opsx sequencing example (Task 6.1)
docs/testing/                           UPDATE  new E2E scenarios (Task 4.2) — reuse the story-1.6-e2e.md pattern
```

No other files are touched. `tools/adapters/jira/main.py`, `tools/adapters/confluence/main.py`, and their tests are untouched — this story does not modify their behavior even though they share the docs-only writer as their manifest-writing backend (their calls always supply a non-empty `--sprint` after their own re-prompt rule, so Task 1's conditional change is invisible to them, and they never pass `--name` in this story).

### Testing standards (project-context.md §5/§6)

- `tools/adapters/docs-only/main.py`'s sprint-optionality change is fully unit-testable (pytest, no real git/process calls) — extend the existing fixture pattern in `tests/adapters/test_docs_only.py` (see `kickoff()` helper, `MANIFEST_KEYS` list). One behavior per test, Arrange/Act/Assert, sentence-style names.
- Everything in Task 2/3 (PRD read, AskUserQuestion elicitation, wording) is skill-flow work — pytest cannot reach it. Per this project's established pattern (Story 1.6's testing strategy), **manual E2E is the primary verification**, not a backstop. Task 4.2's four scenarios are the Definition of Done for this half of the story.

### Previous story intelligence (Story 1.1 and Story 1.6)

- Story 1.1 built the original docs-only writer and its "required, non-empty" validation for all three fields — this story is the first to relax any of that, and only for `sprint`, only for docs-only.
- Story 1.6 established the precedent this story extends: a skill-flow-only change (no adapter script involved) still needs a rigorous manual E2E script as its Definition of Done, structured as numbered pass/fail scenarios in `docs/testing/`. Follow that same file shape.
- Story 1.1's declined-review-finding style is worth reusing here too: if the dev agent considers and rejects an alternative design (e.g. during Task 2's format-support decision), log it explicitly in this file's Dev Agent Record rather than silently picking one.

### Project Structure Notes

- No conflicts with the unified project structure. Surface area is a subset of what Story 1.6 already touched (`.claude/skills/story-kickoff/SKILL.md`) plus one adapter script Story 1.1 created.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.7] — AC text and design-discussion context (this is where the story was first drafted, 2026-07-11)
- [Source: _bmad-output/implementation-artifacts/1-1-create-the-story-manifest-via-docs-only-kickoff.md] — original docs-only writer contract, sprint's original "required" rationale, testing patterns to extend
- [Source: _bmad-output/implementation-artifacts/1-6-jira-adapter-fetches-via-the-atlassian-remote-mcp-server.md] — the skill-flow-only-change + manual-E2E-as-primary-verification precedent this story follows
- [Source: ARCHITECTURE-SPINE.md#AD-4, AD-5, AD-6, AD-6a] — adapter contract, manifest-as-identity, two-phase estimation, points/estimate separation
- [Source: .claude/skills/story-kickoff/SKILL.md] — current flow this story extends (steps 3-4 specifically)
- [Source: tools/adapters/docs-only/main.py] — current sprint validation (`required=True`, non-empty check) this story conditionally relaxes
- [Source: tests/adapters/test_docs_only.py] — existing fixture/helper pattern (`kickoff()`, `MANIFEST_KEYS`) to extend
- [Source: project-context.md] — §1 stdlib-only/no-premature-abstraction, §5-6 testing standards, §8-12 branch/PR/DoD
- [Source: tools/estimate-phase1/main.py#find_change_dir] — confirms no story_id<->openspec-change-name link exists anywhere in the codebase (verified 2026-07-11 during story design); the "exactly one candidate directory" heuristic is the only linkage, which is why sequencing (propose before kickoff) matters for AC 6
- [Source: .claude/commands/opsx/propose.md, .claude/commands/opsx/archive.md] — real `/opsx:propose`/`/opsx:archive` command contracts (verified 2026-07-11) — the change name is developer-chosen kebab-case, never `story_id`; do not invent command syntax without checking these files

## Dev Agent Record

### Agent Model Used

claude-sonnet-5 (create-story context engineering + dev-story implementation)

### Debug Log References

- RED (Task 1): rewrote `test_blank_sprint_exits_2_and_writes_nothing` / `test_missing_sprint_argument_exits_2_and_writes_nothing` to target `source-of-truth=jira` explicitly; added `..._for_confluence` and two docs-only-null variants — confirmed failing against pre-change `main.py` (sprint still unconditionally required)
- GREEN (Task 1): `--sprint` required=False + backend-conditional validation → `uv run pytest tests/adapters/test_docs_only.py -q` → 34/34 passed
- RED (Task 5): added 4 `name`-field tests, updated `MANIFEST_KEYS` — confirmed failing (no `--name` arg existed yet)
- GREEN (Task 5): `--name` optional arg + manifest insertion after `story_id` → 38/38 passed
- Full suite after both: `uv run pytest -q` → 228 passed in 3.75s; `uv run ruff check .` clean; `uv run ruff format --check tools tests` clean (32 files)
- Tasks 2/3/5.3/5.4/6 are skill-flow (`.claude/skills/story-kickoff/SKILL.md`, `tools/build-release/INSTALL.md`) — not pytest-reachable; verified by careful re-read against every AC and cross-checked line-by-line against Story 1.6's equivalent skill-flow sections for consistency of pattern (FR5 fallback wording, AD-4 shape notes, CAP-1 human-confirmation language)

### Completion Notes List

- Task 1: `--sprint` is now `required=False` in `tools/adapters/docs-only/main.py`; validation is conditional on `--source-of-truth` (still required + `fail()` for jira/confluence, `null` for docs-only). Confirmed the two pre-existing tests were silently exercising the wrong backend (both omitted `source_of_truth`, defaulting to docs-only) and would have passed for the wrong reason if left unmodified — rewritten to explicitly target jira, per the story's own regression warning.
- Task 5: new optional `--name` field, backend-agnostic in the writer (any backend *could* pass it; only docs-only's skill path actually does, per the story's docs-only-only scope decision) — `null` when absent, positioned right after `story_id` in the fixed key order.
- Tasks 2/3/6: `SKILL.md` step 4 restructured into 4.0 (name) → 4.1 (optional PRD read) → 4.2 (points, `AskUserQuestion`) → 4.3 (goal, free text, reworded) → 4.4 (milestone/sprint, `AskUserQuestion`, "None" option). Step 3 gained the `/opsx:propose` nudge on a null Phase-1 estimate. Step 5's manifest-write command and completion-relay message both updated for `--name`/omittable `--sprint`. `INSTALL.md` gained a full worked propose→kickoff→apply→archive example, explicit that the change name and `story_id` are unrelated identifiers (verified against the real `.claude/commands/opsx/propose.md`/`archive.md` contracts, not assumed).
- **Deferred, by explicit user instruction:** Subtask 4.2 (manual E2E of the skill-flow scenarios) is intentionally left unchecked. The user's own stated plan for this story is: merge → tag a release → verify release docs → then personally re-run docs-only kickoff end-to-end in a fresh VS Code window as part of a broader "new developer experience" test pass (mirrors exactly how Story 1.6's E2E scenario A was verified live by the user post-implementation, not pre-emptively by the agent). The four scenarios from the story's Task 4.2 are fully specified in this file and ready to execute in that pass; nothing about them changed during implementation. Everything unit-testable (Tasks 1 and 5) is fully tested and green.
- No new dependencies. No architecture deviations from the story file — the sprint-optionality design (true `null`, not literal `"none"`) was implemented exactly as specified, no reason found to prefer the rejected alternative.

### File List

- tools/adapters/docs-only/main.py (modified — `--sprint` conditionally optional, new optional `--name`, docstring update)
- tests/adapters/test_docs_only.py (modified — sprint-optionality tests rewritten/added, name-field tests added, `MANIFEST_KEYS` updated)
- .claude/skills/story-kickoff/SKILL.md (modified — step 3 nudge, step 4 restructured with name/PRD-read/AskUserQuestion/rewording, step 5 command + relay message, Boundaries addition)
- tools/build-release/INSTALL.md (modified — Daily use section: openspec/opsx worked example)
- _bmad-output/implementation-artifacts/1-7-docs-only-kickoff-reads-a-requirements-doc-and-relaxes-sprint-for-ad-hoc-teams.md (this file — task checkboxes, Dev Agent Record, status)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — story status transitions)
