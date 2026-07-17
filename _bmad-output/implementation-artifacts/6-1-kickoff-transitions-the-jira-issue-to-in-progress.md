---
baseline_commit: e155b5c
---

# Story 6.1: Kickoff Transitions the JIRA Issue to "In Progress"

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer kicking off a JIRA-backed story,
I want the ticket to automatically move to "In Progress" the moment I start work,
so that the board reflects reality without a manual JIRA click.

## Acceptance Criteria

1. **Given** `source_of_truth: jira` and a kickoff fetch that actually used the Atlassian MCP path (`story-kickoff/SKILL.md` step 4a.2 — `getAccessibleAtlassianResources` + `getJiraIssue` succeeded)
   **When** step 5's manifest write (`tools/adapters/docs-only/main.py`) succeeds (exit 0)
   **Then** the skill resolves the issue's available transitions (`getTransitionsForJiraIssue` with the already-resolved `cloudId` and issue key) and calls `transitionJiraIssue` for the matched transition

2. **Given** a JIRA workflow that doesn't literally call its active-work state "In Progress" (workflow schemes vary across projects)
   **When** matching a transition
   **Then** match case-insensitively against a small allow-list of common names, in order: any `.story-config.yaml` override (`jira_in_progress_transition`, exact match, checked first) — if absent, `"In Progress"`, `"In Development"`, `"Doing"` (first match wins)

3. **Given** the transition step fails for any reason (no matching state found in the allow-list, permission denied, issue already in that state, `getTransitionsForJiraIssue`/`transitionJiraIssue` themselves error)
   **When** kickoff continues
   **Then** kickoff has **already completed successfully** at this point (the manifest was already written in step 5) — tell the developer plainly what happened with the transition as a **trailing note after** the normal kickoff summary, never before it, and never re-open or re-run any part of kickoff because of it (FR5)

4. **Given** `source_of_truth: confluence` or `docs-only`
   **When** kickoff runs
   **Then** nothing changes — no transition is attempted (Confluence pages have no workflow-status concept; docs-only has no ticket at all)

