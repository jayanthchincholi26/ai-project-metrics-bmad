---
stepsCompleted: [step-01, step-02, step-03, step-04]
inputDocuments: ['_bmad-output/specs/spec-pm-metrics-ai-engineering-flow/SPEC.md', '_bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md']
---

# explore-jira-ai-metrics - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for explore-jira-ai-metrics, decomposing the requirements from SPEC.md (capabilities/constraints in place of a PRD; no UX design contract exists for this project) and ARCHITECTURE-SPINE.md into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1 (CAP-1): A story's PM, engineering, story-point-cost, and token-cost metrics are captured automatically as a byproduct of the dev flow, without the developer re-reporting status or effort.
FR2 (CAP-2): A story's points are estimated automatically at kickoff and reconciled against actuals at close, using defined rules (AD-6), with variance logged rather than overwritten.
FR3 (CAP-3): The system attributes active working time to the correct story as a developer moves between stories, without a manual time-log entry.
FR4 (CAP-4): The kickoff flow adapts its questions and data source to whatever project-management tool (or lack of one) a given project actually uses.
FR5 (CAP-5): The full metrics-capture pipeline runs uniformly for stories of every complexity; complexity classification at kickoff feeds only the Phase-1 point estimate, never a capture on/off decision (removes the under-classification loophole).
FR6 (CAP-6): Per-story snapshots are producible in a stable, versioned shape that a future central presentation layer can consume without needing raw capture-side event detail.
FR7 (CAP-7): The capture side supports a normalized AI-tool adapter interface so tools other than Claude Code can be added later without redesigning event integrity or the reconciliation formula; only the Claude Code adapter is implemented now.

### NonFunctional Requirements

NFR1: No modification of openspec/speckit internals; all interception is external (CLI wrapping, git hooks, Claude Code hooks) since no plugin/extension API exists.
NFR2: Capture must work fully offline / local-first — no producer depends on network availability or a running background service (AD-2).
NFR3: Only a versioned snapshot ever crosses the local-to-central boundary; the raw event log never leaves the developer's machine (AD-3, AD-3a).
NFR4: Adapter credentials (JIRA/Confluence tokens) must never be written into `.story.yaml`, the event log, or any snapshot (AD-4).
NFR5: Branch-per-story is assumed as a hard team convention for time attribution; no per-story time tracking is defined if violated (AD-7, confirmed).

### Additional Requirements

- Event-sourced convergence: no producer writes `.story.yaml` or a snapshot directly; every producer only appends an event, via a single atomic append syscall (AD-1).
- Event `type` values are namespaced per source (`git.*`, `claude.*`, `opsx.*`) so no two producers can collide on a bare type name (AD-1a).
- Events arriving before `.story.yaml` exists are buffered, never dropped, and backfilled with the story ID once the manifest is written (AD-1b).
- Snapshot envelope has a fixed top-level shape (`schema_version, story_id, revision, pm_metrics, engineering_metrics, story_point_cost, token_cost`); every `opsx archive` produces a new immutable revision, never an overwrite (AD-3a).
- Source-of-truth adapter interface returns `{points, goal, sprint, description}` regardless of backend; a project-level config declares `source_of_truth` once (AD-4).
- `.story.yaml` (written by the kickoff skill) is the sole source of story identity; no producer infers it from branch name or ticket key (AD-5).
- Active-story time pointer (`.active-story`) auto-updates on `git checkout` and Claude Code `SessionStart`; a live session's `SessionStart`/`SessionEnd` boundaries take precedence over a mid-session checkout for time-slice accounting (AD-7).
- Hook installation is git-versioned: hook scripts live in a tracked `tools/hooks/` directory, installed by a single committed setup script into `.git/hooks/` and `.claude/settings.json` — never hand-maintained per machine (AD-8).
- Deployment: capture side runs entirely on the developer machine, no server/network dependency; central presentation layer's hosting/tech is explicitly out of scope for this breakdown (Deferred, spine).
- Implementation language/runtime: Python 3.8+ via `uv run` (single-file scripts, no venv management) for all hook logic, the opsx CLI wrapper, and the snapshot assembler — ratifies the existing convention used by `_bmad/scripts/*.py` in this repo. Git-invoked hooks are thin shell/batch shims that call the Python script via `uv run` (git requires a directly executable file, not a bare `.py`).
- A hook that fails to append an event retries up to 3 times, then surfaces a visible error to the developer; never fails silently (AD-9).
- Event namespace generalizes to `ai.<tool>.*` (not just `claude.*`); a signal an AI tool can't report (e.g. token cost) is emitted null-with-reason, never defaulted to zero; the kickoff manifest carries an `ai_tool` field declared like `source_of_truth` (AD-10).

