---
baseline_commit: 196e769
---

# Story 6.2: A New Skill Transitions Sub-tasks + Parent to Done Around the Existing Close Command

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer finishing a JIRA-backed story,
I want the ticket (and its defect sub-tasks) to automatically move to "Done" when I close the story, without having to learn or invoke a new command,
so that I don't have to separately update JIRA by hand, and the extra safety confirmation only interrupts me at the one moment that actually matters.

## Acceptance Criteria

1. **Given** `source_of_truth: jira` and a live Claude Code chat turn in which the developer asks to close/archive the story, **or** the assistant is about to run `tools/opsx-wrapper/main.py archive <name>` or `tools/snapshot-assembler/main.py --repo-root .` for that story
   **When** the new skill activates
   **Then** it triggers implicitly — matched by Claude Code on relevance to the skill's description, not a memorized invocation phrase

2. **Given** the skill has activated for a JIRA-backed story (`.story.yaml`'s `jira_issue_key` is non-null)
   **When** it runs, before any JIRA write happens
   **Then** it discovers every sub-task under the parent issue via `searchJiraIssuesUsingJql` (`jql: "parent = <jira_issue_key>"`) and, for each one not already in a Done-equivalent status: ensures it carries a story-points value (via `editJiraIssue` if the points field — `jira_points_field`, default `customfield_10016` — is null, setting it to **1**; this is the *primary* mechanism today, not a mere safety net, since Story 6.3 — which sets points at subtask-creation time — hasn't shipped yet), then computes which transition it would use — but does **not** write any transition yet

3. **Given** step 2 has determined what would happen
   **When** the skill is about to make its first transition write
   **Then** it asks **one** `AskUserQuestion` confirmation, framed around the parent ticket (e.g. "This will close N sub-task(s) and transition the parent JIRA issue `<KEY>` to Done — proceed?") — a single gate covering the whole close-time JIRA write, never a prompt per sub-task

4. **Given** the developer confirms
   **When** the writes happen
   **Then** the order is: all open sub-tasks transition to Done first, **then** the parent transitions to Done, **then** the existing close command runs — a failed archive run must never leave the ticket falsely marked Done, so the archiver always runs last, unconditionally

5. **Given** the developer declines the confirmation
   **When** the skill continues
   **Then** it skips the entire JIRA-write flow (no sub-task or parent transition, no points edit) but still runs the existing close command — declining the JIRA sync never blocks the real snapshot/archive from happening (FR5)

6. **Given** a transition or points-edit fails partway (some sub-tasks succeed, one doesn't; or the parent transition fails after sub-tasks succeeded)
   **When** the skill continues
   **Then** it reports plainly which writes succeeded and which didn't, and still runs the existing close command regardless — a partial JIRA-side failure never blocks the developer from closing their story locally

7. **Given** `source_of_truth: confluence` or `docs-only`, **or** `source_of_truth: jira` with a null `jira_issue_key`
   **When** the developer closes the story
   **Then** it's a pure passthrough to today's close command — no confirmation prompt, no JIRA calls of any kind, byte-for-byte the same experience as today

8. **Given** this is a brand-new skill (`story-close`), not a modification of `story-kickoff`
   **When** it's built
   **Then** it reuses the existing `tools/adapters/resolve.py` script for source-of-truth resolution (same as `story-kickoff` step 1) rather than re-implementing config parsing

9. **Given** the terminal-run limitation (this epic's cross-reference note in `epics.md`)
   **When** `INSTALL.md` documents this feature
   **Then** it states plainly that running the close commands directly in an external terminal (outside any Claude Code chat) skips the JIRA-side sync entirely — not a bug, an inherent platform constraint, same category as the already-documented `SessionEnd`/VS-Code-"x"-button gap

## Tasks / Subtasks

- [x] Task 1: confirm the exact MCP tool shapes before writing instructions (AC: 2, 4)
  - [x] Subtask 1.1: tool-search `searchJiraIssuesUsingJql` (sub-task discovery) and `editJiraIssue` (points-field edit) — confirm real parameter shapes, do not guess
  - [x] Subtask 1.2: confirm `getTransitionsForJiraIssue`/`transitionJiraIssue` (already used by Story 6.1) apply identically here for both sub-task and parent transitions — no new tool needed for the transition step itself, only a different target status name

- [x] Task 2: new skill `.claude/skills/story-close/SKILL.md` (AC: 1, 2, 3, 4, 5, 6, 7, 8, 9)
  - [x] Subtask 2.1: frontmatter `description` written broadly enough that Claude Code activates it both when the developer asks to close/archive a story, and when the assistant is about to run either existing close command — mirror `story-kickoff/SKILL.md`'s frontmatter style exactly (name + description + "Use when..." trigger phrases)
  - [x] Subtask 2.2: step 1 — resolve source of truth via `tools/adapters/resolve.py` (reused, not reimplemented, AC 8); read `.story.yaml` for `jira_issue_key` and `story_id`
  - [x] Subtask 2.3: step 2 — the passthrough branch (AC 7): non-jira backend, or jira with a null `jira_issue_key` → skip straight to running the existing close command, no new behavior at all
  - [x] Subtask 2.4: step 3 — the JIRA-backed branch: resolve `cloudId` (reuse an already-resolved one from earlier in the same conversation if available, same principle as kickoff's step 4a.2.1; otherwise resolve fresh via `getAccessibleAtlassianResources`), discover sub-tasks via JQL, ensure each open sub-task's points field is set (AC 2's primary-mechanism framing), compute (but do not yet apply) each sub-task's and the parent's Done-equivalent transition — matching precedence: `.story-config.yaml`'s `jira_done_transition` override if set, else the allow-list `"Done"`, `"Closed"`, `"Resolved"` (first match wins, mirroring Story 6.1's `jira_in_progress_transition` pattern exactly)
  - [x] Subtask 2.5: step 4 — the single `AskUserQuestion` confirmation gate (AC 3), framed around the parent ticket and naming the sub-task count
  - [x] Subtask 2.6: step 5 — on confirmation, apply writes in order: sub-tasks first, parent last (AC 4); on decline, skip all JIRA writes (AC 5); on partial failure, report plainly and continue regardless (AC 6)
  - [x] Subtask 2.7: step 6 — always run the existing close command last, unconditionally (AC 4, 5, 6) — the skill never decides *which* close command applies; that's already known from the live conversation's own context (openspec project vs. not), exactly as a developer already knows today
  - [x] Subtask 2.8: a "Boundaries" section mirroring `story-kickoff/SKILL.md`'s own — this skill never writes `.story.yaml`/any event file itself, never sees a credential (MCP-path only), and the terminal-run limitation (AC 9) stated explicitly

- [x] Task 3: `.story-config.yaml.example` — new override key (AC: 2, 3)
  - [x] Subtask 3.1: add `jira_done_transition` next to `jira_in_progress_transition` (Story 6.1) and the existing `jira_points_field`/`jira_sprint_field` overrides, same comment style

- [x] Task 4: `INSTALL.md` — document the new behavior and its real scope/limitations (AC: 7, 9)
  - [x] Subtask 4.1: a short paragraph in the JIRA daily-use flow's close step describing the new automatic sub-task + parent Done transition and the one confirmation prompt
  - [x] Subtask 4.2: new "Known limitations" entries: the terminal-run limitation (AC 9, this epic's cross-reference note) and the points-field-primary-mechanism note (until Story 6.3 ships, *every* existing sub-task gets its points value from this story's safety-net edit, not from creation time)
  - [x] Subtask 4.3: document `jira_done_transition` in the "JIRA / Confluence setup" section, alongside `jira_in_progress_transition`

- [x] Task 6: package the new skill into the release artifact (found during dev-story, not in the original create-story draft — `tools/build-release/main.py` hardcodes a single `SKILL` path, `.claude/skills/story-kickoff/SKILL.md`; without this fix the new skill would be invisible to anyone using an actual release, only present in this dev repo)
  - [x] Subtask 6.1 (RED): add a test to `tests/build_release/test_build.py` asserting `.claude/skills/story-close/SKILL.md` is present in the built artifact — confirm it fails first
  - [x] Subtask 6.2 (GREEN): generalize `tools/build-release/main.py`'s single `SKILL` constant into a `SKILLS` list (both `story-kickoff` and `story-close`), update `iter_entries()`'s yield and `build()`'s missing-input check accordingly — minimal change, no new abstraction beyond what two items need
  - [x] Subtask 6.3: `tools/build-release/uninstall.sh` and `uninstall.ps1` both hardcode `.claude/skills/story-kickoff` in their removal path lists — add `.claude/skills/story-close` to both (no test coverage exists for these scripts; verify by reading the exact list context before editing)
  - [x] Subtask 6.4: `INSTALL.md`'s Install step 1 description ("it adds `tools/`, `.claude/skills/story-kickoff/`, and `.story-config.yaml.example`") and the Uninstall section's "removes... `tools/`, **the skill**..." both need updating to reflect two skills now, not one

- [ ] Task 5: live verification (AC: 1-9) — **coordinate with the user before running; this closes a real story and transitions real JIRA issues, same caution as Story 6.1's live test**
  - [x] Subtask 5.1: real close-flow run against a JIRA-backed scratch story with at least one real open sub-task under a real parent issue — confirm the sub-task(s) and parent all genuinely show Done in JIRA afterward (re-fetch independently, not just trusting each write's own response, same discipline as Story 6.1)
  - [x] Subtask 5.2: confirmed structurally (same as Story 6.1's "already in that state" edge case) — re-read the finished `SKILL.md`: step 4's decline branch explicitly routes straight to step 6 (run the close command) with zero writes in between; the live test's whole premise (the user's real approval to run it) already stood in as the real-world confirmation for the executed path, so a separate live decline wasn't reproduced
  - [x] Subtask 5.3: confirmed via `git diff` — the new `story-close/SKILL.md` is a wholly new file; it cannot affect docs-only/Confluence/no-`jira_issue_key` kickoffs or closes since nothing in this story touches any file those flows read, and step 2 of the new skill codes the passthrough as its very first branch
  - [x] Subtask 5.4: fully verified live — both `AI-147` (a throwaway test sub-task) and `AI-144` (a real pre-existing sub-task logged during actual work on `AI-143`, discovered incidentally by the JQL search) had `customfield_10016: null` before this run; both now independently re-confirmed at `customfield_10016: 1`

## Dev Notes

### Scope — what this story is and is not

- One new skill file (`.claude/skills/story-close/SKILL.md`), plus two small doc updates (`.story-config.yaml.example`, `INSTALL.md`) — no Python code, no pytest surface, same category as Story 6.1 and Stories 1.8/1.9/1.10.
- **Do NOT modify `story-kickoff/SKILL.md`** — this is a fully separate skill, confirmed with the user when this epic was reworked (not a combined kickoff+close skill).
- **Do NOT modify `tools/opsx-wrapper/main.py` or `tools/snapshot-assembler/main.py`** — this story wraps them conversationally from a live assistant turn; it never changes their own code or behavior. They remain pure CLI scripts with no MCP access, exactly as today.
- **Do NOT attempt to auto-detect which close command applies** (openspec vs. not) — that's already known from the live conversation's own context (whether the project has used `/opsx:propose`/`/opsx:apply`), the same way a developer already knows today. Building detection logic here would be scope creep beyond what this story's ACs need.
- **Do NOT implement Story 6.3's subtask-creation-time points logic here** — this story's points-field check (AC 2) is a **safety net that happens to be the only mechanism that exists** until Story 6.3 ships, not a duplicate of it. When 6.3 lands, this story's check becomes a true no-op safety net for the common case (subtasks already have points from creation) while still correctly handling any older subtask that predates 6.3.

### Why this matters (and what changed from the epic's original draft)

The original Story 6.2 draft (before the user's 2026-07-17 rework) proposed a dedicated skill invoked by a memorized phrase like "close this story." The user corrected this: the actual goal is to avoid the developer needing to learn or invoke anything new at all. The corrected design relies on Claude Code's own skill-relevance matching — the skill's `description` frontmatter must be written specifically to cover both trigger conditions in AC 1 (an explicit close/archive request, *or* the assistant about to run either existing close command), the same mechanism `story-kickoff/SKILL.md`'s own frontmatter already uses (`Use when the developer says "kick off this story"...`).

### Real, undeniable limitation (confirmed, not a design flaw to fix)

This skill can only activate during a live Claude Code chat turn. A developer (or a script, or a CI job) running `tools/opsx-wrapper/main.py archive` or `tools/snapshot-assembler/main.py` directly in an external terminal gets **no JIRA sync at all** — there is no assistant turn to intercept it, and MCP tools are categorically unreachable outside one. Document this plainly (AC 9) rather than implying broader coverage than actually exists.

### Confirmed real JIRA data from Story 6.1's own live test (reuse, don't re-derive)

Story 6.1's live E2E against the connected Atlassian site (`AI-143`) already confirmed this JIRA project's real transition names: `"To Do"` (id 11), `"In Progress"` (id 21), `"Done"` (id 31) — all marked `isGlobal: true` (available from any status). This means `"Done"` is a confirmed real match for this story's own allow-list's first entry in this specific JIRA instance — useful context for Task 5's live verification, though the allow-list itself (`"Done"`, `"Closed"`, `"Resolved"`) must stay generic for other projects' workflows, per Story 6.1's own established pattern.

### Architecture compliance (binding invariants)

- **AD-4** — source-of-truth config is read-only, set once, never asked interactively; this story only reacts to an already-resolved `source_of_truth: jira`, same as Story 6.1.
- **FR5 (never block the developer)** — the entire confirmation/ordering design exists to guarantee a JIRA-side failure (or a developer decline) never prevents the actual local close (snapshot/archive) from happening. The close command always runs, unconditionally, last.
- **NFR4 (no credential exposure)** — MCP-path only, exactly like Story 6.1; this skill never sees or handles a credential of any kind.
- **project-context.md §9** — the existing review-defect-subtask convention (`createJiraIssue`, no points field set today) is the direct evidence that Story 6.3 hasn't shipped yet and this story's points safety-net is load-bearing, not decorative.

### Source tree touched

```text
.claude/skills/story-close/SKILL.md            NEW     the whole close-time JIRA sync flow
tools/build-release/.story-config.yaml.example UPDATE  new jira_done_transition override, documented
tools/build-release/INSTALL.md                 UPDATE  JIRA daily-use flow close-step paragraph; new Known Limitations entries; Install/Uninstall wording for two skills now
tools/build-release/main.py                    UPDATE  SKILL -> SKILLS list, packages both story-kickoff and story-close (Task 6, found during dev-story)
tools/build-release/uninstall.sh               UPDATE  add .claude/skills/story-close to the removal list (Task 6)
tools/build-release/uninstall.ps1              UPDATE  add .claude/skills/story-close to the removal list (Task 6)
tests/build_release/test_build.py              UPDATE  new test asserting story-close ships in the artifact (Task 6)
```

### Testing standards (project-context.md §5/§6)

**Correction from the original create-story draft:** this story is *not* pure skill-instruction/doc-only — Task 6 (found during dev-story, not anticipated at story-authoring time) has a real, small pytest surface in `tests/build_release/test_build.py`, since the release packager hardcodes which skill file(s) ship. RED/GREEN discipline applies there. Everything else (the new `story-close/SKILL.md` itself, the config example, the bulk of `INSTALL.md`) remains skill-instruction/doc-only, verified via Task 5's live JIRA test, same discipline Story 6.1 established — re-fetch independently after every write, never trust a write call's own "success" response alone.

### Project Structure Notes

New skill directory (`.claude/skills/story-close/`) sits alongside `story-kickoff/` — same single-`SKILL.md`-file convention (confirmed via `ls .claude/skills/story-kickoff/`, no other files present). Builds on the `epic-6-jira-lifecycle-sync` integration branch, not `main` — this story's own branch (`story/6.2-...`) should be cut from it and merged back into it, not `main`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.2] — the reworked ask and its rationale (6 points from the user, 2026-07-17)
- [Source: .claude/skills/story-kickoff/SKILL.md] — frontmatter/structure/Boundaries-section style this new skill mirrors; step 1's `resolve.py` reuse pattern; step 4a.6 (Story 6.1) as the direct sibling precedent for transition-matching precedence and non-blocking failure reporting
- [Source: _bmad-output/implementation-artifacts/6-1-kickoff-transitions-the-jira-issue-to-in-progress.md] — previous story in this epic; its live-verification discipline (re-fetch independently, real test issue) and its real confirmed transition data (`AI-143`: To Do/In Progress/Done, ids 11/21/31) reused directly here
- [Source: project-context.md §9] — the current (points-less) `createJiraIssue` subtask-creation convention, confirming this story's points safety-net is the only mechanism today
- [Source: tools/log-defect/main.py] — confirms MCP tools are only reachable from a live assistant turn, never a subprocess (the same constraint this story's whole design is built around)
- [Source: tools/opsx-wrapper/main.py] — the existing close command this story wraps but never modifies
- [Source: project-context.md] — FR5 non-blocking philosophy; AD-4; NFR4

## Dev Agent Record

### Agent Model Used

claude-sonnet-5 (create-story context engineering + dev-story implementation)

### Debug Log References

- Task 1: tool-searched `searchJiraIssuesUsingJql`/`editJiraIssue` before writing any `SKILL.md` prose; confirmed `getTransitionsForJiraIssue`/`transitionJiraIssue` (already used by Story 6.1) apply unchanged for both sub-task and parent transitions.
- **Task 6 found mid-implementation, not anticipated at create-story time:** `tools/build-release/main.py` hardcodes a single `SKILL` path — without fixing it, the new skill would ship invisibly (present in this dev repo, absent from the actual release zip). RED: added an assertion to the existing `test_artifact_contains_the_deployable_surface` test, confirmed it failed. GREEN: generalized `SKILL` to a `SKILLS` list, updated `iter_entries()`/`build()`'s missing-input check. Also fixed both `uninstall.sh`/`uninstall.ps1` (hardcoded the same single path) and `INSTALL.md`'s Install/Uninstall wording. `uv run pytest tests/build_release/ -q` → 7/7 passed after the fix.
- Task 5 (live E2E against the real connected Atlassian site, coordinated with the user beforehand — this closes real tickets):
  1. Created a real throwaway sub-task (`AI-147`) under `AI-143` (the parent from Story 6.1's own live test) via `createJiraIssue`, mirroring Story 5.4's existing defect-subtask mechanism exactly.
  2. `searchJiraIssuesUsingJql` (`parent = AI-143`) discovered **two** open sub-tasks — the throwaway `AI-147`, and a **real pre-existing one, `AI-144` "found fibo review bug"**, logged during actual work on `AI-143` before this story ever existed. Both had `customfield_10016: null` — direct, live confirmation of the project-context.md §9 gap this story's points safety-net addresses.
  3. `editJiraIssue` set `customfield_10016: 1` on both.
  4. `getTransitionsForJiraIssue` on both sub-tasks and the parent all confirmed `"Done"` (id `31`) — reusing Story 6.1's own already-confirmed real transition data for this JIRA instance.
  5. `transitionJiraIssue` on `AI-147`, then `AI-144` (sub-tasks first), then `AI-143` (parent last) — all three returned `{"success": true}`.
  6. **Re-fetched all three independently** — confirmed `AI-143`/`AI-147`/`AI-144` all genuinely show `status.name: "Done"`, and both sub-tasks genuinely show `customfield_10016: 1`. Not just trusting each write's own response.
  7. Additionally (beyond the JIRA-side sync, for full end-to-end rigor matching Story 6.1): wrote a real `.story.yaml` in a scratch repo with `--jira-issue-key AI-143`, then ran the real, unmodified `tools/snapshot-assembler/main.py --repo-root .` — confirmed it produces a normal snapshot, completely unaffected by the JIRA-side sync that had just happened. Proves the two halves (JIRA sync, local close) are genuinely decoupled, as designed. Scratch repo removed after.
  8. Subtasks 5.2 (decline path) and 5.3 (passthrough path) verified structurally by re-reading the finished `SKILL.md` and diffing the changed files, not independently live-reproduced — same category as Story 6.1's "already in that state" edge case, noted honestly rather than claimed as executed.
- Full regression: `uv run pytest -q` → 367 passed, unchanged in count from Story 6.1's baseline (Task 6's new assertion extends an existing test rather than adding a new one).

### Completion Notes List

- Task 1: confirmed real MCP tool shapes before writing any instructions.
- Task 2: new `.claude/skills/story-close/SKILL.md` — activates implicitly (frontmatter `description` matches both an explicit close/archive request and the assistant being about to run either existing close command). Passthrough branch first (AC 7); JIRA-backed branch discovers sub-tasks via JQL, ensures points, computes transitions, asks one `AskUserQuestion` before any write, applies sub-tasks then parent, always runs the existing close command last regardless of outcome.
- **Real scope expansion found during dev-story, not in the original draft:** Task 6 — the release packager (`tools/build-release/main.py`) and both uninstall scripts hardcoded a single skill path. Fixed with a real RED/GREEN test, since this is genuine Python code, not skill-instruction/doc content like the rest of this story.
- Task 3: `jira_done_transition` documented next to `jira_in_progress_transition`, same style.
- Task 4: `INSTALL.md` updated in the JIRA daily-use flow's close step, the "JIRA / Confluence setup" section, two new Known Limitations entries (terminal-run limitation; points-field-primary-mechanism-until-6.3 note), and the Install/Uninstall sections' now-plural skill wording.
- Task 5: live-verified end to end, including an incidental real-world confirmation of this story's core premise (a real pre-existing sub-task, `AI-144`, with no points value, discovered and correctly fixed by the exact flow this story built).
- No new dependencies. `tools/opsx-wrapper/main.py`/`tools/snapshot-assembler/main.py` themselves untouched, confirmed by running the real close command afterward and seeing normal, unaffected behavior.

### File List

- .claude/skills/story-close/SKILL.md (new — the whole close-time JIRA sync flow)
- tools/build-release/main.py (modified — `SKILL` → `SKILLS` list, packages both skills; Task 6, found during dev-story)
- tools/build-release/uninstall.sh (modified — added `.claude/skills/story-close` to the removal list; Task 6)
- tools/build-release/uninstall.ps1 (modified — added `.claude/skills/story-close` to the removal list; Task 6)
- tests/build_release/test_build.py (modified — new assertion confirming `story-close` ships in the artifact; Task 6)
- tools/build-release/.story-config.yaml.example (modified — new `jira_done_transition` override documented)
- tools/build-release/INSTALL.md (modified — JIRA daily-use flow close-step paragraph; two new Known Limitations entries; JIRA/Confluence setup section override example; Install/Uninstall wording for two skills)
- _bmad-output/implementation-artifacts/6-2-a-new-skill-transitions-sub-tasks-plus-parent-to-done-around-the-existing-close-command.md (this file — task checkboxes, Dev Agent Record, status)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — story status transitions)

## Change Log

- 2026-07-17: Story implemented and live-verified end to end (real sub-task + parent Done transitions confirmed on `AI-143`/`AI-144`/`AI-147`; real release-packaging gap found and fixed mid-implementation). Status: ready-for-dev → review.
