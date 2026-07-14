---
baseline_commit: 5724b11
---

# Story 5.1: INSTALL.md — Numbered Steps, No Prose

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer adopting this capture tooling in my own project,
I want INSTALL.md's daily-use instructions as a plain numbered step list per backend, instead of prose paragraphs mixed with a partial example,
so that I can follow along step-by-step exactly the way real pilot testing has actually been run, without re-deriving the sequence from surrounding explanation text.

## Acceptance Criteria

1. **Given** `tools/build-release/INSTALL.md`'s current "Daily use" section (prose-heavy, one partial openspec example embedded in paragraphs, docs-only/JIRA differences scattered across several call-out paragraphs)
   **When** this story is done
   **Then** "Daily use" is replaced by two clearly labeled, fully self-contained, sequentially numbered step lists — one for the **docs-only flow**, one for the **JIRA flow** — each covering the complete lifecycle from a fresh clone through closing the story and checking the snapshot

2. **Given** the two step lists
   **When** a step involves archiving/closing a story
   **Then** the exact command to run is stated explicitly and literally on its own step line (`uv run tools/opsx-wrapper/main.py archive <change-name>` for openspec projects, or `uv run tools/snapshot-assembler/main.py --repo-root .` without openspec) — never folded into a paragraph about what the step "produces"

3. **Given** the JIRA flow specifically
   **When** the step list reaches the point of connecting to JIRA
   **Then** it reflects the **corrected** real-world ordering discovered during 2026-07-13 pilot testing: `claude mcp add`/`/mcp` authentication happens **before** kickoff, and (if the project uses openspec) `/opsx:propose` happens **after** kickoff for JIRA specifically — never before, since `/opsx:propose` has no JIRA-fetching capability of its own and will fail or fall back to unauthenticated `WebFetch` if given a ticket URL before kickoff has run

4. **Given** the existing content in Prerequisites, JIRA setup, the `.gitignore` auto-enforcement note, Updating, and Troubleshooting
   **When** this story is done
   **Then** none of that substantive information is lost or silently dropped — it may be condensed/reordered for concision, but every fact, gotcha, and command currently documented stays documented somewhere in the file

5. **Given** this is a pure documentation change
   **When** Definition of Done is evaluated
   **Then** there is no pytest surface (nothing in `tools/` or `tests/` changes) — the check is a careful self-review re-read of the finished file against the two real command sequences actually validated live during 2026-07-12/13 testing (Dev Notes below), not an automated test

## Tasks / Subtasks

- [x] Task 1: Rewrite the docs-only step list (AC: 1, 2, 4)
  - [x] Subtask 1.1: Draft the complete docs-only sequence as plain numbered steps, from fresh clone through closing the story, using the real corrected sequence validated 2026-07-12/13 (Dev Notes below) as the source of truth — not the current file's partial example
  - [x] Subtask 1.2: Explicitly include the openspec-optional branching (steps that only apply "if your project uses openspec SDD") without turning it back into prose — a short inline note per step is fine, a paragraph explaining the whole branch is not
  - [x] Subtask 1.3: State the archive/snapshot command explicitly on its own line (AC 2)

- [x] Task 2: Rewrite the JIRA step list (AC: 1, 2, 3, 4)
  - [x] Subtask 2.1: Draft the complete JIRA sequence as plain numbered steps, correctly ordering MCP setup before kickoff and `/opsx:propose` after kickoff (AC 3) — this is the one place the current file's guidance is actually wrong/misleading if copied verbatim into a JIRA context (the openspec example in "Daily use" today implies propose-before-kickoff universally, which only holds for docs-only)
  - [x] Subtask 2.2: Include the field-override note (`jira_points_field`/`jira_sprint_field`) at the right point in the sequence (`.story-config.yaml` step), not as a disconnected callout
  - [x] Subtask 2.3: State the archive/snapshot command explicitly on its own line (AC 2)