### UX Design Requirements

No UX design contract exists for this project; this section is not applicable.

### FR Coverage Map

| Requirement | Epic |
| --- | --- |
| FR1 (CAP-1) | Epic 2, Epic 3 |
| FR2 (CAP-2) | Epic 2 (Stories 2.5, 2.6) |
| FR3 (CAP-3) | Epic 3 |
| FR4 (CAP-4) | Epic 1 |
| FR5 (CAP-5) | Epic 1 |
| FR6 (CAP-6) | Epic 2 |
| FR7 (CAP-7) | Epic 1 (manifest field), Epic 2 (capture) |
| NFR1 | Epic 2 |
| NFR2 | Epic 2 |
| NFR3 | Epic 2 |
| NFR4 | Epic 1 |
| NFR5 | Epic 3 |

*(Updated 2026-07-10: this table originally referenced "Epic 4"/"Epic 5" from an earlier planning draft; the actual build folded FR2 and FR3 into Epics 2 and 3 respectively — those Epic 4/5 references were stale and have been superseded. Epics 1–3 cover the original SPEC capabilities (CAP-1..7) and are complete. Epic 4 below is a genuinely new addition, opened 2026-07-10 during pre-deploy smoke testing — it covers a distribution gap the original SPEC never addressed, not a resurrection of the old draft's Epic 4.)*

## Epic List

1. Epic 1: Start a Story With Zero Manual PM Setup
2. Epic 2: Metrics Appear Automatically When You Close a Story
3. Epic 3: Time Tracked Without Logging Hours
4. Epic 4: Package and Distribute the Capture Tooling to a Target Repo

### Epic 1: Start a Story With Zero Manual PM Setup
A developer can kick off a story without re-typing PM data, whatever tool (or lack of one) the project uses.
**FRs covered:** FR4, FR7 (manifest field only; capture side is Epic 2)
**Also covers:** AD-4, AD-5, AD-10 (manifest field), NFR4
**Held for later (not a story in this epic):** a GitLab source-of-truth adapter, alongside JIRA/Confluence/docs-only. Add only if real demand emerges.

### Epic 2: Metrics Appear Automatically When You Close a Story
A developer works normally and, on closing the story, a trustworthy metrics snapshot exists — no manual reporting, no placeholder numbers.
**FRs covered:** FR1, FR2, FR5, FR6, FR7 (capture side; manifest field is Epic 1 Story 1.5)
**Also covers:** AD-1, AD-1a, AD-1b, AD-2, AD-3, AD-3a, AD-6, AD-8, AD-9, AD-10, NFR1, NFR2, NFR3

### Epic 3: Time Tracked Without Logging Hours
Switching between stories never corrupts time attribution, and nobody manually starts or stops a timer.
**FRs covered:** FR3
**Also covers:** AD-7, NFR5

---

## Epic 1: Start a Story With Zero Manual PM Setup

A developer can kick off a story without re-typing PM data, whatever tool (or lack of one) the project uses.

> ✅ **Epic complete** — 2026-07-09, all 5 stories done (PRs #1, #4, #6, #8, #9).
>
> **Retro note (§13):** *What worked* — fetch-only adapters composed with one manifest writer kept NFR4 trivially provable; test-first + manual E2E caught what green suites missed (the UTF-8 BOM bug); external-LLM review found one real defect per early story, then zero by 1.5 as its lessons (URL encoding, format-over-membership validation, resilient parsing) got pre-applied; duration fell 60→13 min/story as patterns stabilized. *What to adjust* — squash-merge discipline slipped once (PR #1, merge commit); LLM review produced one hallucinated finding (nonexistent `import math`) — keep grep-verifying before acting; the duplicated flat-YAML parser (2 copies) is fine for now, but revisit at spine level if Epic 2's hooks need it too (Issue #7).
>
> 🔓 **Reopened 2026-07-10** — real-world pilot deployment surfaced that individual developers on an existing JIRA-backed project will not realistically have (or want to manage) a personal `JIRA_API_TOKEN`. Story 1.3's direct-REST-with-token adapter is superseded by **Story 1.6**, which fetches via the already-configured Atlassian Remote MCP Server instead. Story 1.3 is left below for history; do not delete it or its PR.

### Story 1.1: Create the Story Manifest via Docs-Only Kickoff

> ✅ **Complete** — 2026-07-09 · [PR #1](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/1) (merged to `develop`, 9ab68f8)

As a developer,
I want to kick off a story and have my points/goal/sprint captured into a manifest, even when my project has no PM tool,
So that every downstream capture mechanism has a story identity to attach to.

**Acceptance Criteria:**

**Given** a project with no source-of-truth tool configured
**When** the developer runs the kickoff skill
**Then** it prompts for story points confirmation, goal, and sprint, and writes them into `.story.yaml` with a generated `story_id`
**And** `.story.yaml` becomes the sole source other producers read the story ID from (AD-5)
**And** if the developer submits without providing points, goal, or sprint, the kickoff skill re-prompts for the missing field rather than writing an incomplete manifest

### Story 1.2: Project-Level Source-of-Truth Configuration

> ✅ **Complete** — 2026-07-09 · [PR #4](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/4)

As a developer,
I want my project to declare its PM tool once,
So that I'm never asked which tool applies on every single story.

**Acceptance Criteria:**

**Given** a project config declares `source_of_truth: jira | confluence | docs-only`
**When** the kickoff skill runs for any story in that project
**Then** it reads the declared value and behaves accordingly, without re-asking
**And** an unset config defaults to the docs-only behavior from Story 1.1

### Story 1.3: JIRA Adapter Auto-Fills Kickoff

> ⚠️ **Superseded by Story 1.6** (2026-07-10) — the token-based `urllib` fetch below still exists in `tools/adapters/jira/main.py` and works, but real-world pilot rollout means developers won't have a personal `JIRA_API_TOKEN` to put in their environment. Kept here for history; do not delete.
>
> ✅ **Complete** — 2026-07-09 · [PR #6](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/6)

As a developer on a JIRA-backed project,
I want my story's points/goal/sprint pulled automatically from a JIRA issue key,
So that I don't retype what JIRA already knows.

**Acceptance Criteria:**

**Given** `source_of_truth: jira` and a developer enters a JIRA issue key at kickoff
**When** the kickoff skill runs
**Then** it fetches `{points, goal, sprint, description}` from JIRA and populates `.story.yaml`
**And** the JIRA API credential is read from an environment variable / existing credential store at call time and never written into `.story.yaml`, the event log, or any snapshot (NFR4)

### Story 1.4: Confluence Adapter Auto-Fills Kickoff

> ✅ **Complete** — 2026-07-09 · [PR #8](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/8)

As a developer on a Confluence-backed project,
I want the same automatic fill as JIRA,
So that both PM tools are supported identically.

**Acceptance Criteria:**

**Given** `source_of_truth: confluence` and a developer enters a Confluence page reference at kickoff
**When** the kickoff skill runs
**Then** it fetches `{points, goal, sprint, description}` from Confluence and populates `.story.yaml` in the same normalized shape as the JIRA adapter
**And** the Confluence credential is likewise never persisted to any shared file (NFR4)

### Story 1.5: Kickoff Manifest Declares Which AI Tool Is In Use

> ✅ **Complete** — 2026-07-09 · [PR #9](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/9)

As a developer,
I want my project to declare which AI tool it uses,
So that the capture side knows which adapter to activate without asking me on every story.

**Acceptance Criteria:**

**Given** a project config declares `ai_tool: claude-code` (today's only implemented adapter; extensible per AD-10)
**When** the kickoff skill runs for any story in that project
**Then** it writes the `ai_tool` field into `.story.yaml` the same way Story 1.2 writes `source_of_truth` — declared once per project by default, or per-story only if a team genuinely mixes tools
**And** AI-session capture producers (Story 2.3) read this field to know which adapter's event namespace to emit under
**And** an unset `ai_tool` config defaults to `claude-code`

### Story 1.6: JIRA Adapter Fetches via the Atlassian Remote MCP Server

> ⏳ **Not started** — supersedes Story 1.3 (2026-07-10)

As a developer on a JIRA-backed project,
I want kickoff to fetch my story's points/goal/sprint through the team's already-configured JIRA connection,
So that I don't need a personal `JIRA_API_TOKEN` just to run kickoff — auth is handled the same way it already is for every other JIRA action I take as a developer.

**Context (why this replaces Story 1.3):** the original design assumed a developer would export `JIRA_BASE_URL` / `JIRA_EMAIL` / `JIRA_API_TOKEN` into their shell. In a real pilot rollout, developers joining an existing JIRA-backed project don't provision personal API tokens for one-off tooling — and shouldn't have to. The Atlassian Remote MCP Server (`https://mcp.atlassian.com/v1/mcp/authv2`) is the standard way Claude Code (and other AI tools) already connect to JIRA/Confluence/Bitbucket/Compass, authenticated via OAuth 2.1 under the developer's own existing access controls — no manual token. [Atlassian: Extend Atlassian into any AI assistant using MCP](https://www.atlassian.com/platform/remote-mcp-server); [GitHub: atlassian/atlassian-mcp-server](https://github.com/atlassian/atlassian-mcp-server); [Atlassian Support: Getting started with the Atlassian Remote MCP Server](https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/).

**Architecturally, this is not a subprocess adapter script** — an MCP tool is only callable by the agent itself (Claude Code) inside a live conversation, never by a standalone `uv run` script. So unlike Story 1.3's `tools/adapters/jira/main.py`, this story changes the **`story-kickoff` skill's step 4a** to call the MCP tool directly, then hand the already-fetched `{points, goal, sprint, description}` to the existing, unchanged manifest writer (`tools/adapters/docs-only/main.py --source-of-truth jira`). `tools/adapters/jira/main.py` (Story 1.3) is left in place, unused by the skill, as a fallback path for a project that genuinely has no MCP server configured — resolved by Story 1.2's existing config, not a new field.

**Acceptance Criteria (draft):**

**Given** `source_of_truth: jira` and the Atlassian Remote MCP Server already configured for this Claude Code session (org-level or project-level `.mcp.json`)
**When** the developer enters a JIRA issue key at kickoff (e.g. `jira-task-1234`)
**Then** the `story-kickoff` skill calls the MCP server's issue-fetch tool (`getJiraIssue`, per Atlassian's documented toolset) directly — no `JIRA_BASE_URL`/`JIRA_EMAIL`/`JIRA_API_TOKEN` env vars are read or required
**And** the fetched fields are normalized into the same `{points, goal, sprint, description}` shape Story 1.3 produced, then passed to `docs-only/main.py --source-of-truth jira` unchanged
**And** points confirmation stays human either way (CAP-1) — MCP-fetched points are a suggestion, never auto-written without developer confirmation
**And** a field the MCP tool doesn't return is `null`, elicited via the existing step-4 re-prompt rule — never invented
**And** if no JIRA MCP server is reachable/configured for this session, the skill tells the developer plainly and falls back to Story 1.3's token-based script *only if* `JIRA_BASE_URL`/`JIRA_EMAIL`/`JIRA_API_TOKEN` happen to be set, otherwise falls back to the plain docs-only ask — it never blocks kickoff (FR5)
**And** NFR4 is satisfied more simply than before: no JIRA credential of any kind is ever read, held, or written by this tooling — auth lives entirely in the MCP server's own OAuth session

**Testing strategy (decided 2026-07-10 — this story is skill-flow work, not script work):** Story 1.3 was a subprocess script, fully unit-testable with pytest; Story 1.6 changes the `story-kickoff` skill's conversational step 4a, which pytest cannot reach. Manual E2E against a real Atlassian test site (available — confirmed 2026-07-10) is therefore the *primary* verification, not the backstop. The story's Definition of Done must include a scripted E2E pass covering at minimum: (a) happy path — issue key → MCP fetch → confirm → `.story.yaml` written with `source_of_truth: jira`; (b) issue key not found; (c) MCP server not connected → graceful fallback message, kickoff still completable via plain ask (FR5); (d) points absent from the MCP response → null elicited via re-prompt rule, never invented. Any *new or changed* subprocess code (e.g. normalization helpers, if extracted) still gets pytest coverage per the repo standard; invocation remains natural-language ("kick off this story"), not a formal command (decided 2026-07-10).

**Open questions to resolve before implementation:**
- Confirm the exact MCP tool name and its response shape as exposed inside this project's Claude Code session (`getJiraIssue` per Atlassian's docs, but the effective tool name Claude Code sees is prefixed, e.g. `mcp__atlassian__getJiraIssue` — verify via `ToolSearch`/`.mcp.json` once the server is actually connected). An Atlassian test site is available for this (confirmed 2026-07-10); needs `.mcp.json` configured + one OAuth login before the schema can be inspected empirically.
- Confirm whether story points live on a custom field visible to the MCP tool's response the same way Story 1.3 read `customfield_10016`, or whether the MCP tool's normalized response omits it (in which case points would come back `null` more often and rely on Phase-1 estimate + human confirmation).
- Decide whether the API-token path (Story 1.3) stays as a documented fallback long-term, or is deprecated/removed once MCP is proven out in the pilot.

---

## Epic 2: Metrics Appear Automatically When You Close a Story

A developer works normally and, on closing the story, a trustworthy metrics snapshot exists — no manual reporting, no placeholder numbers.

> ✅ **Epic complete** — 2026-07-10, all 6 stories done (PRs #10, #11, #12, #13, #14, #15).
>
> **Retro note (§13):** *What worked* — the shared-emitter spine amendment (Story 2.3) paid for itself immediately: extending it to a third producer family (the opsx wrapper, Story 2.4) and reusing its `git_out()` helper for the assembler's git queries (Story 2.6) both required zero new subprocess-safety code. Extending existing components (the assembler, the docs-only writer) rather than creating parallel ones kept drift low across six stories touching the same files repeatedly. E2E discipline was decisive, not decorative: real-git/real-pipe testing caught 5 of this epic's defects outright (3 BOM-family bugs in 2.2/2.3, a cwd-addressing bug and a latent null-parsing bug in 2.6) that mocked unit suites alone did not surface — several as plausible-looking wrong answers, not crashes, the hardest failure mode to catch any other way. The LLM review loop (Gemini) converged to zero findings on 3 of 6 stories by the epic's end, visibly benefiting from earlier rounds' feedback (URL encoding, resilient parsing, format-over-membership validation) being pre-applied rather than re-caught.
>
> *What to watch* — Story 2.5 shipped without persisting its own output (the Phase-1 estimate), a gap only surfaced when Story 2.6 needed to read it back; the fix (AD-6a) was correct but retroactive. Future create-story passes should explicitly check whether a story's stated ACs, taken alone, satisfy every architecture invariant that later stories in the same epic will depend on — not just the epic document's per-story AC list. Also: this epic's `git_out()` reuse discipline (Issue #7's resolution) held up well through a second consumer; worth revisiting if a fourth producer family ever needs it, to confirm the shared module still earns its keep at that scale.

### Story 2.1: Hook Installation Is a Single Repeatable Setup Step

> ✅ **Complete** — 2026-07-10 · [PR #10](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/10)

As a developer joining the project,
I want one command to install all capture hooks,
So that my activity is captured identically to everyone else's on the team.

**Acceptance Criteria:**

**Given** a fresh clone of the repository
**When** the developer runs `tools/setup-hooks`
**Then** it installs git hooks into `.git/hooks/` and merges the required entries into `.claude/settings.json` (AD-8)
**And** hook logic lives in git-tracked `tools/hooks/`, never hand-maintained per machine

### Story 2.2: Git Activity Captured Silently While You Work

> ✅ **Complete** — 2026-07-10 · [PR #11](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/11)

As a developer,
I want my commits/checkouts/merges captured automatically,
So that my metrics build up without extra effort.

**Acceptance Criteria:**

**Given** the hooks from Story 2.1 are installed
**When** a developer commits, checks out, or merges
**Then** a `git.*` namespaced event is atomically appended to `.story-events.jsonl` (AD-1, AD-1a)
**And** events firing before `.story.yaml` exists are buffered, never dropped (AD-1b)
**And** a failed append retries up to 3 times, then surfaces a visible error to the developer (AD-9)

### Story 2.3: AI Session Activity Captured Silently

> ✅ **Complete** — 2026-07-10 · [PR #12](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/12)

As a developer using Claude Code,
I want my AI session activity (tool use, prompts, token usage) captured automatically,
So that cost and phase metrics exist without manual reporting.

**Acceptance Criteria:**

**Given** Claude Code hooks are configured (Story 2.1)
**When** an AI session runs
**Then** it appends `ai.claude-code.*` namespaced events via the normalized AD-10 adapter shape
**And** a signal Claude Code cannot report is emitted null-with-reason, never defaulted to zero (AD-10)
**And** a failed append follows the same retry-then-surface rule as Story 2.2 (AD-9)

### Story 2.4: Story Closes and a Snapshot Is Created Automatically

> ✅ **Complete** — 2026-07-10 · [PR #13](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/13)

As a developer,
I want closing my story to automatically produce a metrics snapshot,
So that I never manually compile a report.

**Acceptance Criteria:**

**Given** a developer runs `opsx archive`
**When** the CLI wrapper intercepts the command
**Then** the snapshot assembler reduces the full event log (Stories 2.2, 2.3) into the fixed envelope shape: `schema_version, story_id, revision, pm_metrics, engineering_metrics, story_point_cost, token_cost` (AD-3a)
**And** every close produces a new immutable revision; nothing is overwritten in place (AD-3)

### Story 2.5: Story Points Are Estimated Automatically at Kickoff

> ✅ **Complete** — 2026-07-10 · [PR #14](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/14)

As a developer,
I want my story's points estimated automatically from its scope and complexity,
So that I don't have to guess a number myself.

**Acceptance Criteria:**

**Given** a story at kickoff
**When** the Phase-1 formula runs
**Then** it computes base points from task count in `tasks.md`, plus a volatility bonus from openspec stage maturity, plus a novelty modifier from pattern-matching prior `.story.yaml` records (AD-6)
**And** the resulting complexity classification feeds only this point estimate, never a capture on/off decision (FR5)

### Story 2.6: Story Points Are Reconciled Against What Actually Happened

> ✅ **Complete** — 2026-07-10 · [PR #15](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/15)

As a developer,
I want my estimate compared against what actually happened when I close the story,
So that leadership sees real variance instead of a static guess.

**Acceptance Criteria:**

**Given** a story with an event log (Stories 2.2–2.4) and a Phase-1 estimate (Story 2.5)
**When** the story closes
**Then** the Phase-2 formula computes actual points from review cycles, agent-narrated decision events, and testing-type weights (AD-6)
**And** the variance between the Phase-1 estimate and Phase-2 actual is logged, with neither number overwritten

---

## Epic 3: Time Tracked Without Logging Hours

Switching between stories never corrupts time attribution, and nobody manually starts or stops a timer.

> ✅ **Epic complete** — 2026-07-10, all 3 stories done (PRs #16, #17, #18).
>
> **Retro note (§13):** *What worked* — the same "shared, source-parameterized emitter" discipline from Epic 2 carried straight into Epic 3: every new mechanic (`update_active_story`, `record_activity`, `repoint_active_story`, `close_active_story_slice`) was built as a sibling function reusing `emit()`/`write_atomic_json()`/`read_active_story()`, never a parallel append or I/O path — zero new event-integrity code needed across 3 stories despite adding 2 new event types (`time.slice_opened/closed/paused`) and 2 new local state files (`.active-story`, `.active-claude-session`). Live E2E (real git repos, real hook invocations via `uv run --script`) caught nothing new this epic but continued to be the final confirmation step every story leaned on, consistent with Epic 2's finding that it's the strongest signal mocked unit suites alone miss. Story 3.3 completed a rule (session-level slices closing on `SessionEnd`) that had been written into `ARCHITECTURE-SPINE.md` before Epic 3 even started but was left half-wired by Story 3.1 — a good example of a story's own dev notes correctly flagging and closing a cross-story architecture gap before it became a silent one, the same lesson Epic 2's retro flagged as a process improvement.
>
> *What to watch* — the LLM review (Gemini) surfaced a genuinely valid Critical finding on PR #17 (a malformed `STORY_IDLE_THRESHOLD_SECONDS` env var crashing module import, which would have blocked every commit) but also produced a misattributed bullet on **both** PR #16 and PR #18 — content from a different story's actual diff, presented as if it were about the PR under review. Caught both times by grep-verifying the claim against the actual changed files before acting; this is now the second epic in a row where this reviewer has produced at least one hallucinated/misattributed finding (Epic 1's retro flagged the first). Keep grep-verifying every finding, every PR, rather than trusting the review's framing at face value. Separately: PR #17 also failed CI on `ruff format --check` even though local `ruff check` (lint) had passed — format and lint are separate CI gates in this repo and both must be run locally before pushing; this was corrected and held for the rest of the epic.

### Story 3.1: Active-Story Pointer Tracks Time Automatically

> ✅ **Complete** — 2026-07-10 · [PR #16](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/16)

As a developer,
I want the system to know which story I'm actively working on without me telling it,
So that my time-on-task is attributed correctly without logging hours.

**Acceptance Criteria:**

**Given** the branch-per-story convention (NFR5) and hooks installed (Story 2.1)
**When** the developer checks out a story branch or a Claude Code session starts
**Then** `.active-story` updates, closing the outgoing story's time slice and opening a new one for the incoming story (AD-7)

### Story 3.2: Idle Time Doesn't Inflate a Story's Active Time

> ✅ **Complete** — 2026-07-10 · [PR #17](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/17)

As a developer,
I want idle periods (meetings, breaks) excluded from my active time,
So that time-on-task reflects real work, not an open session.

**Acceptance Criteria:**

**Given** an active time slice from Story 3.1
**When** there is no `PostToolUse`/prompt activity for a configurable idle threshold (default: exactly 15 minutes)
**Then** the active slice auto-pauses (AD-7)

### Story 3.3: Mid-Session Checkout Doesn't Double-Count Time

> ✅ **Complete** — 2026-07-10 · [PR #18](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/18)

As a developer,
I want switching story branches mid-AI-session to not corrupt time totals,
So that my time attribution stays accurate even when I context-switch quickly.

**Acceptance Criteria:**

**Given** a live Claude Code session (Story 3.1)
**When** a `git checkout` happens mid-session
**Then** the live session's `SessionStart`/`SessionEnd` boundaries govern time-slice accounting
**And** the checkout re-points which story current activity counts toward, without itself opening or closing a session-level slice (AD-7 precedence rule)

---

## Epic 4: Package and Distribute the Capture Tooling to a Target Repo

> 🆕 **Opened 2026-07-10** — surfaced during pre-deploy smoke testing (see `docs/testing/pre-deploy-smoke-checklist.md`). AD-8 assumed `tools/` already lives inside a target project's own repo, but no story ever designed how it gets there. Cloning this planning repo wholesale (specs, BMad artifacts, prompts, `_bmad-output/`) is not a viable install path for a pilot team's own project.

A developer on a target project can get the capture tooling (`tools/`, its tests, and its minimal dependency footprint) into their own repo without also importing this repo's planning artifacts, specs, or history.

**Not covered by the original SPEC.md** (CAP-1..7) — this is an operational/deployment gap identified after the fact, not a reconciled capability. Revisit `SPEC.md` and the architecture spine (AD-8) once the distribution mechanism is chosen, so the constraint is captured canonically rather than living only here.

### Story 4.1: Choose and Implement a Distribution Mechanism for the Capture Tooling

> ⏳ **Not started**

As a developer on a target project,
I want a documented, repeatable way to bring only the capture tooling into my project,
So that adopting metrics capture doesn't require cloning or vendoring this planning repo's specs, prompts, and BMad artifacts.

**Acceptance Criteria (draft — pending a decision on mechanism):**

**Given** a target project that wants to adopt the capture pipeline
**When** a developer follows the documented install path
**Then** only `tools/`, `tests/` (or an equivalent minimal test footprint), and the dependency declarations needed to run them land in their repo — not `_bmad-output/`, `prompts/`, `openspec/`, or this repo's own specs
**And** `tools/setup-hooks.py` (Story 2.1) still works unmodified against the vendored copy
**And** the mechanism is a single documented command/step, not a manual file-by-file copy
**And** picking up an update to `tools/` later (e.g. a new hook or a bugfix) has a defined, repeatable path — not just a one-time copy
**And** the documented install path states every prerequisite up front (below), so a developer isn't discovering a missing piece mid-install

**Prerequisites to document (confirmed by inspecting `tools/`; every hook/adapter script is stdlib-only — `urllib`, `json`, `subprocess`, `argparse`, no third-party runtime imports anywhere under `tools/`):**

| Prerequisite | Why | Notes |
| --- | --- | --- |
| **Git** | Hooks are git hooks (`post-commit`, `post-checkout`, `post-merge`, `commit-msg`); branch-per-story convention (NFR5) | Any reasonably current version. On Windows, cloning **this planning repo** additionally needs `git config core.longpaths true` (its `_bmad-output/` paths exceed the 260-char limit from deep clone destinations — hit in real testing 2026-07-10); the release artifact won't carry those paths, making this a non-issue for target repos |
| **Python 3.8+** | `requires-python = ">=3.8"` in `pyproject.toml`; every hook/adapter script targets this floor | Matches `ruff`'s `target-version = "py38"` too |
| **uv** | Every script is invoked via `uv run` (PEP 723 inline script headers); git hooks are thin shell/batch shims that call `uv run <script>.py` (per epics.md build convention) | Must be on `PATH` — this is exactly what broke in initial testing when `uv run pytest` failed to spawn on a fresh clone |
| **Claude Code** | Only required if `ai_tool: claude-code` (default) — the `.claude/settings.json` hook entries and `tools/hooks/claude/*.py` producers need it running | Not required for git-only capture if a project declares no AI tool |
| **Atlassian Remote MCP Server access** (only if `source_of_truth: jira`, pending Story 1.6) | The JIRA fetch is moving from a personal API token to the org's already-configured Atlassian Remote MCP Server (`https://mcp.atlassian.com/v1/mcp/authv2`), OAuth 2.1-authenticated under the developer's existing JIRA access — no token to provision | Requires the MCP server to already be configured in the developer's Claude Code setup (`.mcp.json` or org-level); `JIRA_API_TOKEN` (Story 1.3) remains only as a documented fallback, not the primary path |
| **Confluence API token** (only if `source_of_truth: confluence`, until an MCP equivalent is decided) | Adapter (`tools/adapters/confluence/main.py`) is currently a plain `urllib` REST call — **no MCP server yet** | Env vars: `CONFLUENCE_BASE_URL` (include `/wiki` for Cloud), `CONFLUENCE_EMAIL`, `CONFLUENCE_API_TOKEN`. Same personal-token concern as JIRA's original design applies here too — revisit once Story 1.6 (JIRA→MCP) is proven out, since the Atlassian Remote MCP Server also covers Confluence |
| **No third-party Python packages at runtime** | `pytest`/`ruff` (`pyproject.toml` `dependency-groups.dev`) are dev-only, needed to run this repo's own test suite — **not** needed by a target repo just running the installed hooks | Worth calling out explicitly so target teams don't assume they need `uv sync` with the dev group just to use the tooling |

**Correcting a likely misconception before this ships as install docs:** `source_of_truth: docs-only` does not read, parse, or ingest any shared document — it's a plain conversational elicitation where the developer types points/goal/sprint directly into the `story-kickoff` skill, which then writes `.story.yaml`. There is no supported document format for docs-only. For JIRA, Story 1.6 (see Epic 1) moves the fetch to the Atlassian Remote MCP Server instead of a personal API token — Confluence still uses a plain `urllib` REST call with a personal token for now (same gap Story 1.6 is fixing for JIRA), pending a decision on whether to extend the MCP approach to Confluence too, since the same Atlassian Remote MCP Server also exposes Confluence tools.

**Decision status (2026-07-10): recommendation is the release artifact — pending final confirmation before implementation.**
- **Release artifact (recommended)**: tag a release here; CI zips `tools/` + `.claude/skills/story-kickoff/` + a small install script; target team downloads from the GitHub Releases page (which doubles as the public prerequisite/download URL for install docs) and runs one command inside their own repo. Fits this codebase's stdlib-only, no-build-step design; updates = download next tag, re-run install.
- **Git subtree/submodule (rejected)**: submodules impose clone/update friction on teams that didn't opt in; subtree pulls this planning repo's history (specs, prompts, BMad artifacts) into the client's project — the exact wholesale-clone problem this epic exists to fix.
- **Template repo (rejected)**: permanent two-repo sync burden with inevitable drift, and only helps at project-creation time — useless for existing projects adopting the tooling.

**Held for later (not in this story):** automatic update/sync tooling beyond the initial install path; versioning/compatibility policy between the tooling's version and a target repo's pinned copy.

### Story 4.2: `develop` Promotes to `main` on a Defined Release Cadence

> ⏳ **Not started** — opened 2026-07-10 from a live smoke-test failure

As a pilot developer cloning this repository,
I want the default branch a fresh clone lands on to actually contain the shipped tooling,
So that the documented install steps work on first contact instead of failing with "program not found."

**What happened (2026-07-10):** the first real fresh-clone smoke test failed at `uv run pytest` → `Failed to spawn: pytest — program not found`. Root cause: `git clone` checks out `main` (the default branch), and `main` is **33 commits behind `develop`** — no `pyproject.toml`, no `uv.lock`, no `tools/`, no `tests/`. All 18 story PRs (Epics 1–3) merged to `develop`; nothing was ever promoted to `main`. A pilot rollout at that moment would have shipped an empty tool. Reproduced independently on a second fresh clone the same day.

**Acceptance Criteria (draft):**

**Given** all three implementation epics are complete on `develop` and CI is green
**When** a release is cut
**Then** `develop` merges to `main` via a reviewed PR (per project-context.md conventions), so a fresh clone's default checkout contains the complete tooling
**And** the release rule is written down in `project-context.md`: what triggers a promotion (e.g. an epic completing, or a tagged release for Epic 4's artifact), and that `main` must never sit behind `develop` across a rollout boundary
**And** once Story 4.1's release-artifact flow exists, tagging `main` is what produces the distributable — making "main is current" a hard precondition of every release rather than a convention

**Relationship to Story 4.1:** independent and unblocking — this story is worth doing immediately (it's one PR plus a documented rule) even before the distribution mechanism is built, since anyone cloning the repo today gets a broken default branch.
