---
baseline_commit: c2d7476
---

# Story 1.8: Confluence Adapter Fetches via the Atlassian Remote MCP Server

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer whose project's `source_of_truth` is Confluence,
I want kickoff to fetch the page via the same Atlassian MCP server JIRA already uses,
so that I don't need a personal Confluence API token just to run a kickoff.

## Background

Found live during Confluence pilot testing (2026-07-15): the user pointed out that `story-kickoff/SKILL.md`'s Confluence variant (step 4b) never got the MCP upgrade Story 1.6 gave the JIRA variant — it still only documented the script-based fetch (`tools/adapters/confluence/main.py`, requiring `CONFLUENCE_BASE_URL`/`CONFLUENCE_EMAIL`/`CONFLUENCE_API_TOKEN`, a personal token), the exact pattern Story 1.6 moved JIRA away from.

Researched the actual Atlassian Remote MCP Server's capabilities before implementing (not assumed): it does expose Confluence tools (`getConfluencePage` and related), confirmed live in the user's own test session fetching a real page. But it has a real, currently-open platform gap — **it exposes no Confluence page-label read capability at all** (confirmed via an open, unanswered GitHub issue on Atlassian's own MCP server repo). This project's points/sprint auto-fill for Confluence has always worked by reading page labels (`points-<number>`, `sprint-<name>`) — a capability only the script-based fallback (real Confluence REST API, personal token) can still provide.

Also found: the MCP server cannot resolve Confluence short-links (`/wiki/x/...`) to a numeric page ID either (confirmed via a separate open GitHub issue) — the user's own live assistant worked around this by fetching/resolving the short-link itself, but that's not a documented, reliable capability of the tool.

## Acceptance Criteria

1. **Given** the connected Atlassian MCP server exposes Confluence tools
   **When** a developer runs Confluence kickoff
   **Then** the page fetch goes through MCP (`getAccessibleAtlassianResources` → `getConfluencePage`) by default, no personal Confluence API token needed — mirroring 4a's JIRA-via-MCP precedent
2. **Given** the developer provides a Confluence page reference
   **When** kickoff asks for it
   **Then** it asks for the **full page URL** (not a short link) and parses the numeric page ID out of it itself — the developer never has to manually extract a bare content ID
3. **Given** the MCP server cannot read Confluence page labels (a confirmed platform gap)
   **When** a Confluence page is fetched via MCP
   **Then** points/sprint always fall back to a plain manual ask, with an explicit, honest one-time explanation of why (not a silent degradation) — and the developer is told the script fallback (with real credentials) is the only path that still gets real label-based auto-fill
4. **Given** no Confluence MCP tools are available in the session
   **When** kickoff runs
   **Then** it falls back to the Story 1.4 script exactly as before (env-var credentials, real label reading) if configured, else a plain unassisted ask — kickoff is never blocked (FR5)

## Tasks / Subtasks

- [x] Task 1: research the real MCP capability before implementing (AC 1, 3, 4)
  - [x] Subtask 1.1: confirmed `getConfluencePage`/related tools exist, gated by `cloudId` + numeric page ID, live in the user's own test session
  - [x] Subtask 1.2: confirmed labels are NOT exposed by the MCP server (open GitHub issue, no maintainer response) — this shapes AC 3's honest-degradation requirement
  - [x] Subtask 1.3: confirmed short-link resolution is NOT supported by the MCP server either (separate open GitHub issue) — shapes AC 2's "ask for the full URL" requirement
- [x] Task 2: rewrite `story-kickoff/SKILL.md` step 4b (AC 1, 2, 3, 4)
  - [x] Subtask 2.1: MCP-first fetch, mirroring 4a's structure (resolve `cloudId` once, reuse across JIRA/Confluence calls in the same kickoff)
  - [x] Subtask 2.2: ask for the full page URL, parse the numeric ID from the `/pages/<ID>/` segment
  - [x] Subtask 2.3: points/sprint always null via the MCP path, with the explicit one-time explanation text
  - [x] Subtask 2.4: degradation chain preserved — script fallback (real label reading) → plain ask, kickoff never blocked
- [x] Task 3: verify
  - [ ] Subtask 3.1: **live verification pending** — this is a skill-instruction-only change with no pytest surface (same precedent as Stories 1.6/2.10); needs a real kickoff run in the user's live session against a real Confluence page (ideally one with `points-`/`sprint-` labels, to confirm the MCP path correctly nulls them out and the honest explanation is given) before considered fully done

## Dev Notes

### Scope

Documentation/skill-instruction change only — no new Python code, no new tests (this project's established precedent: skill-only changes with no pytest surface get verified via real live skill invocations, not unit tests — see Stories 1.6/2.10's own Dev Notes). `tools/adapters/confluence/main.py` (the script fallback) is untouched; it still works exactly as before for teams that configure real credentials.

### Why this differs from Story 1.6's JIRA upgrade

Story 1.6 was a clean win: MCP fully replaced the personal-token JIRA fetch, no functional loss. This story is **not** a clean win — the MCP path genuinely can't do everything the script path could (labels), so the honest design keeps both paths alive with a clear tradeoff communicated to the developer, rather than pretending MCP is a strict improvement. AD-4/CAP-1 (points confirmation stays human, null-with-reason never fabricated) already covers this gracefully — an MCP-fetched page's points/sprint just always take the same path an unlabeled page already took.

### Source tree touched

```text
.claude/skills/story-kickoff/SKILL.md    UPDATE  step 4b rewritten (MCP-first, full-URL input, honest labels caveat)
```

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5

### Debug Log References

Research: confirmed via a general-purpose research agent against Atlassian's own MCP server repo/docs and two relevant open GitHub issues (labels, short-link resolution). Live: the user's own assistant, in a separate live Claude Code session, successfully fetched a real Confluence page ("Fibonacci Series", page ID 22020097) via `getConfluencePage` — confirming the MCP fetch path itself works for real, even before this story's skill-instruction update landed.

### Completion Notes List

- This story is functionally complete but **not fully closed** — Subtask 3.1 (a real live kickoff run using the updated skill instructions) is the actual proof, same "verify live before declaring done" discipline as Story 5.8's Subtask 5.3.
- The labels gap is a genuine Atlassian platform limitation (open, unanswered upstream issue), not something this project can work around cleanly — documented honestly rather than silently degraded.

### File List

.claude/skills/story-kickoff/SKILL.md (updated)
