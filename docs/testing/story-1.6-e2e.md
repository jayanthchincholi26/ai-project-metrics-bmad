# Story 1.6 E2E — JIRA Kickoff via MCP

Manual end-to-end verification for the MCP-based JIRA kickoff (skill-flow change; pytest
cannot reach conversational steps — this script is the primary verification per the story's
testing strategy). Prereqs: the Atlassian Remote MCP Server added and OAuth-authenticated
(`claude mcp add --transport http atlassian https://mcp.atlassian.com/v1/mcp/authv2`, then
`/mcp` → authenticate), and a test JIRA site with at least one Story-type issue.

Setup in the test repo before each scenario: `.story-config.yaml` containing
`source_of_truth: jira`, and **no** `.story.yaml` at the repo root (delete between runs —
each kickoff must start clean).

## Scenario A — happy path (points set on the issue)

1. Ensure the target issue (e.g. `AI-53`) has Story Points set (e.g. 5) and belongs to a sprint.
2. Say: "kick off this story". Enter the issue key when asked.
3. **Pass when:** the skill resolves jira without asking which backend; calls
   `getAccessibleAtlassianResources` once, then `getJiraIssue`; presents points/goal/sprint
   fetched from the issue (points=5, goal=issue summary, sprint per active-wins-else-last);
   asks you to confirm points (human confirmation, even though JIRA supplied a number);
   writes `.story.yaml` with `source_of_truth: "jira"` and the confirmed values.
4. Verify: `Get-Content .story.yaml` — no credential-like content anywhere in it.

> First verified 2026-07-11 against `my-sg-custom-dashboard.atlassian.net` / AI-53
> (`customfield_10016: 5`, sprint list closed-19 + future-20 → "AI Sprint 20").

## Scenario B — issue key not found

1. Kick off and enter a nonexistent key (e.g. `AI-99999`).
2. **Pass when:** the skill reports what the MCP tool returned (not-found), re-asks for the
   key, and never writes a manifest with invented values. Entering a valid key afterwards
   continues normally.

## Scenario C — no JIRA MCP server connected

1. Disable/remove the atlassian MCP server for the session (`claude mcp remove atlassian`
   or run in a window without it), keep `source_of_truth: jira`, and ensure
   `JIRA_BASE_URL`/`JIRA_EMAIL`/`JIRA_API_TOKEN` are **not** set.
2. Kick off.
3. **Pass when:** the skill says plainly that no JIRA MCP server is connected, does **not**
   ask for a token in chat, falls back to the plain three-field ask, and completes the
   kickoff (FR5 — never blocked). Manifest still records `source_of_truth: "jira"`.
4. Variant C2 (fallback script): same, but with the three `JIRA_*` env vars set — pass when
   it uses `tools/adapters/jira/main.py` and behaves like the Story 1.3 flow.

## Scenario D — points absent on the issue

1. Use an issue with **no** Story Points set.
2. Kick off with its key.
3. **Pass when:** points come back null, the skill elicits points via the re-prompt rule
   (offering the Phase-1 estimate as a suggestion if one exists), and never writes a manifest
   missing points. `points_estimated` stays distinct per AD-6a.

> Field visibility for this scenario was verified 2026-07-11: the same issue returned
> `customfield_10016: null` before points were set and `5` after.

## Results

| Scenario | Date | Result | Notes |
|---|---|---|---|
| A | | | |
| B | | | |
| C / C2 | | | |
| D | | | |
