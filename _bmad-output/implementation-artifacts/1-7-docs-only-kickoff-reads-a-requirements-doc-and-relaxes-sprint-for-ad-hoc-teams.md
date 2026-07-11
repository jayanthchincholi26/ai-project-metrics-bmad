---
baseline_commit: ffc694efa49bb565b3e8b0d5caef38fc8895a515
---

# Story 1.7: Docs-Only Kickoff Reads a Requirements Doc and Relaxes Sprint for Ad Hoc Teams

Status: ready-for-dev

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

## Tasks / Subtasks

- [ ] Task 1: Make `sprint` optional in the docs-only writer, backend-conditionally (AC: 4)
  - [ ] Subtask 1.1 (RED): **two existing tests test the wrong thing after this change and must be rewritten, not just extended** — `test_blank_sprint_exits_2_and_writes_nothing` (line 251) and `test_missing_sprint_argument_exits_2_and_writes_nothing` (line 258) both call the `kickoff()` helper without overriding `source_of_truth`, so they exercise the **default backend (docs-only)** — after Task 1.2's change these exact calls will *succeed* (not fail), so left as-is they will fail for the wrong reason (a real regression the dev agent must not miss). Rewrite both to explicitly pass `source_of_truth="jira"` (proving sprint is still required there), and add two new docs-only-specific tests: blank/whitespace-only `--sprint` and omitted `--sprint`, both with `source_of_truth` left at its docs-only default, both asserting exit 0 and `manifest["sprint"] is None` (JSON `null`), with manifest key order otherwise unchanged. Also add one `--source-of-truth confluence` variant of the still-required case, for parity with jira
  - [ ] Subtask 1.2 (GREEN): in `tools/adapters/docs-only/main.py`, change `--sprint` from `required=True` to optional (default `None`). Validate conditionally: if `args.source_of_truth in ("jira", "confluence")`, an empty/missing sprint is still `fail("--sprint must not be empty")` (unchanged *behavior*, but now via the application-level `fail()` return path, not argparse's own enforcement — see the test-assertion-style note in 1.1); if `docs-only`, `clean(args.sprint)` empty or `args.sprint is None` writes `sprint: null` in the manifest rather than failing. **Nuance:** with `required=True` removed, argparse no longer raises `SystemExit` for a missing `--sprint` — `args.sprint` is simply `None` and application code decides. The rewritten jira/confluence "missing sprint" test must switch from `pytest.raises(SystemExit)` to the plain `exit_code = kickoff(...); assert exit_code == 2` style already used by every other validation-failure test in this file
  - [ ] Subtask 1.3: update the module docstring's AD-4 contract note to mention sprint's docs-only nullability; this is the **only** production code file this story updates (the change is small and precise) — do not touch `--points`/`--goal` validation, which are unaffected

- [ ] Task 2: PRD-read capability in the kickoff skill's docs-only path (AC: 1, 2)
  - [ ] Subtask 2.1: extend `.claude/skills/story-kickoff/SKILL.md` step 4 (the plain docs-only elicitation) — before asking points/goal/sprint, ask once: "Do you have a requirements document (PRD) for this story? If so, give me its path." A "no" or no path given skips straight to today's behavior (steps 3-4 below), unmodified
  - [ ] Subtask 2.2: if a path is given, read it with the Read tool. Supported: `.md`, `.txt`, `.pdf`, `.docx`. A legacy binary `.doc`, a missing file, or an unreadable file is **not fatal** — tell the developer plainly ("couldn't read that file — want to paste the text instead, or skip?") and fall back to the plain ask; never block kickoff on a bad path (FR5, same principle as the Phase-1-estimator-failure fallback already in step 3)
  - [ ] Subtask 2.3: summarize the document's relevant content (scope/objective, any hints toward complexity) — never paste the raw document text into chat or into `.story.yaml`. This is a purely conversational/skill-level capability; no new Python script or library is introduced (no PDF/DOCX parsing library needed — the Read tool already handles these formats; a genuinely stdlib-only script-level parser would be redundant and against the no-premature-abstraction standard for a one-consumer need)
  - [ ] Subtask 2.4: derive a candidate points value and a candidate one-line goal from the summary. Present both to the developer as **suggestions**, clearly labeled as document-derived and distinct from any Phase-1 estimate (step 3) — if both a Phase-1 estimate and a document-derived suggestion exist, show both and let the developer pick or override; neither is ever written without confirmation (AC 2, CAP-1)

- [ ] Task 3: Restructure points/sprint elicitation onto `AskUserQuestion`; reword goal and sprint (AC: 3, 4)
  - [ ] Subtask 3.1: rewrite SKILL.md step 4's elicitation to use the `AskUserQuestion` tool for **points** and **sprint** (2-4 concrete options each + the tool's built-in "Other" free-text path), and plain free-text chat for **goal** (pre-filled with the document-derived candidate from Task 2 when one exists, otherwise an open ask)
  - [ ] Subtask 3.2: points question options: include any Phase-1/document-derived suggestion(s) first, then common story-point values (e.g. 1, 2, 3, 5, 8) as additional options — "Other" always covers a value outside the preset list
  - [ ] Subtask 3.3: sprint question — reword away from "Sprint" to a backend-neutral phrasing (e.g. "Milestone, release, or time period this belongs to"). Options must include an explicit "None — this project doesn't track sprints/milestones" choice alongside 1-2 generic examples; selecting it, or answering "none"/"n/a" via "Other", means step 5 omits `--sprint` entirely (do not pass the literal string "none" — omit the flag so Task 1's writer change produces a true `null`, not a fake sprint name)
  - [ ] Subtask 3.4: goal question wording: replace the bare "**Goal** — one line describing what done looks like" with plain language, e.g. "What does done look like for this story?" — the underlying manifest field and the `--goal` CLI flag stay named exactly as today (AD-4 shape); only the developer-facing question wording changes
  - [ ] Subtask 3.5: the re-prompt rule (Story 1.1 AC 3) still applies to points and goal exactly as today; it applies to sprint **only for jira/confluence** — for docs-only, "none" is now itself a valid, complete answer, not a trigger for re-prompting

- [ ] Task 4: Full regression, live E2E, and documentation parity (AC: 1-4)
  - [ ] Subtask 4.1: run `uv run pytest`, `uv run ruff check .`, and `uv run ruff format --check tools tests` — all three, per the standing Story 3.2 PR #17 CI lesson (format is a separate gate from lint)
  - [ ] Subtask 4.2: manual E2E in a real Claude Code session (skill-flow change; pytest cannot reach conversational steps) — extend `docs/testing/story-1.6-e2e.md`-style coverage with a new scenario file or section: (a) docs-only kickoff with a real `.md` PRD path → suggestions presented, confirmed, `.story.yaml` correct; (b) docs-only kickoff, developer says "none" for sprint → `.story.yaml` has `sprint: null`, no re-prompt loop; (c) docs-only kickoff, bad/missing doc path → graceful fallback to plain ask, kickoff still completes; (d) JIRA kickoff (source_of_truth: jira) with no sprint on the issue → confirm sprint is **still required** and re-prompted exactly as before this story (regression check across the backend boundary)
  - [ ] Subtask 4.3: update `.claude/skills/story-kickoff/SKILL.md`'s "Boundaries" section if the PRD-read capability introduces any new boundary worth stating (e.g. "the skill never writes the document's own content into any tracked file")
  - [ ] Subtask 4.4: update `docs/testing/pre-deploy-smoke-checklist.md` or the release `INSTALL.md` only if this story changes anything a fresh install path would encounter (likely not — this is a conversational elicitation change, not an install/prerequisite change); note in the PR if no doc changes were needed there

## Dev Notes

### Scope — what this story is and is not

- This story touches the **docs-only kickoff path only**. JIRA (Story 1.6) and Confluence (Story 1.4) variants are explicitly unaffected — their `sprint` stays required, and neither gets a document-read capability in this story (Held for later, below).
- **Do NOT build in this story:** structured extraction of a formal task list from a PRD (this story only supports human-facing summarization to *inform* a developer's own estimate, never automated point calculation from document content); a new adapter script for document reading (it's conversational, using the Read tool already available to the skill); extending document-read to JIRA/Confluence kickoffs.
- The `points`/`goal`/`description` manifest fields and their validation in `tools/adapters/docs-only/main.py` are **unchanged** by this story — only `--sprint`'s requiredness changes, and only conditionally on `--source-of-truth`.

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
.claude/skills/story-kickoff/SKILL.md   UPDATE  docs-only elicitation (step 4): PRD read, AskUserQuestion, rewording
tools/adapters/docs-only/main.py        UPDATE  --sprint becomes conditionally optional (Task 1)
tests/adapters/test_docs_only.py        UPDATE  new sprint-optionality tests (regression-lock jira/confluence)
docs/testing/                           UPDATE  new E2E scenarios (Task 4.2) — reuse the story-1.6-e2e.md pattern
```

No other files are touched. `tools/adapters/jira/main.py`, `tools/adapters/confluence/main.py`, and their tests are untouched — this story does not modify their behavior even though they share the docs-only writer as their manifest-writing backend (their calls always supply a non-empty `--sprint` after their own re-prompt rule, so Task 1's conditional change is invisible to them).

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

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