5. **Given** a JIRA-backed kickoff that did **not** use the MCP path — the Story 1.3 script fallback (`tools/adapters/jira/main.py`, env-var personal token) or the plain unassisted ask (`story-kickoff/SKILL.md` step 4a.4's degradation chain)
   **When** kickoff completes
   **Then** **no transition is attempted at all** — this is a deliberate, documented scope boundary, not a silent gap: `tools/adapters/jira/main.py` is a pure fetch-only script with no transition capability today, and building that capability into it (a second REST call using the same personal token) is explicitly out of scope for this story (see Dev Notes "Why the script-fallback path is out of scope")

## Tasks / Subtasks

- [x] Task 1: confirm the exact MCP tool shapes before writing instructions (AC: 1, 2)
  - [x] Subtask 1.1: tool-search `getTransitionsForJiraIssue` and `transitionJiraIssue` (deferred tools) to confirm their actual parameter names/shapes before referencing them in `SKILL.md` prose — do not guess at a parameter shape the way a hallucinated API would
  - [x] Subtask 1.2: confirm via `getAccessibleAtlassianResources`'s already-established reuse pattern (step 4a.2 resolves `cloudId` once per kickoff) that the same `cloudId` is valid input to both new tool calls — no second resolution needed

- [x] Task 2: `SKILL.md` — new step 4a.6 (AC: 1, 2, 3, 5)
  - [x] Subtask 2.1: add step 4a.6 immediately after step 5 in the document's own reading order (or cross-referenced from it), stating precisely: runs only after step 5's manifest write succeeds, only when step 4a.2's MCP fetch was the path actually used (not the script fallback, not the plain ask) — explicit per-path callout, matching AC 5's scope boundary
  - [x] Subtask 2.2: document the transition-matching precedence exactly as AC 2 states it (config override first, then the 3-name allow-list, first match wins)
  - [x] Subtask 2.3: document the non-blocking failure/trailing-note behavior exactly as AC 3 states it — this step can never cause kickoff (which already succeeded) to be reported as failed or incomplete
  - [x] Subtask 2.4: cross-reference this new step from step 4a's own numbered list header, the same way 4a/4b already cross-reference each other, so a reader scanning step 4a doesn't miss that a 6th sub-step now exists

- [x] Task 3: `.story-config.yaml.example` — new override key (AC: 2)
  - [x] Subtask 3.1: add `jira_in_progress_transition` next to the existing `jira_points_field`/`jira_sprint_field` overrides, following the exact same comment style and placement (only meaningful when `source_of_truth: jira`)

- [x] Task 4: `INSTALL.md` — document the new behavior and its real scope boundary (AC: 3, 5)
  - [x] Subtask 4.1: one new sentence in the JIRA daily-use flow's kickoff step noting the automatic In Progress transition
  - [x] Subtask 4.2: a new "Known limitations" entry stating plainly: the transition only happens via the MCP path; the script-fallback and plain-ask paths do not get it (AC 5) — and that a transition failure is reported as a trailing note, never as a kickoff failure (AC 3)
  - [x] Subtask 4.3: document the `jira_in_progress_transition` config override in the JIRA setup section, alongside the existing `jira_points_field`/`jira_sprint_field` overrides

- [x] Task 5: live verification (AC: 1, 2, 3, 4, 5)
  - [x] Subtask 5.1: real kickoff against a real JIRA issue in the connected Atlassian site, confirming the issue actually moves to an active-work state in the real JIRA UI, not just a log line claiming success
  - [x] Subtask 5.2: confirm a Confluence-backed and a docs-only kickoff are both completely unaffected (no transition attempted, no new prompts, byte-for-byte identical kickoff summary shape otherwise)
  - [x] Subtask 5.3: confirm the trailing-note behavior by deliberately using an issue whose workflow has no matching state name (or that's already in an active-work state) — kickoff summary must still report success for the manifest write itself, with the transition outcome appended after

## Dev Notes

### Scope — what this story is and is not

- This is a `story-kickoff/SKILL.md`-only change (a 6th sub-step under 4a), plus two small doc updates (`.story-config.yaml.example`, `INSTALL.md`) — no Python code, no pytest surface, same category as Stories 1.8/1.9.
- **Do NOT touch step 4b (Confluence) or the docs-only flow at all** — AC 4 requires them to be completely untouched.
- **Do NOT attempt to add transition capability to `tools/adapters/jira/main.py`** (the Story 1.3 script fallback) — see the dedicated note below on why this is a deliberate, not accidental, scope boundary.
- **Do NOT make a transition failure affect the reported kickoff outcome in any way** — by the time this step runs, step 5 has already written the manifest and kickoff has already succeeded. This step is purely additive telemetry-to-JIRA; its failure mode is "tell the developer, move on," never "kickoff failed."

### Why the script-fallback path is out of scope (found during story authoring, not assumed)

Read `tools/adapters/jira/main.py` directly (not from memory) before writing this story: it is a pure `urllib`-based fetch script — one `GET /rest/api/2/issue/{key}?fields=...` call, normalize, print JSON, exit. It has no transition capability today, and building one in would mean a second REST call (`POST /rest/api/2/issue/{key}/transitions`) added to a script whose entire reason for existing (per Story 1.6's own history) is a fallback for developers who don't have MCP connected — i.e., exactly the developers least likely to want more surface area in a credential-holding script. Building this now would be speculative reach beyond what this story's AC actually needs (project-context.md §7) — if real demand emerges for parity on that path, it's a separate, explicitly-scoped future story, not something to fold in silently here.

### Architecture compliance (binding invariants)

- **AD-4** — source-of-truth config is read-only, set once, never asked interactively. This story doesn't touch config resolution at all; it only reacts to an already-resolved `source_of_truth: jira`.
- **AD-5** — `.story.yaml` remains the sole source of story identity; this story writes nothing new to the manifest (no new field), it only performs an external JIRA-side side effect after the manifest is already correct.
- **FR5 (never block kickoff)** — the single invariant this story is built entirely around: a transition failure can only ever be a trailing, non-blocking note, never a retroactive kickoff failure, exactly like every other degradation chain already in this skill (step 3's estimator, step 4.1's requirements-doc read, step 4a/4b's own MCP fallbacks).
- **NFR4 (no credential exposure)** — the MCP path already carries no credential this skill ever sees (OAuth lives entirely in the MCP server's own session, per the skill's existing "Boundaries" section) — this story adds no new credential handling of any kind, since it's explicitly MCP-only (AC 5).

### Source tree touched

```text
.claude/skills/story-kickoff/SKILL.md          UPDATE  new step 4a.6 (transition to In Progress, MCP-path only)
tools/build-release/.story-config.yaml.example UPDATE  new jira_in_progress_transition override, documented
tools/build-release/INSTALL.md                 UPDATE  one sentence in the JIRA daily-use flow; new Known Limitations entry; config override documented in JIRA setup section
```

No files under `tools/` (Python code) or `tests/` are touched — same precedent as Stories 1.8/1.9/1.10 (skill-instruction/doc-only changes, no pytest surface).

### Testing standards (project-context.md §5/§6)

No pytest surface for this story (pure skill-instruction + doc change). Definition of Done is Task 5's live verification against a real JIRA issue — the same discipline this project has applied to every other MCP-touching, skill-instruction-only story (1.6, 1.8, 1.9).

### Project Structure Notes

No conflicts — extends `story-kickoff/SKILL.md` (already modified by Stories 1.6/1.7/1.8/1.9) and `INSTALL.md` (modified by nearly every story in this project by now). Builds on the `epic-6-jira-lifecycle-sync` integration branch, not `main` — this story's own branch (`story/6.1-...`) should be cut from `epic-6-jira-lifecycle-sync` and merged back into it, not into `main`, per the user's explicit instruction when this epic was reworked.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.1] — the ask and its rationale; note this story's AC 5 narrows the epic's original draft AC 1 ("MCP or script fallback") to MCP-only, a correction made during story authoring after reading `tools/adapters/jira/main.py`'s actual current code
- [Source: .claude/skills/story-kickoff/SKILL.md#4a] — the exact JIRA variant flow this story extends; step 4a.2's `cloudId` resolution, step 4a.4's degradation chain (the paths this story's AC 5 excludes), step 5's manifest-write success signal this story's new step depends on
- [Source: tools/adapters/jira/main.py] — confirmed fetch-only, no transition capability, grounding the AC 5 scope boundary
- [Source: tools/build-release/.story-config.yaml.example] — existing `jira_points_field`/`jira_sprint_field` override convention this story's `jira_in_progress_transition` follows
- [Source: project-context.md] — §7 no-premature-abstraction (grounds the script-fallback scope decision); FR5 non-blocking philosophy

## Dev Agent Record

### Agent Model Used

claude-sonnet-5 (create-story context engineering)

### Debug Log References

_(filled in during dev-story implementation)_

### Completion Notes List

_(filled in during dev-story implementation)_

### File List

_(filled in during dev-story implementation)_