- [x] Task 3: Preserve and condense surrounding sections (AC: 4)
  - [x] Subtask 3.1: Re-read Prerequisites, JIRA setup, the `.gitignore` note, Updating, and Troubleshooting; confirm every fact/command from the current file has a home in the rewritten file (a checklist diff against the current file's content, not just a vibe check)
  - [x] Subtask 3.2: Condense any remaining prose paragraphs elsewhere in the file into short bullets/numbered notes where that improves scannability, without cutting substantive content

- [x] Task 4: Self-review pass (AC: 5)
  - [x] Subtask 4.1: Read the finished file end to end as if seeing it for the first time; confirm each step list, followed literally in order, matches a real command sequence that was actually run and validated during 2026-07-12/13 testing (cross-check against Dev Notes below and, if needed, the session history) — no invented or unverified steps

## Dev Notes

### Scope — what this story is and is not

- Pure documentation change to `tools/build-release/INSTALL.md`. No code in `tools/`, no new script, no manifest/schema change.
- **Do NOT invent new steps or a new install mechanism** — this story only reorganizes and corrects the presentation of exactly what already exists and was already validated live. If something in the current file's content turns out to be wrong (see the JIRA-ordering correction, AC 3), fix the wording, but don't design new behavior.
- **Do NOT include the "close VS Code entirely + run from a plain terminal" discipline as a normal daily-use step.** That was a diagnostic technique used specifically to get a clean `ai_sessions`/`sessions_observed` measurement during a controlled test (2026-07-13) — it is not something a developer needs to do for ordinary story work, and including it here would misrepresent it as a required step.

### The real, corrected sequences to use as source of truth (validated live, 2026-07-13)

**Docs-only** (validated end-to-end: kickoff → `/opsx:propose`/`/opsx:apply` → commit/push → archive → snapshot, all in one continuous session):
1. Clone (or `git init`) an empty repo.
2. Download the release zip, extract at the repo root.
3. Confirm `git --version` / `uv --version`.
4. *(openspec projects only)* `npm install -g @fission-ai/openspec@latest`, then `openspec init`.
5. `git checkout -b story/<branch-name>`.
6. Create `.story-config.yaml`:
   ```yaml
   source_of_truth: docs-only   # default when absent
   ai_tool: claude-code         # default when absent
   ```
7. `uv run tools/setup-hooks.py --repo-root .`
8. *(openspec projects only, do this before kickoff)* `/opsx:propose <change-name>` — a developer-chosen kebab-case name, never the story ID. Doing this before kickoff gives the Phase-1 estimator a real `tasks.md` to read.
9. In chat: *"kick off this story"* — answer the prompts (story name, points, goal, milestone/sprint — say "none" if not tracked).
10. Work normally — commits, checkouts, AI sessions capture silently in the background.
11. *(openspec projects only)* `/opsx:apply`.
12. Commit and push your work.
13. Close the story: `uv run tools/opsx-wrapper/main.py archive <change-name>` (one command — archives the openspec change *and* produces the snapshot), or without openspec: `uv run tools/snapshot-assembler/main.py --repo-root .`.
14. Check `snapshots/<story-id>.v1.rev1.json`.

**JIRA** (validated end-to-end, with the propose/kickoff ordering **correction** discovered 2026-07-13 — see the "why this order" note below):
1. Clone (or `git init`) an empty repo.
2. Download the release zip, extract at the repo root.
3. Confirm `git --version` / `uv --version`.
4. *(openspec projects only)* `npm install -g @fission-ai/openspec@latest`, then `openspec init`.
5. `git checkout -b story/<branch-name>`.
6. Create `.story-config.yaml`:
   ```yaml
   source_of_truth: jira
   ai_tool: claude-code
   # only if your JIRA site's custom fields differ from the defaults:
   # jira_points_field: customfield_10016
   # jira_sprint_field: customfield_10020
   ```
7. Connect the Atlassian MCP server (once per machine **and** per project path — `claude mcp add` is local-scope): `claude mcp add --transport http atlassian https://mcp.atlassian.com/v1/mcp/authv2`, then `/mcp` in the same chat session to complete OAuth.
8. `uv run tools/setup-hooks.py --repo-root .`
9. In chat: *"kick off this story \<issue-key\>"* — kickoff fetches points/goal/sprint automatically via the now-connected MCP tools; confirm or override the values.
10. *(openspec projects only, do this AFTER kickoff for JIRA — see note below)* `/opsx:propose <change-name>`.
11. *(openspec projects only)* `/opsx:apply`.
12. Work normally, commit and push.
13. Close the story: `uv run tools/opsx-wrapper/main.py archive <change-name>`, or without openspec: `uv run tools/snapshot-assembler/main.py --repo-root .`.
14. Check the resulting snapshot.

**Why JIRA's propose/kickoff order differs from docs-only's (a real correction found in this round of testing, not a stylistic choice):** `/opsx:propose` has no JIRA-fetching capability at all — it only accepts a kebab-case name or a plain-text description you type. Passing it a JIRA URL/ticket reference before kickoff has run will either fail or silently fall back to unauthenticated `WebFetch` (which can't reach an authenticated Atlassian page), producing a proposal built on nothing. The Atlassian MCP fetch only exists inside the `story-kickoff` skill itself (step 4a). So for JIRA, kickoff must run first to get the real ticket content; `/opsx:propose` afterward can then use that real content (typed or pasted) instead of a bare URL it can't resolve. This means, for JIRA, Phase-1's estimate will still be null at kickoff time (no `tasks.md` exists yet) — that's expected, not a bug, and different from docs-only where propose-before-kickoff is possible and gives a real Phase-1 number.

### Architecture compliance (binding invariants)

- No AD/architecture invariant is touched by this story — it's presentation-only. The commands themselves (`setup-hooks.py`, `story-kickoff`, `opsx-wrapper`, `snapshot-assembler`) are unchanged; only how they're documented changes.
- `project-context.md` §12 (Story DoD) still applies for what counts as "done" here, minus the automated-test bullet (N/A for a docs-only change, same precedent as Story 2.10).

### Testing standards (project-context.md §5/§6)

- No pytest surface, same precedent as Story 2.10 (a skill-instruction-only change). Definition of Done is the self-review re-read specified in AC 5/Task 4, not an automated suite.

### Source tree touched

```text
tools/build-release/INSTALL.md   UPDATE   "Daily use" section replaced with two step lists; surrounding sections condensed, nothing dropped
```

No files under `tools/` (code) or `tests/` are touched.

### Project Structure Notes

No conflicts — this is the same file Stories 1.6, 1.7, 2.7, and 2.11 have each incrementally updated before.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.1] — the ask and its rationale
- [Source: tools/build-release/INSTALL.md] — the file being rewritten; current content is the baseline for the "nothing lost" check (AC 4)
- [Source: project_pm_metrics_pipeline.md memory, 2026-07-12/13 entries] — the actual validated command sequences and the JIRA propose/kickoff ordering correction this story's content is built from
- [Source: project-context.md] — §12 Story DoD (docs-only precedent, no automated-test bullet)

## Dev Agent Record

### Agent Model Used

claude-sonnet-5 (create-story context engineering + dev-story implementation)

### Debug Log References

- No pytest surface for this story (pure documentation change, per Dev Notes) — Definition of Done is the self-review re-read specified in AC 5/Task 4.
- Self-review (Task 4): read the finished file end to end, cross-checked both step lists against the real command sequences validated live 2026-07-12/13 (docs-only: kickoff → propose/apply → commit/push → archive → snapshot; JIRA: MCP connect → kickoff → propose/apply → commit/push → archive → snapshot). Found one real gap on first pass — the old file's general "step order matters for the point estimate, not correctness" reassurance had been dropped in favor of the more specific JIRA-only explanation — restored it under the docs-only section (AC 4).
- Completeness check (Task 3, Subtask 3.1): diffed the rewritten file against the pre-story version fact-by-fact (Prerequisites table, Install steps, JIRA setup mechanics, `.gitignore` auto-enforcement + warning text, Updating, Troubleshooting) — every fact/command from the original has a home in the rewritten file.

### Completion Notes List

- Task 1/2: "Daily use" replaced with two independent, fully self-contained numbered step lists (docs-only, JIRA), each covering fresh-clone-to-snapshot. The archive/snapshot command is stated literally on its own step line in both (AC 2), never folded into descriptive prose.
- Task 2 specifically corrects a real ordering mistake that would otherwise have propagated into install docs: JIRA's flow puts `/opsx:propose` **after** kickoff (with an explanation of why — `/opsx:propose` has no JIRA-fetch capability and will hit `WebFetch`/fail if given a ticket URL before kickoff has run), while docs-only's flow keeps `/opsx:propose` **before** kickoff (for a real Phase-1 estimate) — these are genuinely different, not a copy-paste of the same note.
- Task 3: Prerequisites, JIRA setup, `.gitignore` auto-enforcement, Updating, and Troubleshooting sections preserved with all facts intact; JIRA setup reformatted into numbered steps for consistency with the rest of the file.
- Task 4: self-review caught and fixed the one gap noted above before finalizing.
- No code changes, no new dependencies, no architecture deviations.

### File List

- tools/build-release/INSTALL.md (rewritten — "Daily use" split into two step lists; surrounding sections condensed/reformatted, no content lost)
- _bmad-output/implementation-artifacts/5-1-installmd-numbered-steps-no-prose.md (this file — task checkboxes, Dev Agent Record, status)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — story status transitions)
