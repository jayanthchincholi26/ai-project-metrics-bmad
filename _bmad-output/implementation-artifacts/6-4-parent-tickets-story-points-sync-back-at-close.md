---
baseline_commit: 47ce9f1
---

# Story 6.4: Parent Ticket's Story Points Sync Back at Close

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As someone viewing the JIRA board,
I want the ticket's points field to reflect what was actually estimated by the end of the story,
so that JIRA isn't left showing a stale pre-work guess.

## Acceptance Criteria

1. **Given** `source_of_truth: jira`, a non-null `jira_issue_key`, and the existing close command (`story-close`'s step 6, Story 6.2) has just run successfully
   **When** `story-close` continues
   **Then** it parses the snapshot path out of the close command's own JSON output, reads `story_point_cost.phase2_points` from that snapshot file, and — if non-null — writes it to the parent issue's points field via `editJiraIssue` (using the same `jira_points_field` config key already used elsewhere) — **not** `pm_metrics.points` and **not** an at-close developer prompt (decided with the user when this epic was scoped)

2. **Given** `phase2_points` is null for any reason (e.g. a docs-only-style close with no real event activity)
   **When** the close-time sync runs
   **Then** it skips the write entirely rather than writing a null/zero (AD-10 null-with-reason philosophy, applied here to an outbound write instead of a snapshot field)

3. **Given** the write fails (permission denied, custom field misconfigured, the field doesn't accept the value's type)
   **When** `story-close` continues
   **Then** same non-blocking philosophy as every other write in this skill — report plainly, the story is already fully closed locally regardless (the close command already ran and already succeeded before this step even starts)

4. **Given** the close command itself fails (a failed archive/snapshot run)
   **When** `story-close` continues
   **Then** this new step never runs at all — there is no snapshot to read `phase2_points` from, and nothing about a failed local close should trigger any further JIRA write

5. **Given** the developer declined the earlier confirmation (Story 6.2's step 4 — sub-tasks/parent Done transition)
   **When** the close command still runs afterward (per Story 6.2's AC 5, declining never blocks the local close)
   **Then** the points sync-back in this story is covered by that **same** decline — extend the existing confirmation wording to also mention the points sync, rather than asking a second time after the close command runs

6. **Given** `source_of_truth: confluence`/`docs-only`, or `jira` with a null `jira_issue_key`
   **When** the story closes
   **Then** nothing changes — this step is skipped entirely, same passthrough boundary as the rest of `story-close`

## Tasks / Subtasks

- [ ] Task 1: extend `.claude/skills/story-close/SKILL.md` — the confirmation wording (AC: 5)
  - [ ] Subtask 1.1: update step 4's `AskUserQuestion` text to also mention the points sync (e.g. "...and sync its story points" appended to the existing "close N sub-task(s) and transition the parent... to Done" message) — one confirmation still covers everything, no new prompt

- [ ] Task 2: extend `.claude/skills/story-close/SKILL.md` — the new post-close step (AC: 1, 2, 3, 4, 6)
  - [ ] Subtask 2.1: add a new step 7, explicitly ordered *after* step 6 (running the close command) — state plainly why: `phase2_points` doesn't exist until the close command has actually produced a snapshot
  - [ ] Subtask 2.2: parse the snapshot file path from the close command's own stdout (the JSON ack line both `tools/snapshot-assembler/main.py` and `tools/opsx-wrapper/main.py archive` print on success — confirm the exact key name by reading both scripts' current output shape, don't assume)
  - [ ] Subtask 2.3: read that file, extract `story_point_cost.phase2_points`; if null, skip the write entirely (AC 2)
  - [ ] Subtask 2.4: if non-null, call `editJiraIssue` with the parent's `jira_issue_key`, setting the points field (`.story-config.yaml`'s `jira_points_field`, default `customfield_10016`) to that value
  - [ ] Subtask 2.5: this step only runs when steps 3-6 actually executed for a JIRA-backed story with the developer's confirmation (AC 5, 6) and the close command succeeded (AC 4) — a declined confirmation, a non-jira story, or a failed close command all skip it entirely

- [ ] Task 3: `INSTALL.md` — document the new behavior (AC: 1, 2, 3, 4)
  - [ ] Subtask 3.1: extend the existing JIRA daily-use flow's close-step paragraph (added by Story 6.2) to also mention the points sync-back
  - [ ] Subtask 3.2: extend the existing "review defect sub-tasks... points at creation" Known Limitations entry area with a short note on the parent's own points sync, or add a small new entry — cross-reference Story 6.2's entries rather than re-explaining the shared mechanics (confirmation gate, non-blocking failures, terminal-run limitation)

- [ ] Task 4: live verification (AC: 1, 2, 3, 4, 5, 6) — **coordinate with the user before running; this writes to a real JIRA issue's points field**
  - [ ] Subtask 4.1: real close-flow run (via the story's own close command, not just the JIRA-side calls in isolation) against a JIRA-backed scratch story tied to a real parent issue — confirm the parent's points field genuinely reflects the real computed `phase2_points` afterward (re-fetch independently, same discipline as every other Epic 6 story)
  - [ ] Subtask 4.2: confirm the `phase2_points`-null case skips the write cleanly (a scratch story with no real event activity) — the parent's points field must be left completely untouched, not zeroed

## Dev Notes

### Scope — what this story is and is not

- Pure extension of `.claude/skills/story-close/SKILL.md` (Story 6.2) plus a small `INSTALL.md` update — no new skill, no Python code, no pytest surface (unlike Stories 6.2/6.3, this one has no packaging concern since it doesn't add a new skill file).
- **Do NOT change `tools/snapshot-assembler/main.py`'s own `story_point_cost_of()` computation** — `phase2_points`'s formula (Story 2.6) is completely unchanged; this story only reads the already-computed value and writes it elsewhere.
- **Do NOT add a second confirmation prompt** — AC 5 is explicit: the existing one-confirmation-gate design (Story 6.2) is preserved by folding the points-sync mention into the same message, not asking again after the close command runs.
- **Do NOT attempt this before the close command runs** — this is the one real design correction from the original epic draft (see the sequencing note in `epics.md`'s own Story 6.4 section): `phase2_points` is computed *by* the close command, so there is no way to read it before that command has actually executed.

### Why the ordering matters (the real discovery here)

Read `.claude/skills/story-close/SKILL.md` (Story 6.2) fully before drafting this story, per its own create-story instruction. Its step 6 ("run the existing close command — always, last, unconditionally") is exactly why: the local snapshot — and therefore `phase2_points` — doesn't exist until that command has run. The original epic draft's AC 1 said "at the same close-time MCP step introduced by Story 6.2," which would have been impossible to implement correctly (nothing to read yet). Corrected in `epics.md` before this story file was written.

### `phase2_points`, for context (Story 2.6, unchanged by this story)

`round(review_cycles*1.0 + verification_files*1.0 + context_files*0.2)` — this project's own documented-invention formula (AD-6 specifies the four inputs, not the arithmetic). Null only when nothing about the story's activity could be measured at all. This story does not touch this calculation in any way, only reads its result.

### Architecture compliance (binding invariants)

- **FR5 (never block)** — same as every other Epic 6 story: a failed points write is reported and moved past, never treated as a story-close failure (the close already succeeded locally before this step even starts, AC 3/4).
- **AD-10 (null-with-reason)** — AC 2 is a direct application: never write a fabricated zero when `phase2_points` is null.
- **project-context.md §7 (no premature abstraction)** — this is a small, single addition to an existing skill's existing flow, not a new mechanism.

### Source tree touched

```text
.claude/skills/story-close/SKILL.md   UPDATE   step 4's confirmation wording (points mention); new step 7 (post-close points sync)
tools/build-release/INSTALL.md        UPDATE   JIRA daily-use flow close-step paragraph extended; Known Limitations note
```

No new files, no Python code, no pytest surface.

### Testing standards (project-context.md §5/§6)

No pytest surface (pure skill-instruction + doc extension). Definition of Done is Task 4's live verification — re-fetch independently after the write, never trust a write call's own "success" response alone, same discipline every prior Epic 6 story established.

### Project Structure Notes

Extends `.claude/skills/story-close/SKILL.md` (already built by Story 6.2, already extended once by nothing yet — this is its first post-6.2 change) and `INSTALL.md` (touched by nearly every story in this project by now). Builds on the `epic-6-jira-lifecycle-sync` integration branch, not `main` — this story's own branch (`story/6.4-...`) should be cut from it and merged back into it, not `main`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.4] — the reworked ask, including the sequencing correction made during story authoring
- [Source: .claude/skills/story-close/SKILL.md] — the exact existing flow this story extends (step 4's confirmation, step 6's close command, the file this story adds step 7 to)
- [Source: tools/snapshot-assembler/main.py] — `story_point_cost_of()`/`phase2_points`'s exact computation (Story 2.6, unchanged); the JSON ack shape printed on a successful real (non-dry-run) close
- [Source: tools/opsx-wrapper/main.py] — confirms it runs the assembler as an uncaptured subprocess (stdout inherited), so the assembler's own JSON ack line reaches the same place regardless of which close command path is used
- [Source: project-context.md] — FR5 non-blocking philosophy; AD-10

## Dev Agent Record

### Agent Model Used

claude-sonnet-5 (create-story context engineering)

### Debug Log References

_(filled in during dev-story implementation)_

### Completion Notes List

_(filled in during dev-story implementation)_

### File List

_(filled in during dev-story implementation)_
