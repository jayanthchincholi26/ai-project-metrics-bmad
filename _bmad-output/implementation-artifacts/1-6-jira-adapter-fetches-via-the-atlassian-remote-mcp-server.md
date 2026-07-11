---
baseline_commit: ea2f6a6f293855659e9d0329b633c3cc44bdd746
---

# Story 1.6: JIRA Adapter Fetches via the Atlassian Remote MCP Server

Status: done

> **Backfilled record (2026-07-11).** This story was designed and implemented directly in a
> working session (smoke-test → empirical MCP verification → implementation → PR #19) without
> the create-story/dev-story workflow; this file was written after the merge so the
> implementation-artifacts trail stays complete. Full decision/verification log lives in
> `epics.md` (Story 1.6) and [PR #19](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/19).

## Story

As a developer on a JIRA-backed project,
I want kickoff to fetch my story's points/goal/sprint through the team's already-configured JIRA connection,
So that I don't need a personal `JIRA_API_TOKEN` just to run kickoff.

## Acceptance Criteria

1. **Given** `source_of_truth: jira` and a JIRA MCP server configured for the session
   **When** the developer enters a JIRA issue key at kickoff
   **Then** the story-kickoff skill fetches via the MCP tools directly — no `JIRA_*` env vars read or required
   **And** fields normalize to the same `{points, goal, sprint, description}` shape as Story 1.3
   **And** points confirmation stays human (CAP-1); null fields are elicited, never invented
   **And** no MCP server → plain fallback message, then the Story 1.3 token script only if all three `JIRA_*` env vars are set, else the plain ask — kickoff never blocks (FR5)
   **And** NFR4 holds structurally: auth lives in the MCP server's OAuth session; the skill never sees a credential

## What Was Done

- Rewrote `.claude/skills/story-kickoff/SKILL.md` step 4a to the MCP flow: two-call sequence
  (`getAccessibleAtlassianResources` → `cloudId`, resolved once per kickoff → `getJiraIssue`
  with config-driven field IDs, defaults `customfield_10016`/`customfield_10020`), Story 1.3's
  normalization rules restated as skill prose, and the FR5 degradation chain.
- Strengthened the skill's Boundaries section: credentials never appear anywhere; on the MCP
  path this is structural, not procedural.
- Added `docs/testing/story-1.6-e2e.md` — the four-scenario manual E2E script (skill-flow
  story; pytest can't reach conversational steps, so E2E is the primary verification).
- `tools/adapters/jira/main.py` deliberately unchanged — it remains the fallback.

## Dev Notes

- **Empirical verification preceded implementation** (all against
  `my-sg-custom-dashboard.atlassian.net`, 2026-07-11): OAuth via `claude mcp add --transport
  http atlassian https://mcp.atlassian.com/v1/mcp/authv2` + `/mcp` worked first try; the MCP
  layer returns the full raw REST v3 issue object (custom fields intact); `customfield_10016`
  returned `null` unset and `5` after being set; `customfield_10020` returned the full
  sprint-object list handled by the existing active-wins-else-last rule.
- **Server-agnostic by design**: the skill targets whichever JIRA MCP server the session has;
  official Atlassian remote is the recommended default. The community `mcp-atlassian` server
  registers zero tools without env credentials (observed live) — which server a project uses
  is a deployment/prerequisites choice, not skill logic.
- **Review note**: 4th consecutive PR where the external LLM review misattributed findings
  (credited base-branch commits and an untouched `APPROACH.md` to this PR). Grep-verify held:
  actual diff was 2 files, review's substantive verdict on those was positive, zero defects.
- E2E scenario A verified live pre-merge; B/C/D pending (tracked in the E2E script's results
  table).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.6] — full empirical verification log
- [Source: _bmad-output/implementation-artifacts/1-3-jira-adapter-auto-fills-kickoff.md] — the superseded token-based adapter; its normalization rules carry over
- [Source: docs/testing/story-1.6-e2e.md] — four-scenario E2E script (DoD)
- [PR #19](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/19) — squash-merged to `enhancements`, 9eddf90
