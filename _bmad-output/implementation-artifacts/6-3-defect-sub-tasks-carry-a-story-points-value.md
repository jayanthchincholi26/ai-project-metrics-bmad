---
baseline_commit: b0c424e
---

# Story 6.3: Defect Sub-tasks Carry a Story-Points Value

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a JIRA board viewer,
I want each defect sub-task to carry a small point estimate,
so that sub-tasks show up realistically in JIRA reporting rather than as unestimated.

## Acceptance Criteria

1. **Given** a review defect is logged for a JIRA-backed story
   **When** the subtask is created
   **Then** the create call includes a story-points value on the subtask, defaulting to **1**, using the same `jira_points_field` config key already used for reading points at kickoff (no new config key introduced)

2. **Given** compile/test defects
   **When** they're captured
   **Then** nothing changes — still local-only, still the explicit non-goal Story 5.4 already documented (hooks can't reach MCP)

3. **Given** the review-defect-to-JIRA-subtask mechanism currently only exists in `project-context.md` §9 (this repo's own internal engineering-standards doc — never packaged into a release)
   **When** this story is done
   **Then** a new shipped skill (`.claude/skills/log-review-defect/SKILL.md`) carries the full instruction — create the subtask (with the points value from AC 1) via `createJiraIssue`, then run `tools/log-defect/main.py` — generalized for any project, not hardcoded to this repo, and packaged into the release the same way `story-kickoff`/`story-close` are (`tools/build-release/main.py`'s `SKILLS` list, both uninstall scripts, `INSTALL.md`)

4. **Given** the new shipped skill now fully specifies this mechanism
   **When** `project-context.md` §9 is reviewed
   **Then** it's simplified to reference the shipped skill's instructions rather than duplicating the mechanism inline — one source of truth, not two copies that can silently drift apart (the exact failure mode that caused this gap: the shipped product never got the instruction because it only ever lived in this repo's own private doc)

5. **Given** a JIRA-backed story with no `jira_issue_key` (an older story, or one predating Story 5.4), or a `source_of_truth: confluence`/`docs-only` story
   **When** a review defect is logged
   **Then** the new skill skips the `createJiraIssue` step entirely and just runs `tools/log-defect/main.py` with no `--jira-subtask-key` — byte-for-byte the same local-event behavior as today

6. **Given** a declined or stale review finding (confirmed not real, or already fixed elsewhere)
   **When** the developer/assistant is deciding whether to log it
   **Then** nothing about this story changes that rule — only a confirmed-real, actually-fixed finding is ever logged this way (unchanged from Story 5.4/project-context.md §9's existing rule)

## Tasks / Subtasks

- [ ] Task 1: new shipped skill `.claude/skills/log-review-defect/SKILL.md` (AC: 1, 3, 5, 6)
  - [ ] Subtask 1.1: frontmatter `description` written to trigger implicitly (same "hidden trigger" pattern as `story-close`, Story 6.2) — matched whenever a pasted code review's finding has been verified against the diff, confirmed real, and fixed
  - [ ] Subtask 1.2: step 1 — read `.story.yaml` for `source_of_truth` and `jira_issue_key`
  - [ ] Subtask 1.3: step 2 — for `source_of_truth: jira` with a non-null `jira_issue_key`: call `createJiraIssue` (`parent` = `jira_issue_key`, `issueTypeName: "Subtask"`, summary/description from the finding) with `additional_fields` setting the points custom field (`.story-config.yaml`'s `jira_points_field`, default `customfield_10016`) to **1** (AC 1) — generalize project-context.md §9's existing instruction, don't just copy it verbatim (it currently omits the points field entirely, which is exactly this story's fix)
  - [ ] Subtask 1.4: step 3 — for every other case (non-jira, or jira with null `jira_issue_key`): skip step 2 entirely (AC 5)
  - [ ] Subtask 1.5: step 4 — always run `uv run tools/log-defect/main.py --repo-root . --type review --summary "<finding summary>" --description "<finding description>" [--jira-subtask-key <key from step 2, if applicable>]` (unchanged from today's existing script — no code change to `tools/log-defect/main.py` itself needed)
  - [ ] Subtask 1.6: explicit rule carried over verbatim from project-context.md §9 (AC 6): only a finding confirmed real (against the diff) **and** actually fixed is ever logged this way — a declined/stale finding never is

- [ ] Task 2: package the new skill into the release artifact (AC: 3) — same pattern Story 6.2 already established for `story-close`, done proactively this time, not discovered mid-implementation
  - [ ] Subtask 2.1 (RED): extend `tests/build_release/test_build.py`'s existing `test_artifact_contains_the_deployable_surface` with an assertion for `.claude/skills/log-review-defect/SKILL.md` — confirm it fails first
  - [ ] Subtask 2.2 (GREEN): add the new skill path to `tools/build-release/main.py`'s `SKILLS` list (already a list since Story 6.2 — this is now a one-line addition, not a re-generalization)
  - [ ] Subtask 2.3: add `.claude/skills/log-review-defect` to both `tools/build-release/uninstall.sh` and `uninstall.ps1`'s removal path lists (same lists Story 6.2 already extended once)
  - [ ] Subtask 2.4: `INSTALL.md`'s Install step 1 description and Uninstall section wording — now three skills, not two

- [ ] Task 3: `project-context.md` §9 — remove the duplication (AC: 4)
  - [ ] Subtask 3.1: replace the inline `createJiraIssue`/`log-defect` instruction with a short reference to `.claude/skills/log-review-defect/SKILL.md` — confirm nothing project-specific is lost in the process (re-read the current §9 text fully before editing, don't paraphrase from memory)

- [ ] Task 4: `INSTALL.md` — document the new skill for end users (AC: 3, 5)
  - [ ] Subtask 4.1: a short new subsection (or addition to an existing one) explaining that a confirmed-and-fixed review defect on a JIRA-backed story now automatically creates a real Jira Subtask (with a points value) alongside the local defect event — mention this is the same implicit-trigger mechanism as `story-close` (Story 6.2), not a new command to learn
  - [ ] Subtask 4.2: a Known Limitations entry: same terminal-run limitation category as Stories 6.1/6.2 (only works inside a live Claude Code chat turn) — cross-reference rather than re-explain from scratch

- [ ] Task 5: live verification (AC: 1, 3, 5, 6) — **coordinate with the user before running; this creates a real Jira subtask**
  - [ ] Subtask 5.1: real invocation of the new skill's flow against a real JIRA-backed parent issue — confirm the created subtask genuinely carries the points value (re-fetch independently, same discipline as Stories 6.1/6.2), and confirm the local `tools/log-defect/main.py` event still gets appended correctly with the real `--jira-subtask-key`
  - [ ] Subtask 5.2: confirm the no-`jira_issue_key`/non-jira passthrough (AC 5) structurally — no live JIRA call needed for this branch, same as prior stories' passthrough verification

## Dev Notes

### Scope — what this story is and is not

- **Do NOT touch `tools/log-defect/main.py`** — it already accepts `--jira-subtask-key` and `--points` (used for the local event only, unrelated to the JIRA subtask's own points *field*); nothing about its own behavior needs to change.
- **Do NOT touch `tools/hooks/` (compile/test defect capture)** — AC 2 explicitly confirms this story doesn't touch the hook-captured, local-only path; that remains Story 5.4's documented non-goal (hooks can't reach MCP).
- **Do NOT invent a severity-based points scheme** (e.g. more points for a "Critical" finding vs. a "Low" one) — the reference tool and Story 6.2 both use a flat default of 1, override-able only via the same config key already used elsewhere; anything more is speculative reach beyond this story's actual ask.
- **This story's real, primary contribution is Task 1 + Task 3** (shipping the mechanism at all, and de-duplicating `project-context.md`), not just the points field — the points field alone (AC 1) is almost a footnote once AC 3/4 are understood; don't under-invest in the shipped-skill half while over-focusing on the one-line points addition.

### Why this matters (the real discovery, not the original narrow ask)

Researching where `createJiraIssue` is actually called (per this story's original create-story instruction: confirm this precisely before drafting tasks) found it exists **only** in `project-context.md` §9 — this repo's own internal engineering-standards doc, which is never packaged into `tools/build-release/main.py`'s release artifact (confirmed: `INSTALL.md`, `story-kickoff/SKILL.md`, and `story-close/SKILL.md` — the only three sources an end user's Claude Code session would ever see — mention nothing about creating a Jira subtask for a review defect). This means Story 5.4's review-defect-to-JIRA feature has, since it shipped, only ever worked for this repo's own dogfooding — a real end user installing `ai-metrics-capture` gets zero instruction telling their assistant to do this, ever. Confirmed with the user (2026-07-17) to fix both in this story: ship the missing instruction as a proper skill, and add the points field that was this story's original, narrower ask.

### Architecture compliance (binding invariants)

- **The MCP-only-from-a-live-turn constraint** (Story 5.4's own key architectural discovery, reused throughout Epic 6) — `tools/log-defect/main.py` still never touches MCP itself; the new skill's step 2 (subtask creation) must happen in the same live turn, before step 4 (`log-defect` invocation), exactly like today's `project-context.md` §9 instruction already requires.
- **AD-1a** — `ai.claude-code.defect_review` stays the event type; this story doesn't touch the event schema at all, only what happens *before* that event gets appended (a real JIRA write, with a points field this time).
- **project-context.md §7 (no premature abstraction / no duplication)** — AC 4 exists specifically to close a duplication gap, not create a new one; the shipped skill becomes the single source of truth for this mechanism, referenced (not re-copied) by `project-context.md` itself.
- **Terminal-run limitation** (same category as Stories 6.1/6.2) — this skill, like `story-close`, can only activate inside a live Claude Code chat turn.

### Source tree touched

```text
.claude/skills/log-review-defect/SKILL.md      NEW     the full review-defect-to-JIRA-subtask flow, generalized for any project
tools/build-release/main.py                    UPDATE  add the new skill path to the existing SKILLS list (one-line addition, Story 6.2 already did the generalization)
tools/build-release/uninstall.sh               UPDATE  add .claude/skills/log-review-defect to the removal list
tools/build-release/uninstall.ps1              UPDATE  add .claude/skills/log-review-defect to the removal list
tests/build_release/test_build.py              UPDATE  new assertion confirming the skill ships in the artifact
tools/build-release/INSTALL.md                 UPDATE  new subsection documenting the feature for end users; Known Limitations entry; Install/Uninstall wording for three skills
project-context.md                             UPDATE  §9 simplified to reference the shipped skill instead of duplicating its mechanism
```

### Testing standards (project-context.md §5/§6)

Same shape as Story 6.2: the skill file itself and `project-context.md`/`INSTALL.md` are skill-instruction/doc-only (no pytest surface), but the packaging half (Task 2) has a real, small pytest surface in `tests/build_release/test_build.py` — RED/GREEN discipline applies there, same as Story 6.2's Task 6. Definition of Done for the rest is Task 5's live verification — re-fetch independently after every write, never trust a write call's own "success" response alone.

### Project Structure Notes

New skill directory (`.claude/skills/log-review-defect/`) sits alongside `story-kickoff/` and `story-close/` — same single-`SKILL.md`-file convention. Builds on the `epic-6-jira-lifecycle-sync` integration branch, not `main` — this story's own branch (`story/6.3-...`) should be cut from it and merged back into it, not `main`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.3] — the reworked ask (scope expanded 2026-07-17, confirmed with the user)
- [Source: project-context.md §9] — the current inline instruction to generalize and then replace with a reference
- [Source: tools/log-defect/main.py] — confirmed unchanged; its own docstring already describes the "assistant creates the subtask first, in the same turn" convention this story's new skill formalizes properly
- [Source: .claude/skills/story-close/SKILL.md] — Story 6.2's own precedent for an implicitly-triggered skill (frontmatter description style) and for the packaging fix (Task 2 here mirrors Story 6.2's Task 6 exactly, done proactively this time)
- [Source: tools/build-release/main.py] — already a `SKILLS` list after Story 6.2; this story only appends one more entry
- [Source: tools/build-release/INSTALL.md] — the Known Limitations terminal-run-limitation entries (Stories 6.1/6.2) this story's own entry cross-references rather than re-explains

## Dev Agent Record

### Agent Model Used

claude-sonnet-5 (create-story context engineering)

### Debug Log References

_(filled in during dev-story implementation)_

### Completion Notes List

_(filled in during dev-story implementation)_

### File List

_(filled in during dev-story implementation)_
