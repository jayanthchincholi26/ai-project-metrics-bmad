---
baseline_commit: 5a71c43
---

# Story 1.10: INSTALL.md Documents the Confluence Flow

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer whose project uses Confluence as its source of truth,
I want INSTALL.md to document the Confluence setup and daily-use flow with the same completeness as JIRA's,
so that I'm not left guessing how to configure or use a fully-built, already-shipped backend.

## Acceptance Criteria

1. **Given** the Prerequisites table's JIRA-only MCP row
   **When** this story is done
   **Then** it covers both JIRA and Confluence, noting they share one Atlassian MCP connection

2. **Given** the existing "JIRA setup" section
   **When** this story is done
   **Then** it becomes "JIRA / Confluence setup," documenting the shared MCP connection steps once, JIRA-specific custom-field overrides, and a new Confluence-specific subsection explaining that MCP fetches the goal (page title) but cannot read points/sprint page labels — and that real label auto-fill requires the Story 1.4 script fallback (personal API token), not the MCP path

3. **Given** the existing "Daily use — docs-only flow" and "Daily use — JIRA flow" sections
   **When** this story is done
   **Then** a new "Daily use — Confluence flow" section exists with the same structure and completeness (fresh branch through checking the snapshot), including the full-URL-not-short-link kickoff guidance and the same `/opsx:propose`-after-kickoff ordering rationale as JIRA

4. **Given** "Known limitations"
   **When** this story is done
   **Then** it gains an entry stating that Confluence kickoff never auto-fills points/sprint via MCP (goal only), consistent with the honest-tradeoff framing already used for `token_cost`/duration limitations elsewhere in the file

5. **Given** this is a pure documentation change
   **When** Definition of Done is evaluated
   **Then** there is no pytest surface — the check is a self-review re-read cross-checked against `story-kickoff/SKILL.md`'s actual step 4b logic, not an automated test

## Tasks / Subtasks

- [x] Task 1: Prerequisites and setup sections (AC: 1, 2)
  - [x] Subtask 1.1: Broaden the Prerequisites table's row 5 to cover both `source_of_truth: jira` and `confluence`, noting the shared MCP connection and that auto-fill completeness differs (JIRA full, Confluence partial)
  - [x] Subtask 1.2: Rename "JIRA setup" to "JIRA / Confluence setup"; keep the shared MCP connect/auth steps as steps 1-2 (unchanged), move the JIRA custom-field override to an explicitly labeled "JIRA only" step, and add a new "Confluence only" step explaining the MCP page-label gap precisely as `story-kickoff/SKILL.md` step 4b actually describes it — not a simplified/inaccurate version
  - [x] Subtask 1.3: In the new Confluence-only step, be precise about *when* the script fallback (env vars) actually activates — only when MCP tools are unavailable in the session at all, never as a simple opt-in alongside an active MCP connection, since MCP is always preferred when available

- [x] Task 2: Daily use — Confluence flow (AC: 3)
  - [x] Subtask 2.1: Write a new "Daily use — Confluence flow" section mirroring the JIRA flow's step structure and count (branch → kickoff → optional openspec propose/apply → work → commit/push → close → check snapshot → optional report/dashboard)
  - [x] Subtask 2.2: Kickoff step explicitly instructs pasting the full Confluence page URL (not a short link), matching `story-kickoff/SKILL.md`'s documented reasoning (short links can't be resolved to a page ID by the MCP tools)
  - [x] Subtask 2.3: State plainly in the kickoff step that points/sprint are always manual via the MCP path, cross-referencing the "JIRA / Confluence setup" section's fuller explanation rather than re-explaining it
  - [x] Subtask 2.4: Add the same `/opsx:propose`-after-kickoff ordering rationale as the JIRA flow, generalized correctly (`/opsx:propose` has no Atlassian-fetching capability of any kind, not just no JIRA-fetching capability)

- [x] Task 3: Known limitations and cross-references (AC: 4)
  - [x] Subtask 3.1: Add a new "Known limitations" entry stating the Confluence points/sprint MCP gap plainly, in the same honest-tradeoff voice as the existing `token_cost`/duration entries
  - [x] Subtask 3.2: Fix the two remaining stale JIRA-only cross-references that this change makes inaccurate: "Data use and privacy"'s "see 'JIRA setup' above" pointer, and Troubleshooting's "JIRA MCP server"/"JIRA MCP tools" wording (the underlying issue and fix apply identically to Confluence, same shared MCP server)

- [x] Task 4: Self-review pass (AC: 5)
  - [x] Subtask 4.1: Read the finished file end to end; cross-check the new Confluence content word-for-word against `story-kickoff/SKILL.md`'s actual step 4b logic (not assumption) — specifically the exact conditions under which the script fallback activates, and the two confirmed MCP platform gaps (no label read, no short-link resolution)
  - [x] Subtask 4.2: Confirm `uv run pytest -q` is unaffected (a pure doc change should not touch any test file) — full suite still green

## Dev Notes

### Scope — what this story is and is not

