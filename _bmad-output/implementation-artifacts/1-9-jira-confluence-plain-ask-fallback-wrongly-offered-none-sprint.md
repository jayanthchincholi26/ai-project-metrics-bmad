---
baseline_commit: d47d4e8
---

# Story 1.9: JIRA/Confluence Kickoff's Plain-Ask Fallback Wrongly Offered the Docs-Only "None" Sprint Option

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer whose JIRA/Confluence kickoff falls back to a plain manual ask (no MCP, no fetch),
I want the sprint question to require a real value, exactly as it always has for these backends,
so that the manifest writer doesn't reject the kickoff with `--sprint must not be empty`.

## Background

Found live during Story 1.8's own real-session verification (2026-07-15): a Confluence kickoff with no MCP auth and no env credentials correctly degraded to a plain manual ask (per FR5) — but the assistant offered the docs-only-specific "None — this project doesn't track sprints/milestones" option (step 4.4) for a **Confluence**-sourced story, then tried to write the manifest with `--sprint` omitted. `tools/adapters/docs-only/main.py` correctly rejected it (`error: --sprint must not be empty`), since sprint has always been required for JIRA/Confluence, never `null` — only docs-only gets the "none" exception (Story 1.7).

Root cause: `SKILL.md`'s step 4 header already states this rule ("This step is docs-only-specific ... The JIRA/Confluence variants (4a/4b) are unaffected ... sprint stays required exactly as before"), but 4a's and 4b's own "fall back to the plain step-4 ask" phrasing never repeated that override at the point where it actually matters operationally — an easy thing to lose track of when literally reusing step 4.4's UI. This is a pre-existing ambiguity (4a's fallback text has read this way since Story 1.6), not something Story 1.8 introduced — it just happened to get live-caught for the first time during 1.8's own Confluence testing.

## Acceptance Criteria

1. **Given** JIRA kickoff (4a) falls back to the plain step-4 ask (no MCP, no env credentials)
   **When** sprint is elicited
   **Then** it is asked as a confirmed, non-empty value — the docs-only "None" option is never offered, and a blank answer is re-prompted
2. **Given** Confluence kickoff (4b) falls back to the plain step-4 ask, either via the MCP path itself (points/sprint always null there) or via the no-MCP-tools branch
   **When** sprint is elicited
   **Then** same rule as AC 1 — confirmed non-empty value, never "None", re-prompt on blank
3. **Given** docs-only kickoff
   **When** sprint is elicited
   **Then** completely unchanged — "None" remains a valid, complete answer (Story 1.7)

## Tasks / Subtasks

- [x] Task 1: fix 4a's fallback wording (AC 1)
  - [x] Subtask 1.1: explicit inline reminder that sprint stays required even on the no-MCP/no-credentials fallback path, asked as plain free text (not `AskUserQuestion`'s docs-only "None" option)
- [x] Task 2: fix 4b's wording at both points where it matters (AC 2)
  - [x] Subtask 2.1: the primary MCP-path text (points/sprint always null there) — same explicit reminder
  - [x] Subtask 2.2: the no-MCP-tools fallback branch — same explicit reminder
- [x] Task 3: verify
  - [x] Subtask 3.1: full suite unaffected (skill-instruction-only change), 337 passed
  - [ ] Subtask 3.2: **live verification pending** — needs a real re-run of the fallback path (JIRA or Confluence, no MCP/no credentials) confirming the sprint question is now asked as a plain required value, not offered "None"

## Dev Notes

### Scope

Documentation/skill-instruction change only, same category as Story 1.8 — no new Python code, no pytest surface. `tools/adapters/docs-only/main.py`'s own `--sprint must not be empty` validation is correct and untouched; the bug was entirely in the skill's own guidance text being ambiguous about the rule it had already stated elsewhere.

### Why this wasn't caught by Story 1.6's own testing

Story 1.6's JIRA-MCP verification (2026-07-11) tested the no-MCP-fallback path and noted "a fallback (no-MCP) AskUserQuestion call threw a one-off InputValidationError then silently retried and succeeded" — but didn't specifically flag this sprint-option issue at the time, plausibly because that particular test run didn't happen to hit a blank/None sprint answer. This is the first time it's been concretely observed causing a real write failure.

### Source tree touched

```text
.claude/skills/story-kickoff/SKILL.md    UPDATE  explicit sprint-required reminders at 3 fallback points (4a's one, 4b's two)
```

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5

### Debug Log References

Full suite: 337 passed (unaffected, as expected). Root-caused live via the user's own real Confluence kickoff test session hitting the actual `docs-only/main.py` rejection.

### Completion Notes List

- Same "not fully closed without a live re-test" discipline as Stories 5.8/1.8 — Subtask 3.2 is the real proof this wording fix actually changes live behavior, not just reads better.

### File List

.claude/skills/story-kickoff/SKILL.md (updated)