- Pure documentation change to `tools/build-release/INSTALL.md`. No code in `tools/`, no new script, no manifest/schema change — same precedent as Story 5.1.
- **Do NOT invent new Confluence capabilities or imply the MCP label gap is fixed** — this story only documents what `story-kickoff/SKILL.md`'s step 4b already does today. If the platform gap is ever closed upstream, that's a future story's content update, not this one's.
- **Do NOT claim the script-fallback env vars are a simple "opt-in for better auto-fill"** — get the actual activation condition right (only when MCP tools aren't available in the session at all), since overstating it would set a wrong expectation for someone who has MCP connected for JIRA and assumes the same env vars will "also" improve Confluence auto-fill in that same session.

### Why this matters

Noticed directly by the user while reading the installed `INSTALL.md` right after cutting release v0.10.0: Confluence (`source_of_truth: confluence`) has been a complete, tested, live-verified backend since Stories 1.4 and 1.8 (a real live kickoff against a real Confluence page, `story-20260715-480790`), yet `INSTALL.md` — the primary document a new adopter reads — has zero dedicated coverage for it. Only docs-only and JIRA have full setup/daily-use sections.

### Architecture compliance (binding invariants)

- No AD/architecture invariant is touched — presentation-only, same as Story 5.1. AD-4 (source-of-truth config is read-only, set once, never asked interactively) is unaffected; this story only documents the existing Confluence path, it doesn't change kickoff behavior.
- `project-context.md` §12 (Story DoD) applies minus the automated-test bullet (N/A for a docs-only change, same precedent as Stories 2.10/5.1).

### Testing standards (project-context.md §5/§6)

- No pytest surface, same precedent as Story 5.1. Definition of Done is the self-review re-read specified in AC 5/Task 4, cross-checked against `story-kickoff/SKILL.md`'s actual logic rather than assumption.

### Source tree touched

```text
tools/build-release/INSTALL.md   UPDATE   Prerequisites row broadened; "JIRA setup" -> "JIRA / Confluence setup" with a new Confluence subsection; new "Daily use — Confluence flow" section; new Known Limitations entry; two stale JIRA-only cross-references fixed
```

No files under `tools/` (code) or `tests/` are touched.

### Project Structure Notes

No conflicts — this is the same file Stories 1.6, 1.7, 2.7, 2.11, 2.12, 3.5, and 5.11 have each incrementally updated before.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.10] — the finding and its rationale
- [Source: .claude/skills/story-kickoff/SKILL.md#4b] — the actual, authoritative Confluence kickoff logic this story's content must match exactly (MCP fetch conditions, the two platform gaps, the script-fallback activation condition)
- [Source: tools/build-release/INSTALL.md] — the file being extended; current content (JIRA/docs-only sections) is the structural template for the new Confluence sections
- [Source: project-context.md] — §12 Story DoD (docs-only precedent, no automated-test bullet)

## Dev Agent Record

### Agent Model Used

claude-sonnet-5 (create-story context engineering + dev-story implementation)

### Debug Log References

- No pytest surface for this story (pure documentation change, per Dev Notes) — Definition of Done is the self-review re-read specified in AC 5/Task 4.
- Ran `uv run pytest -q` after the change as a regression sanity check anyway (not because a doc change should affect tests, but to catch anything unexpected): 366 passed, unchanged from before this story.
- Self-review (Task 4): cross-checked the new Confluence-only setup step and Daily-use section word-for-word against `story-kickoff/SKILL.md`'s step 4b. Caught and corrected one real drafting error before finalizing: the first draft implied the script-fallback env vars were a simple opt-in for better auto-fill regardless of MCP state; SKILL.md is explicit that the fallback only activates when Confluence MCP tools aren't available in the session at all, and MCP is always preferred when available — corrected the wording to state this precisely (Task 1, Subtask 1.3).
- Also caught a stale forward-reference during self-review: the Confluence flow's `/opsx:propose` step originally said "same reasoning as the JIRA flow below," but the JIRA flow section sits *above* Confluence in the file — fixed to "above."

### Completion Notes List

- Task 1: Prerequisites table row 5 now covers JIRA and Confluence together, noting the shared MCP connection and that auto-fill completeness differs. "JIRA setup" renamed to "JIRA / Confluence setup"; the two original steps (connect, authenticate) are unchanged and now explicitly framed as shared; a "JIRA only" label was added to the existing custom-field-override step; a new "Confluence only" step explains the MCP page-label gap and the script-fallback's precise activation condition.
- Task 2: new "Daily use — Confluence flow" section, same 10-step structure and completeness as the JIRA flow (branch, kickoff via full page URL, optional openspec propose/apply, work, commit/push, close, check snapshot, optional report/dashboard), plus a closing paragraph generalizing the `/opsx:propose`-after-kickoff rationale to "no Atlassian-fetching capability of any kind," not JIRA-specific wording copied verbatim.
- Task 3: added a new "Known limitations" entry stating the Confluence points/sprint MCP gap in the same honest-tradeoff voice as the file's existing `token_cost`/duration entries. Fixed two now-stale cross-references: "Data use and privacy"'s "see 'JIRA setup' above" → "JIRA / Confluence setup"; Troubleshooting's "JIRA MCP server"/"JIRA MCP tools" wording → "Atlassian MCP server"/"JIRA/Confluence MCP tools" (same root cause and fix apply to both backends).
- Task 4: self-review found and fixed the two real drafting issues noted in Debug Log above before finalizing. Full test suite re-run as a sanity check, unaffected (366 passed).
- No code changes, no new dependencies, no architecture deviations.

### File List

- tools/build-release/INSTALL.md (modified — Prerequisites row broadened; "JIRA setup" renamed and extended with a Confluence subsection; new "Daily use — Confluence flow" section; new Known Limitations entry; two stale cross-references fixed)
- _bmad-output/implementation-artifacts/1-10-installmd-documents-the-confluence-flow.md (this file — task checkboxes, Dev Agent Record, status)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — story status transitions)
- _bmad-output/planning-artifacts/epics.md (modified — pilot-testing finding logged, Story 1.10 formalized)
