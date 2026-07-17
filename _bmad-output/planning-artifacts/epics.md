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
>
> 🔍 **Pilot-testing finding (2026-07-16):** `tools/build-release/INSTALL.md` has full "setup" and "daily use" sections for JIRA (and docs-only), but Confluence — a fully built, tested, live-verified backend since Stories 1.4/1.8 — has none at all: no dedicated setup section, no daily-use step list, and the Prerequisites table only mentions JIRA. A developer setting `source_of_truth: confluence` gets no install-time guidance whatsoever, despite the config example listing it as a supported value. Noticed directly by the user while reading the installed docs. Backlog, not urgent — candidate fix: extend "JIRA setup" to cover both backends (they share the same Atlassian MCP connection) and add a "Daily use — Confluence flow" section mirroring the JIRA one, including the real, currently-open MCP gap (no page-label read support, so points/sprint always need manual entry via that path, unlike JIRA).

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

### Story 1.7: Docs-Only Kickoff Reads a Requirements Doc and Relaxes Sprint for Ad Hoc Teams

> ✅ **Complete** — 2026-07-11 · [PR #21](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/21) (squash-merged to `enhancements`, da3b593). Manual E2E of the skill-flow scenarios deferred to the user's own post-release testing pass, by explicit instruction.

As a developer on a project with no PM tool,
I want kickoff to optionally read a requirements document I point it to, and to not force a fake sprint number on a team that doesn't run sprints,
So that docs-only kickoff is genuinely adapted to "no PM tool," not just "no JIRA/Confluence," and points/goal aren't guessed blind when a PRD already describes the work.

**Context:** raised during live testing of the release artifact (2026-07-11). Docs-only kickoff currently never reads any document — it's a pure conversational ask, and `sprint` is a required field for every backend including docs-only, forcing ad hoc teams to invent a sprint number they don't have. Both are real gaps in CAP-4's "adapts to whatever tool or lack of tool" premise, not implementation bugs.

**Acceptance Criteria (draft):**

1. **Given** `source_of_truth: docs-only` at kickoff
   **When** the skill runs
   **Then** it asks whether the developer has a requirements document (PRD) and, if so, its path
   **And** it reads `.md`/`.txt`/`.pdf`/`.docx` directly; a legacy binary `.doc` or unreadable file is not fatal — the skill says so plainly and falls back to the plain ask
   **And** the document's content is summarized, never dumped verbatim into the manifest or chat
2. **Given** a requirements document was read
   **When** the skill elicits points and goal
   **Then** it presents a **document-derived suggestion** for both, as a second advisory signal alongside any Phase-1 estimate (never silently written — same "suggest, human confirms" pattern as Phase-1; CAP-1 points confirmation stays human)
3. **Given** the skill elicits points, goal, and sprint
   **When** it prompts the developer
   **Then** it uses `AskUserQuestion` (structured options + freeform "Other") for **points** and **sprint**; **goal** is asked as free text (optionally pre-filled with a document-derived candidate) since a one-line objective doesn't fit a small options set
   **And** the "goal" question is phrased in plain language (e.g. "What does done look like for this story?"), not the bare word "Goal"
4. **Given** `source_of_truth: docs-only` specifically (JIRA/Confluence unaffected — they have a real sprint concept to pull from)
   **When** the developer has no milestone/release/sprint concept to give
   **Then** an explicit "none"/"N/A" answer is accepted as valid — the skill does not re-prompt forever demanding a fabricated value
   **And** the elicitation wording reflects this (e.g. "Milestone, release, or time period this belongs to — say 'none' if you don't track this")
   **And** the manifest's `sprint` field itself stays named `sprint` regardless of backend (AD-4 normalized shape unchanged) — only the docs-only question wording and requiredness change; JIRA/Confluence keep `sprint` required exactly as today
5. **Given** `source_of_truth: docs-only` (decided 2026-07-11: docs-only-only, not a cross-backend AD-4 change — see Held for later)
   **When** the skill elicits the required fields
   **Then** it also asks for a short human-readable **Story Name** (e.g. "Auth Module Implementation") as free text, before goal/points/sprint
   **And** the manifest gains a new optional `name` field (`null` for JIRA/Confluence, which don't ask for it in this story), positioned right after `story_id`
   **And** the kickoff completion summary shows **Name** right after **Story ID** — directly fixes the "opaque `story_id`-only summary" gap found in testing
6. **Given** a developer just completed docs-only kickoff and isn't sure what's next
   **When** they read `INSTALL.md`
   **Then** it documents the real sequence with a concrete example: `/opsx:propose <change-name>` (developer-chosen kebab-case, **never** `story_id` — verified against `.claude/commands/opsx/propose.md`) ideally before kickoff for a real Phase-1 estimate, then normal work, then `/opsx:apply`, then `/opsx:archive`
   **And** when Phase-1 comes back null because no openspec change was found, the skill adds a one-line non-blocking nudge toward `/opsx:propose` (FR5 — informational only)

> 🔍 **Post-implementation finding (2026-07-13, live pilot testing):** during the no-MCP fallback path (JIRA MCP tools unavailable, kickoff degrading to manual elicitation per CAP-4/AD-10), the first `AskUserQuestion` call threw a visible `InputValidationError` (partial payload: `"origin": "array"...`) before silently retrying and succeeding — the developer saw a raw tool-use error flash by, though kickoff still completed correctly. Not reproduced on the JIRA-success path (which only asks a single confirm/override question), so it appears isolated to the fallback path's multi-field elicitation (points + sprint asked together, per AC 3 above). Low severity — self-recovered, no bad data written — but a real, reproducible error worth a look: likely a malformed multi-question payload (missing/incorrect field on one of the two questions) in that specific branch of the skill's instructions.

**Held for later (decided 2026-07-11):** a `name` field for JIRA/Confluence too (JIRA's `summary` already maps to `goal` today — extending `name` cross-backend changes the AD-4 shape for all three adapters and needs its own design pass on whether `goal` then means something different for JIRA; revisit as its own story if wanted). Actually parsing structured data out of a PRD (e.g. extracting a formal task list) — this story only supports summarization to inform a human's own estimate, not automated extraction. Extending the same doc-read capability to JIRA/Confluence kickoffs, if ever wanted.

### Story 1.6: JIRA Adapter Fetches via the Atlassian Remote MCP Server

> ✅ **Complete** — 2026-07-11 · [PR #19](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/19) (squash-merged to `enhancements`, 9eddf90) — supersedes Story 1.3. E2E scenario A verified live pre-merge; scenarios B/C/D pending a convenient test window (tracked in `docs/testing/story-1.6-e2e.md`). Review note: 4th consecutive PR with a misattributed/hallucinated reviewer finding (this time crediting base-branch commits and an untouched `APPROACH.md` to the PR) — grep-verify discipline held.

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

**Empirical verification (2026-07-11, against `my-sg-custom-dashboard.atlassian.net`):**
- ✅ **OAuth flow works exactly as designed**: `claude mcp add --transport http atlassian https://mcp.atlassian.com/v1/mcp/authv2` (project-local scope), then `/mcp` in the CLI → browser OAuth → authenticated on first try. No token provisioned anywhere.
- ✅ **Full raw REST v3 issue shape survives the MCP layer** (fetched AI-53 with `fields: ["*all"]`): the response is the complete JIRA REST issue object wrapped in `{"issues": {"nodes": [...]}}` — custom fields intact, nothing normalized away.
- ✅ **Points field visible**: `customfield_10016` present in the response (null on the test issue only because no points were set — the correct elicitation-path trigger). Story 1.3's `DEFAULT_POINTS_FIELD` and `extract_points()` logic transfer as-is.
- ✅ **Sprint field visible**: `customfield_10020` with the full sprint-object list (closed + future entries on the test issue). Story 1.3's `extract_sprint()` rule (active wins, else last) handles the observed shape exactly.
- ✅ **Tool names confirmed**: `mcp__atlassian__getJiraIssue` does the fetch, but it requires a `cloudId` parameter — obtained by calling `mcp__atlassian__getAccessibleAtlassianResources` first. Step 4a is therefore a **two-call sequence** (resolve cloudId → fetch issue); the skill should cache/reuse the cloudId within a kickoff rather than re-resolving per field.
- ✅ **Positive-path points confirmed** (2026-07-11): after setting Story Points = 5 on AI-53, a re-fetch returned `customfield_10016: 5`. All empirical unknowns for this story are now closed; implementation can start.

**Remaining open questions:**
- Decide whether the API-token path (Story 1.3) stays as a documented fallback long-term, or is deprecated/removed once MCP is proven out in the pilot.
- Server-agnostic wording (decided 2026-07-11): the skill's step 4a should target *whichever JIRA MCP server the session has configured* (official Atlassian remote recommended as default; community `mcp-atlassian` also exists but registers zero tools without env credentials — observed live). Which server a project uses is a deployment/prerequisites choice, not skill logic.

### Story 1.8: Confluence Adapter Fetches via the Atlassian Remote MCP Server

> ✅ **Complete** — 2026-07-15 · [PR #40](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/40) (squash-merged to `enhancements-v2`, d47d4e8), found live during Confluence pilot testing: step 4b never got the MCP upgrade Story 1.6 gave JIRA. **Live-verified same day** (`story-20260715-480790`): a real kickoff against a real Confluence page correctly fetched via `getAccessibleAtlassianResources` → `getConfluencePage`, gave the honest labels-gap explanation, and wrote the manifest correctly. That same live test surfaced Story 1.9 below.

### Story 1.9: JIRA/Confluence Kickoff's Plain-Ask Fallback Wrongly Offered the Docs-Only "None" Sprint Option

> 🆕 **Built 2026-07-15** — found live during Story 1.8's own real-session verification: a Confluence kickoff correctly degraded to a plain manual ask (no MCP auth, no env credentials), but offered the docs-only-specific "None" sprint option, and the manifest writer correctly rejected it (`--sprint must not be empty` — sprint has always been required for JIRA/Confluence, only docs-only gets the "none" exception). Root cause: `SKILL.md`'s step 4 header already states the rule, but 4a's and 4b's own fallback text never repeated it at the point it actually matters — a pre-existing ambiguity since Story 1.6, just never live-caught until now. Fixed with explicit inline reminders at all three fallback points (4a's one, 4b's two). [PR #41](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/41) merged 65e22d5 into `enhancements-v2` (2026-07-15), synced to `main` by PR #43's epic sync — the fix is live. Not fully closed: Subtask 3.2 (a real live re-test of the no-MCP fallback path) is still open as of 2026-07-17.

Researched the real MCP capability before implementing, not assumed: the Atlassian MCP server does expose Confluence tools (`getConfluencePage` and related) — confirmed live in the user's own session, fetching a real page ("Fibonacci Series", ID 22020097). But it has two confirmed, currently-open platform gaps of its own: **no Confluence page-label read capability at all** (this project's points/sprint auto-fill has always worked via `points-<number>`/`sprint-<name>` labels), and **no short-link resolution** (`/wiki/x/...` URLs can't be turned into a page ID by the MCP tools). Unlike Story 1.6's clean win for JIRA, this is an honest tradeoff, not a strict upgrade: `story-kickoff/SKILL.md` step 4b now fetches via MCP by default (no personal token, asks for the full page URL and parses the numeric ID itself), but points/sprint always fall back to a plain manual ask over that path, with an explicit explanation of why — the script fallback (real Confluence REST API, personal token) remains the only way to get genuine label-based auto-fill. Skill-instruction-only change, no pytest surface (same precedent as Stories 1.6/2.10) — verified so far via research plus one real live MCP page fetch; a full live kickoff run against the updated instructions is the remaining proof point.

### Story 1.10: INSTALL.md Documents the Confluence Flow

> ✅ **Complete** — 2026-07-16 · [PR #51](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/51), merged 9abb7e8 (merged directly as docs-only, no LLM review pass). `tools/build-release/INSTALL.md` gains: a broadened Prerequisites row covering both JIRA and Confluence via the shared Atlassian MCP connection; "JIRA setup" renamed to "JIRA / Confluence setup" with a new Confluence-specific subsection explaining the MCP page-label gap and the script-fallback alternative; a full new "Daily use — Confluence flow" step list mirroring the JIRA one; and a new "Known limitations" entry stating plainly that Confluence kickoff never auto-fills points/sprint via MCP, only the goal. Pure documentation change, no pytest surface (same precedent as Story 5.1) — self-reviewed against `story-kickoff/SKILL.md`'s actual step 4b logic (the real source of truth for what Confluence kickoff does) rather than assumption.

As a developer whose project uses Confluence as its source of truth,
I want INSTALL.md to document the Confluence setup and daily-use flow with the same completeness as JIRA's,
so that I'm not left guessing how to configure or use a fully-built, already-shipped backend.

**Context:** logged as a 🔍 pilot-testing finding (2026-07-16, this epic's blockquote block, formalized into this story now). Noticed directly by the user while reading the installed `INSTALL.md`: only docs-only and JIRA have setup/daily-use sections, despite Confluence being a complete, tested, live-verified backend (Stories 1.4/1.8).

**Acceptance Criteria (draft):**

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

---

## Epic 2: Metrics Appear Automatically When You Close a Story

A developer works normally and, on closing the story, a trustworthy metrics snapshot exists — no manual reporting, no placeholder numbers.

> ✅ **Epic complete** — 2026-07-10, all 6 stories done (PRs #10, #11, #12, #13, #14, #15).
>
> 🔓 **Reopened 2026-07-11** — real pilot-simulation testing of v0.2.0 surfaced a severe (S1) bug in Story 2.1's hook installer: Claude hook commands are written as relative paths, which break permanently for the rest of a session the moment the developer `cd`s anywhere (e.g. into a subproject to build/test) — every subsequent tool call and `Stop` then fails to spawn, in an unrecoverable loop requiring a session restart. Superseded by **Story 2.7**.
>
> **Retro note (§13):** *What worked* — the shared-emitter spine amendment (Story 2.3) paid for itself immediately: extending it to a third producer family (the opsx wrapper, Story 2.4) and reusing its `git_out()` helper for the assembler's git queries (Story 2.6) both required zero new subprocess-safety code. Extending existing components (the assembler, the docs-only writer) rather than creating parallel ones kept drift low across six stories touching the same files repeatedly. E2E discipline was decisive, not decorative: real-git/real-pipe testing caught 5 of this epic's defects outright (3 BOM-family bugs in 2.2/2.3, a cwd-addressing bug and a latent null-parsing bug in 2.6) that mocked unit suites alone did not surface — several as plausible-looking wrong answers, not crashes, the hardest failure mode to catch any other way. The LLM review loop (Gemini) converged to zero findings on 3 of 6 stories by the epic's end, visibly benefiting from earlier rounds' feedback (URL encoding, resilient parsing, format-over-membership validation) being pre-applied rather than re-caught.
>
> *What to watch* — Story 2.5 shipped without persisting its own output (the Phase-1 estimate), a gap only surfaced when Story 2.6 needed to read it back; the fix (AD-6a) was correct but retroactive. Future create-story passes should explicitly check whether a story's stated ACs, taken alone, satisfy every architecture invariant that later stories in the same epic will depend on — not just the epic document's per-story AC list. Also: this epic's `git_out()` reuse discipline (Issue #7's resolution) held up well through a second consumer; worth revisiting if a fourth producer family ever needs it, to confirm the shared module still earns its keep at that scale.
>
> 🔍 **Pilot-testing finding (2026-07-16):** `tools/snapshot-assembler/main.py` (Story 2.4) has no dry-run/preview mode — `--help` only exposes `--repo-root`. Testing the defect-capture hook (Story 5.4/5.8) by deliberately introducing a compile error led to running the assembler just to see the event roll up into a snapshot, which — per AD-3 — closed the story for real (a mid-flight snapshot, taken before the code was even committed). Recoverable via a fresh run creating the next revision (AD-3b treats priors as audit history, not corruption, so nothing was lost), but avoidable: a `--dry-run` flag that runs the full reduction and prints the would-be snapshot to stdout without writing the file or consuming the AD-1b pending spool would let a developer preview current-state metrics without ever triggering the "story closed" signal. Backlog, not urgent.

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

> 🔍 **Post-implementation finding (2026-07-11, live pilot-simulation testing):** when `sessions_observed: 0` (no AI session events captured at all — as opposed to sessions existing but not reporting token cost), `token_cost.reason` comes back bare `null` rather than an explanatory string. AD-10's rule is "null-with-reason, never a bare null" — this may be a minor gap in that guarantee for the zero-sessions case specifically (every other null-token-cost snapshot observed so far carried a real reason string, e.g. "claude-code hooks do not report token usage"). Low severity, not yet turned into a story — worth a quick look at whether `sessions_observed == 0` should populate a reason too (e.g. "no AI sessions observed for this story"). **Confirmed with a live repro during 2026-07-14 pilot testing (`story-20260714-abfa46`: `ai_sessions: 1`, `sessions_observed: 0`, `reason: null`, visible as "not tracked — no reason given" in both the dashboard and metrics report) — now Story 5.6.**

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

### Story 2.7: Hook Commands Are Cwd-Independent (Absolute Paths)

> ✅ **Complete** — 2026-07-11 · [PR #22](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/22) (squash-merged to `enhancements`, 4d21476). Review found 2 real defects (fixed before merge, see the story's Review Follow-ups) and 5 misattributed findings — 2 of those 5 were legitimate concerns about untouched files, split out below as Stories 2.8/2.9.

As a developer,
I want the capture hooks to keep working no matter which directory I `cd` into during a session,
so that a normal workflow (building/testing a subproject) never permanently breaks metrics capture — or my whole session.

**What happened (verbatim from testing):** kickoff (Story 1.7) worked perfectly — name, PRD read, points/milestone via `AskUserQuestion`, all correct. The developer then did realistic work: used `/opsx:propose`/`/opsx:apply` to actually implement the proposed auth feature in `demo/user-auth-service/`, `cd`-ing into that subdirectory to run its own test suite. From that point on, **every** tool call failed with:
```
PreToolUse hook error: [uv run tools/hooks/claude/pre_tool_use.py]: error: Failed to spawn: `tools/hooks/claude/pre_tool_use.py`
Caused by: The system cannot find the path specified. (os error 3)
```
`Stop` failed identically on every turn boundary, producing an infinite loop with no recovery path inside the session — required killing and restarting entirely.

**Root cause (confirmed in code):** `tools/setup-hooks.py`'s `command_for()` writes a **relative** path into every Claude hook entry in `.claude/settings.json`:
```python
def command_for(script: str) -> str:
    return f"uv run tools/hooks/claude/{script}"
```
This only resolves correctly if the hook is invoked with the repo root as cwd. Claude Code's hook-invocation mechanism appears to reuse whatever working-directory state the session has drifted to (via the model's own `cd`s in Bash tool calls) rather than always using the workspace root — so the moment a session `cd`s into a subdirectory, every subsequent hook invocation looks for the script relative to the wrong location and fails to spawn entirely.

**Acceptance Criteria (draft):**

1. **Given** a repo where `tools/setup-hooks.py --repo-root <path>` has been run
   **When** `.claude/settings.json` is inspected
   **Then** every one of the six Claude hook commands (`SessionStart`, `SessionEnd`, `PreToolUse`, `PostToolUse`, `Stop`, `UserPromptSubmit`) is an **absolute path** to its script (resolved from `--repo-root` at install time), never a bare relative path
2. **Given** a live Claude Code session with hooks installed this way
   **When** the developer `cd`s into any subdirectory (or a subproject entirely) and continues working
   **Then** every hook continues to spawn and fire correctly — no `Failed to spawn` error, regardless of the session's current working directory at the moment a hook fires
3. **Given** an existing installation from before this fix (relative paths already in `.claude/settings.json`)
   **When** the developer re-runs `uv run tools/setup-hooks.py --repo-root .`
   **Then** the installer detects and upgrades the stale relative-path entries to absolute paths in place (the installer's existing idempotent-upgrade behavior, extended to cover this migration — not just a fresh install)
4. **Given** the git hook shims (`post-commit`, `post-checkout`, `post-merge`, `commit-msg`)
   **When** this story is implemented
   **Then** confirm whether they have the same relative-path fragility or are protected by git's own guarantee that hooks always run with cwd at the repo root (per the existing comment in `tools/hooks/_events.py`) — fix only if actually vulnerable; don't fix what isn't broken

**Held for later:** whether Claude Code itself should be more resilient to a hook failing to spawn (e.g. degrade to a warning rather than blocking every subsequent tool call) is an Anthropic-side concern, not something this codebase can fix — worth a `/feedback` report separately, but out of scope for this story's fix.

### Story 2.8: Git Commit Hooks Never Abort a Commit if `uv` Is Unavailable

> ✅ **Complete** — 2026-07-15, split out from PR #22's review (Gemini) — a real, valid finding, but about `tools/hooks/git/commit-msg.sh`, a file Story 2.7 never touched; [PR #39](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/39) (squash-merged to `enhancements-v2`, 1338f2a)

`tools/hooks/git/commit-msg.py` is deliberately written to always exit 0, but that guarantee only held once Python was actually running — `commit-msg.sh` invoked it via a bare `uv run ...`, and if `uv` itself wasn't on the invoking process's PATH, the **shell** failed before Python ever started, which git treats as a real abort signal for `commit-msg` specifically. Fixed with a `command -v uv` guard plus an unconditional `exit 0`, with a visible stderr warning on miss (AD-9). Applied the same guard to `post-commit`/`post-checkout`/`post-merge` too, for consistent messaging — though confirmed via `_events.py`'s own documented exit-code table that those three were never actually at risk (git ignores their exit codes already), so this is a UX polish for them, not a correctness fix. Verified live: a real scratch repo, real hook install, real `git commit` with `uv` stripped from `PATH` — commit succeeded with visible warnings, not blocked.

### Story 2.9: `repo_root()` Falls Back to a Parent-Directory Walk, Not Just Cwd

> ✅ **Complete** — 2026-07-15, split out from PR #22's review (Gemini) — a real, valid hardening suggestion, but about `tools/hooks/_events.py`, a file Story 2.7 never touched; [PR #39](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/39) (squash-merged to `enhancements-v2`, 1338f2a)

`repo_root()` used to fall back straight to `Path.cwd()` if `git rev-parse --show-toplevel` failed for any reason (timeout, `git` unavailable, OS-level limits). Story 2.7 already fixed the *primary* way a session's cwd can drift into a subdirectory; this story adds a smarter intermediate step for the rarer residual case: now walks up from cwd looking for a `.git` directory-or-file (worktrees/submodules use a file) before falling back to bare cwd. Verified with real-filesystem tests exercising the actual function directly (not monkeypatched away, unlike most other tests in this suite).

**Acceptance Criteria (draft):**

1. **Given** `git_out("rev-parse", "--show-toplevel")` returns `None` (git failed or is unavailable)
   **When** `repo_root()` is called from a subdirectory of the actual repo
   **Then** it walks up from the current directory looking for a `.git` directory and returns that parent, rather than returning the current (possibly nested) directory unconditionally
2. **Given** no `.git` directory is found anywhere in the parent chain (genuinely not inside a repo)
   **When** `repo_root()` is called
   **Then** it falls back to `Path.cwd()` exactly as today — this story only adds a smarter *intermediate* step, not a new failure mode

### Story 2.10: A Closed Story's Manifest Doesn't Block the Next Story's Kickoff

> ✅ **Complete** — 2026-07-13 · [PR #24](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/24) (squash-merged to `enhancements`, 05c29fa; branch preserved). Found live during pilot testing of the JIRA-via-MCP flow (v0.2.1, `ai-project-metrics-bmad-testing` test repo). Skill-instruction-only change (no pytest surface) — verified with 4 real live invocations of the actual skill, not simulated. Review found 3 real, correctly-attributed defects (explicit `<repo-root>`-relative path, missing-`snapshots/`-directory fallback, malformed-manifest fallback) — all fixed and re-verified live before merge.

As a developer,
I want kicking off a new story to work normally even though the previous story's `.story.yaml` was merged into my base branch,
so that ordinary branch-per-story git hygiene (branching the next story off `develop`, not off the previous story's branch) never gets blocked by a stale manifest.

**Context:** AD-5 requires `.story.yaml` to be git-committed per story, and it is — but no story, AD, or the Story DoD/Archival Checklist (`project-context.md` §12–13) ever defines how it's retired once that story closes. Concretely: `story-1` branches off `develop`, kickoff writes and commits `.story.yaml`, the story is archived (`opsx-wrapper archive`) and its branch merges back into `develop` — `.story.yaml` merges in too. `story-2` then branches off `develop` (completely normal git flow, not branching off `story-1`'s branch) and inherits story-1's `.story.yaml`. `story-kickoff`'s "Refuse a double kickoff early" guard (SKILL.md step 2) then blocks kickoff, telling the developer to "close out or archive the current story" — but story-1 *is* already closed; only its manifest file is still sitting there from the merge. Confirmed live: `story/AI-53` (branched after `story/add-user-basic-auth` had been archived, snapshotted, committed, and pushed) still carried the old story's `.story.yaml` and had to be manually `git rm`'d before kickoff would proceed.

**Acceptance Criteria (draft):**

1. **Given** a story has been successfully archived via `tools/opsx-wrapper/main.py archive <name>`
   **When** the archive completes successfully
   **Then** `.story.yaml` is removed (staged for the developer's next commit, consistent with "close = one command, nothing left dangling" — the same philosophy Story 2.4's wrapper already applies to the snapshot step) — needs a decision on whether removal is automatic-and-committed by the wrapper itself, or automatic-but-left-staged for the developer's own close-out commit
2. **Given** a project that doesn't use `openspec`/the opsx wrapper (plain docs-only or JIRA/Confluence close-out with no archive command)
   **When** a story is done
   **Then** define an equivalent manual or documented step so the same stale-manifest problem doesn't occur for non-openspec projects too
3. **Given** the fix above
   **When** `story-2` is branched off `develop` after `story-1`'s manifest-clearing change has merged
   **Then** kickoff proceeds normally with no stale-manifest block

**Design decision (resolved 2026-07-13, before implementation):** not a wrapper-side automatic teardown (that would only cover the openspec/opsx path, and mutating git state as a side effect of archiving is a surprising thing for a wrapper to do) and not a manual checklist step (too easy to forget, same class of problem as Story 2.11). Instead: `story-kickoff`'s own "Refuse a double kickoff early" guard (SKILL.md step 2) gets smarter. AD-3 already guarantees a snapshot is the authoritative signal a story has closed — so when `.story.yaml` already exists, kickoff checks whether `snapshots/{story_id}.*.json` also exists for that manifest's `story_id`. If a snapshot exists, the story is provably already closed (just its manifest lingered via merge/branch-inherit) — kickoff says so plainly and offers to clear `.story.yaml` (confirmed, not silent) so the new kickoff can proceed. If no snapshot exists, it's genuinely the same in-progress story — today's hard block stays exactly as-is. This is backend-agnostic (works whether or not a project uses openspec) and needs zero new state or wrapper changes.

### Story 2.11: Setup Enforces `.gitignore` for Local Capture State (Prevents Silent Cross-Branch Data Loss)

> ✅ **Complete** — 2026-07-13 · [PR #23](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/23) (squash-merged to `enhancements`, 8397b95; branch preserved). Found live during pilot testing (flow-2 branch-switch scenario), severity high — silent data corruption, no error surfaced anywhere. Review found 3 real, correctly-attributed defects (batched `git ls-files` call, whitespace/anchored-entry tolerance, `.gitignore`-as-a-directory guard) — all fixed and tested before merge.

As a developer working multiple story branches off the same trunk,
I want `.story-events.jsonl` (and the other local capture files) to always be git-ignored,
so that switching between story branches never silently discards or forks captured events.

**Context:** INSTALL.md documents `.story-events.jsonl`, `.story-events.pending.jsonl`, `.active-story`, and `.active-claude-session` as files the developer should manually add to `.gitignore` — but nothing in `setup-hooks.py` enforces or validates this, and it's a single easy-to-miss bullet buried in the "Daily use" section, not the "Install" steps. In this pilot test, that bullet was missed, so `.story-events.jsonl` got committed on `story/add-user-basic-auth` and carried forward via normal branching.

**What happened (verbatim from testing):** with `.story-events.jsonl` git-tracked, `story/AI-53` and `story/AI-54` each accumulated their own committed version of the shared event log. Checking out between them caused git to silently overwrite the working-tree file with whichever branch's committed version was checked out — discarding, not merging, whatever events had been recorded on the branch just left. Confirmed via `Select-String` over the full log: every `AI-54`-branch event (the `stub.txt` commit, the AI-54 kickoff, etc.) was completely absent once back on `story/AI-53` — no error, no warning, just quietly missing data. Had a snapshot been assembled for either story mid-test, its `engineering_metrics` would have been silently wrong.

**Acceptance Criteria (draft):**

1. **Given** `tools/setup-hooks.py --repo-root .` is run (fresh install or upgrade)
   **When** the repo's `.gitignore` doesn't already contain `.story-events.jsonl`, `.story-events.pending.jsonl`, `.active-story`, and `.active-claude-session`
   **Then** the installer appends the missing entries automatically (creating `.gitignore` if absent), consistent with the "one command, nothing left dangling" philosophy already applied to `opsx-wrapper`'s archive step
2. **Given** a repo where one or more of these files is *already* git-tracked (this pilot's exact situation — a stale commit predates the fix)
   **When** the installer runs
   **Then** it detects the already-tracked file(s) and surfaces a visible, actionable warning (AD-9: never fail silently) — e.g. "`.story-events.jsonl` is tracked by git; this can silently fork your event log across branches — run `git rm --cached .story-events.jsonl` to fix" — rather than silently leaving the dangerous state in place
3. **Given** this fix
   **When** a developer works two story branches off the same trunk and switches between them repeatedly
   **Then** `.story-events.jsonl` is never touched by `git checkout` at all (untracked + ignored), so the log stays continuous and no branch's events are ever discarded or forked

**Held for later:** whether `setup-hooks.py` should also proactively scan for and warn about *other* dangerous already-committed local state beyond this specific file list — out of scope for this story, which fixes the concrete case actually found.

### Story 2.12: Dry-Run Mode for Snapshot Assembler

> ✅ **Complete** — 2026-07-16 · [PR #46](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/46), merged a86760c. `--dry-run` computes and prints the full snapshot to stdout without writing the file or consuming the AD-1b pending spool. Deliberately not threaded through `opsx-wrapper archive` (see Dev Notes "Why the wrapper is out of scope"). Live-verified in a real scratch repo: a subsequent real close after a dry run still produced `rev1`, not `rev2`. Gemini's review raised a merge-conflict warning against PR #45 (rounding fix, merged first) — verified for real via an actual scratch merge: `tools/snapshot-assembler/main.py` auto-merges cleanly (the two PRs touch non-overlapping regions), the only real conflict was two paragraphs both added at the same `INSTALL.md` anchor point, trivially resolved by keeping both.

As a developer,
I want to preview a story's current metrics without closing the story,
so that testing/inspecting in-progress capture (e.g. verifying the defect-capture hook fires correctly) never accidentally marks a mid-flight story as done.

**Context:** logged as a 🔍 pilot-testing finding (2026-07-16, this epic's blockquote block, formalized into this story now). `tools/snapshot-assembler/main.py` has no preview/dry-run mode — `--help` only exposes `--repo-root`. Per AD-3, a snapshot's mere existence is the authoritative "this story is closed" signal every other producer (`story-kickoff`'s double-kickoff guard, Story 2.10) relies on. Confirmed live in a pilot repo: a developer deliberately introduced a compile error to verify `PostToolUse`'s defect-capture hook (Story 5.4/5.8), then ran the assembler just to see that event roll up into a snapshot — which closed the story for real, with `engineering_metrics.commits: 0` (the actual code hadn't been committed yet). Recoverable (AD-3b: revisions are exclusive-create, never overwritten; a later real close creates the next revision, and the stale one is left as harmless audit history) but avoidable.

**Acceptance Criteria (draft):**

1. **Given** `tools/snapshot-assembler/main.py --repo-root <root> --dry-run`
   **When** the assembler runs
   **Then** it performs the exact same reduction as today (reads `.story-events.jsonl` + the AD-1b pending spool, computes all six envelope sections: `pm_metrics`, `engineering_metrics`, `story_point_cost`, `token_cost`, `estimated_cost`, `defect_metrics`) and prints the computed snapshot JSON to stdout
2. **Given** `--dry-run` is set
   **When** the assembler would otherwise write `snapshots/{story_id}.v{schema}.rev{N}.json`
   **Then** it skips that write entirely — no file is created, no revision number is consumed
3. **Given** `--dry-run` is set
   **When** the assembler would otherwise consume the AD-1b pending spool (append its events to the main log, delete the spool file)
   **Then** it skips that too — the pending spool is left completely untouched, so a later real (non-dry-run) run still sees and correctly backfills it
4. **Given** `--dry-run` is *not* set (the default)
   **When** the assembler runs
   **Then** behavior is byte-for-byte unchanged from today — this story only adds an opt-in preview path, never alters the existing close-time behavior
5. **Given** `tools/opsx-wrapper/main.py archive <name>`
   **When** a clean pass-through for this flag is possible without changing the wrapper's own archive semantics (it always performs a real `openspec archive` + real snapshot)
   **Then** evaluate threading `--dry-run` through to the assembler call for symmetry — informational only, not a hard requirement of this story if it doesn't fit cleanly (the wrapper's own `archive` action isn't itself dry-runnable, only its snapshot half is)

---

---

## Epic 3: Time Tracked Without Logging Hours

Switching between stories never corrupts time attribution, and nobody manually starts or stops a timer.

> ✅ **Epic complete** — 2026-07-10, all 3 stories done (PRs #16, #17, #18).
>
> 🔍 **Post-epic smoke-test finding (2026-07-11):** an abrupt VS Code shutdown (no `SessionEnd`) leaves a stale `.active-claude-session` marker. Until the next `SessionStart` self-heals it, any `git checkout` takes the "session live → repoint only" path with no live session actually present — skipping slice accounting it should have performed. Observed live (overnight, marker present + no `.active-story`). Low severity, but the snapshot assembler should treat a `session_start` with no matching `session_end` event as a reduced-confidence signal on that story's time totals. Backlog, not urgent.
>
> 🔍 **Pilot-testing finding (2026-07-16):** the raw-span fallback (`estimated_cost_of()`'s `duration_minutes` when no completed time slice exists) uses whichever event has the *latest* timestamp recorded for a story — including non-work bookkeeping events (`opsx.archive`, `session_start`/`session_end` themselves), not just real activity (`git.*` commits, `ai.claude-code.{prompt,tool_use}`). Observed live in a pilot repo: an `opsx archive` run nearly 2 hours after a story's real work had finished became the fallback's end-of-span, inflating a ~15-20 real-minute story to a reported 117.6 minutes / $19.60 `estimated_cost`. Only bites when Story 3.4's real-slice path is unavailable (which the 2026-07-11 finding above shows is common), so it compounds an existing gap rather than being new on its own. Backlog, not urgent — candidate fix: exclude only genuine bookkeeping event types (`opsx.*`, `ai.<tool>.session_start`/`session_end`, `time.*`) from the raw-span fallback's timestamp scan, keeping every other event type (`git.*` and all remaining `ai.<tool>.*` activity, e.g. `prompt`/`tool_use`/`tool_start`/`stop`/`defect_*`) — a narrower include-list of just prompt/tool_use would wrongly undercount real activity like defect-capture events.
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

### Story 3.4: Snapshot Assembler Reduces Idle-Aware Time Slices into Real Active-Time Duration

> ✅ **Complete** — 2026-07-15 · [PR #44](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/44), merged 2ddf985. Found during leadership Q&A prep: `estimated_cost_of()` in `tools/snapshot-assembler/main.py` computed `duration_minutes` as a raw `last_event_at - first_event_at` span, with no idle/pause subtraction at all — meaning Stories 3.1-3.3's own `time.slice_opened`/`time.slice_paused`/`time.slice_closed` events were captured but never actually consumed by the one place that turns them into a number leadership sees. Fixed by a new `active_time_seconds_of()` reducer, preferring idle-excluded active time when a completed slice exists, falling back to the original raw span otherwise. Live-verified with real hook subprocess calls (not just unit tests): a genuine `time.slice_closed` event's `duration_seconds/60` matched the computed `duration_minutes` exactly, and a separate abrupt-session-kill run confirmed the fallback path is unchanged. `INSTALL.md`'s v0.9.1 stopgap limitation narrowed to the one remaining caveat: a mid-session story switch still blends a session's time into whichever story was active at close (same limitation `token_cost` already has).

As someone reviewing the dashboard,
I want a story's reported duration to reflect actual active work time, not the calendar span between its first and last commit,
So that a story left open across days (or interleaved with meetings/other stories) doesn't report a wildly inflated duration and cost.

**Acceptance Criteria:**

**Given** a story's event log contains one or more `time.slice_opened` → `time.slice_paused`(0+) → `time.slice_closed` sequences
**When** the snapshot assembler reduces the story at close time
**Then** `estimated_cost.duration_minutes` is computed from the sum of each slice's `duration_seconds` minus that slice's own `slice_paused.idle_seconds` — not the raw first/last-event span

**Given** a story is closed while an AI session is still open (a dangling `slice_opened` with no matching `slice_closed` yet)
**When** the assembler runs
**Then** it falls back to the existing raw-span calculation with an honest `reason` explaining why (AD-10 null-with-reason pattern) — never a fabricated or silently-wrong active-time number

**Given** an older snapshot or an `ai_tool` whose hooks don't emit `time.slice_*` events
**When** the assembler reduces it
**Then** behavior is unchanged from today (raw span, no reason needed) — this story only improves the calculation when the richer signal exists, it never removes the existing fallback

**And** `INSTALL.md`'s "Known limitations" entry for `Duration`/`estimated_cost` is narrowed to describe only the remaining caveat (a mid-session story switch via `repoint_active_story()` still attributes a slice's whole time to whichever story was active when the AI session finally closes — the same session-vs-story blending `token_cost` already has, for time instead of dollars)

### Story 3.5: Raw-Span Fallback Excludes Bookkeeping Events

> ✅ **Complete** — 2026-07-16 · [PR #47](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/47), merged eefcd61. New `activity_span_of()` excludes only genuine bookkeeping event types (`opsx.*`/`session_start`/`session_end`/`time.*`) from `estimated_cost_of()`'s raw-span fallback — an exclude-list, not the narrower include-list originally drafted, corrected before implementation began (Dev Notes explain why). Live-verified in a real scratch repo: a real activity window (10:00–10:07) plus an `opsx.archive` event 2 hours later correctly produced `duration_minutes: 7.0`, not ~127. Merging after PR #46 (also merged same day) surfaced one real issue neither PR's own review caught: a test asserted the pre-rounding value for `estimated_cost.usd` — fixed post-merge-simulation, before either PR was actually merged to `main`, by running the full suite against a real combined-merge scratch test rather than trusting GitHub's conflict check alone.

As someone reviewing the dashboard,
I want the raw-span fallback duration to reflect real developer activity, not administrative/bookkeeping actions,
so that a story's reported duration/cost isn't inflated by an unrelated later command that happens to touch the same story_id.

**Context:** logged as a 🔍 pilot-testing finding (2026-07-16, this epic's blockquote block, formalized into this story now). Story 3.4's raw-span fallback (`estimated_cost_of()`, used whenever no completed `time.slice_*` sequence exists for a story) computes `duration_minutes` from `engineering_metrics.first_event_at`/`last_event_at` — the first and last timestamps of *any* event tagged with that `story_id`, with no filter on event type. Confirmed live in a pilot repo: an `opsx.archive` bookkeeping event, emitted by a re-run of the assembler/wrapper nearly 2 hours after a story's real work had finished, became the fallback's end-of-span — inflating a ~15-20 real-minute story to a reported 117.6 minutes / $19.60 `estimated_cost`. This compounds whenever Story 3.4's real-slice path is unavailable (already common — see this epic's 2026-07-11 finding), turning a "no idle exclusion" gap into an actively misleading number, not just an imprecise one.

**Acceptance Criteria (draft):**

1. **Given** the raw-span fallback is in effect for a story (no completed `time.slice_*` sequence exists)
   **When** `engineering_metrics.first_event_at`/`last_event_at` are computed (or a new duration-specific pair is computed for this purpose)
   **Then** only genuine bookkeeping event types are excluded from the span — `opsx.*`, `ai.<tool>.session_start`, `ai.<tool>.session_end`, `time.*` — every other event type (`git.*` and all remaining `ai.<tool>.*` activity, e.g. `prompt`/`tool_use`/`tool_start`/`stop`/`defect_*`) still counts, so real activity signals like defect-capture events are never undercounted
2. **Given** a story whose *only* events are bookkeeping ones (e.g. a kickoff immediately followed by an archive, no real work in between)
   **When** the assembler computes the raw-span fallback
   **Then** it degrades to null-with-reason (AD-10) rather than a fabricated zero or a misleading span from bookkeeping-only timestamps
3. **Given** this fix
   **When** a re-run of the assembler/wrapper happens well after a story's real work concluded (the exact scenario that surfaced this finding)
   **Then** `estimated_cost`/`duration_minutes` for that story are unaffected by the timing of that later re-run
4. **Given** Story 3.4's real-slice path (a completed `time.slice_*` sequence exists)
   **When** the assembler computes duration
   **Then** behavior is unchanged — this story only narrows the *fallback* path's event selection, it does not touch the idle-aware active-time calculation at all

---

## Epic 4: Package and Distribute the Capture Tooling to a Target Repo

> 🆕 **Opened 2026-07-10** — surfaced during pre-deploy smoke testing (see `docs/testing/pre-deploy-smoke-checklist.md`). AD-8 assumed `tools/` already lives inside a target project's own repo, but no story ever designed how it gets there. Cloning this planning repo wholesale (specs, BMad artifacts, prompts, `_bmad-output/`) is not a viable install path for a pilot team's own project.

A developer on a target project can get the capture tooling (`tools/`, its tests, and its minimal dependency footprint) into their own repo without also importing this repo's planning artifacts, specs, or history.

**Not covered by the original SPEC.md** (CAP-1..7) — this is an operational/deployment gap identified after the fact, not a reconciled capability. Revisit `SPEC.md` and the architecture spine (AD-8) once the distribution mechanism is chosen, so the constraint is captured canonically rather than living only here.

### Story 4.1: Choose and Implement a Distribution Mechanism for the Capture Tooling

> ✅ **Complete** — 2026-07-11 · [PR #20](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/20) (squash-merged to `enhancements`, 7b621ff). Verified live: built the artifact, extracted into a virgin git repo, hooks installed, a real commit captured to the pending spool with zero planning-repo files present.

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

> 🔁 **Superseded 2026-07-15** — the two-tier `develop`→`main` plan below is replaced by a simpler one: every story branch now opens its PR directly against `main` (no intermediate integration branch at all). See `project-context.md` §8/§10/§11 for the current rule. This entry is kept for history — the smoke-test failure it documents is exactly the class of bug the simpler flow prevents structurally (there's no second branch to fall behind).

As a pilot developer cloning this repository,
I want the default branch a fresh clone lands on to actually contain the shipped tooling,
So that the documented install steps work on first contact instead of failing with "program not found."

**What happened (2026-07-10):** the first real fresh-clone smoke test failed at `uv run pytest` → `Failed to spawn: pytest — program not found`. Root cause: `git clone` checks out `main` (the default branch), and `main` is **33 commits behind `develop`** — no `pyproject.toml`, no `uv.lock`, no `tools/`, no `tests/`. All 18 story PRs (Epics 1–3) merged to `develop`; nothing was ever promoted to `main`. A pilot rollout at that moment would have shipped an empty tool. Reproduced independently on a second fresh clone the same day, and again on 2026-07-15 in a separate testing repo (`ai-project-metrics-bmad-testing`) during Story 5.9's live verification — same root cause, different repo, which is what prompted dropping the two-tier branch model rather than continuing to patch around it.

**Resolution:** rather than building a `develop`→`main` promotion mechanism, the team moved straight to `main` as the only trunk (§10 of `project-context.md`). Every story branch merges to `main` directly via the existing PR + human + LLM review gate — no separate promotion step to forget.

### Story 4.3: One-Command Curl/irm Installer (No Manual Zip Download)

> ✅ **Complete** — opened 2026-07-14 after the user asked why this couldn't be "install like BMad or openspec"; PR #30, merged

A second, more convenient distribution path alongside Story 4.1's existing GitHub Releases zip — a single `curl -fsSL <url> | sh` (macOS/Linux) or `irm <url> | iex` (Windows) command, mirroring the exact pattern `uv`'s own installer already uses (already cited in this project's own `INSTALL.md`). The script resolves the **latest** release dynamically via the GitHub API, downloads and extracts the zip into the current directory, then prints the next step. Does not replace the manual zip-download path — both stay documented, this is additive. No automated test (not Python; same manual-E2E-only precedent as Story 2.7's git-hook shims); verified via real live E2E against the actual v0.3.0 release. Required making the GitHub repo public (was private, which blocks unauthenticated `curl`/`raw.githubusercontent.com` access) — confirmed with the user after a clean secrets scan of the full git history.

### Story 4.4: `.story-config.yaml.example` Template Shipped in the Release

> ✅ **Complete** — opened 2026-07-14, after the user asked why the config file couldn't ship as part of the build; PR #29

A commented `.story-config.yaml.example` (every documented key, commented out, with its default explained) now ships in the release artifact, so a developer copies-and-edits instead of hand-typing from `INSTALL.md`'s prose. Deliberately **not** auto-copied into `.story-config.yaml` — a project's absence of that file is meaningful (AD-4's docs-only default), and this story must not weaken that by silently deciding a `source_of_truth` on the developer's behalf.

### Story 4.5: Publish as a Package for a True One-Word Install (`uvx ai-metrics-capture install`)

> ✅ **Complete** — 2026-07-14 · [PR #37](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/37) (squash-merged to `enhancements-v2`, 496645a). Real PyPI publish is out of scope (intentionally, per this story's own AC 4) — gated behind Story 4.2, still parked.

Story 4.3's `curl`/`irm` one-liner is only as short as a raw GitHub URL allows — there's no name-resolution layer, so it must fully spell out host/org/repo/branch/path every time. `npx bmad-method install` is short specifically because npm's **registry** resolves the package name for you. Built a `pypi-package/` subdirectory (its own independent `pyproject.toml`, isolated from this repo's own dev/test config) with a `hatchling`-based package `ai-metrics-capture`, whose `install` console-script bundles the exact same files Story 4.1's zip artifact ships (reusing `tools/build-release/main.py`'s `iter_entries()` at a pre-build sync step, not a duplicated file list) and copies them into the developer's repo — no GitHub API call needed at install time, since `uvx` already resolved the right version. Verified live: real `uv build` + real `uvx --from <wheel>` install into a scratch git repo produced a file layout byte-identical (`diff -rq` empty) to a real zip extract. A `workflow_dispatch`-only, TestPyPI-targeting GitHub Actions workflow exists for future publishing, but nothing can actually publish anywhere until a human wires a real secret and Story 4.2 lands — this story ships the packaging, not a live PyPI presence.

### Story 4.6: One-Command Uninstall (`uninstall.sh` / `uninstall.ps1`)

> ✅ **Complete** — opened 2026-07-14, after the user asked how to reset a test repo back to a clean state between install tests; PR #31, merged

Teardown counterpart to Story 4.3's install scripts: `uninstall.sh`/`uninstall.ps1` remove everything the install and `setup-hooks.py` added — the extracted `tools/`/skill/`INSTALL.md`/config template, the four `.git/hooks/` shims, this tooling's own entries in `.claude/settings.json` (surgically, never the whole file), and any capture-time artifacts (`.story.yaml`, `.story-events.jsonl`, `snapshots/`, `metrics-reports/`, etc.) if present. Prints what it's about to remove and asks for y/N confirmation first (a `--yes`/`-Yes` flag skips the prompt for scripted use) — this is destructive, unlike install. No automated test (shell/PowerShell scripts, same manual-E2E-only precedent as 4.3).

### Story 4.7: `setup-hooks.py` Crashes on a BOM-Prefixed `settings.json`

> ✅ **Complete** — opened 2026-07-14, a real bug hit live during pilot testing; PR #34, merged

`setup-hooks.py` read `.claude/settings.json` with plain `utf-8`, so a BOM-prefixed file crashed with "Unexpected UTF-8 BOM" — fixed to `utf-8-sig` (this project's established convention for exactly this class of bug, now the 4th instance). Root cause traced to `uninstall.ps1`'s own settings.json rewrite step using `Set-Content -Encoding utf8`, which writes a real BOM on Windows PowerShell 5.1 — fixed to write BOM-less UTF-8 directly via `.NET`'s `UTF8Encoding($false)`. Two-sided fix: the read is now defensive against any BOM-writing tool, and the actual source of the corruption (this project's own uninstall script) no longer introduces one.

### Story 4.8: `.story-config.yaml.example` Template Missing Story 5.4's Defect-Capture Keys

> ✅ **Complete** — 2026-07-14 · [PR #35](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/35) (squash-merged to `enhancements-v2`, 111db78). Gemini review's 4 "unpatched defects" were all stale/misattributed (none of the named files were even in this PR's diff) — verified and confirmed already fixed in prior stories.

Story 5.4 added real, working `test_commands`/`build_commands` config keys but never updated the shipped `.story-config.yaml.example` template, `INSTALL.md`'s own embedded config example, or Story 4.4's template-completeness test's hardcoded key list — all three fixed. A real gap in Story 5.4's own Definition of Done that a stricter completeness check should have caught.

---

## Epic 5: Leadership-Ready Reporting and Real Cost/Defect Tracking

> 🆕 **Opened 2026-07-13** — a batch of enhancement requests from the user after two clean rounds of docs-only/JIRA pilot testing (v0.2.2), inspired partly by a richer per-story report format seen in a different tool (`developer_handover.md`/`metrics.md`-style: date/duration, story points, estimated cost, AI token cost, defect breakdown, testing/review efficiency, notes). Work happens on a new branch, `enhancements-v2`, off `enhancements` — **starting tomorrow (2026-07-14), not today.** Agreed priority order: A → B → C → E, with D last since its capture mechanism needs the user's decision first (not yet made).
>
> 🔍 **Pilot-testing finding (2026-07-16):** a real JIRA-flow snapshot (`story-20260716-ea94fb`) showed `token_cost.reason: "no assistant usage data found in transcript"` even though real work clearly happened (a real commit, a real defect_review event with a JIRA subtask). Root-caused by direct inspection of `.story-events.jsonl`: 3 `session_start` events existed for this story but only 2 `session_end` events — and the session that did essentially all the real work (96 of 98 session-tagged events, including the final commit and defect event) never sent `session_end` at all (the already-known VS Code "x"-button `SessionEnd` gap). `token_cost_of()` surfaces `reasons[0]` — the reason from the chronologically *first* `session_end` — which here belonged to an unrelated, near-empty 2-minute reconnect blip, not the real session. The displayed reason is technically true for that blip but misleading about what actually happened to the story's real token cost. Backlog, not urgent — candidate fix: when `session_start` count exceeds `session_end` count (i.e., at least one session never closed), say so explicitly instead of surfacing an unrelated closed session's own reason.
>
> 🔍 **Pilot-testing finding (2026-07-16):** across a full day of reading generated snapshots and reports, the user repeatedly lost track of what specific fields mean and how they're calculated (`phase1_points`/`phase2_points`/`variance`, `sessions_observed` vs `ai_sessions`, `duration_minutes`'s active-vs-raw-span distinction, etc.) — the explanations exist only in `tools/snapshot-assembler/main.py`'s docstrings and `INSTALL.md`, neither of which sits next to the actual output being read (`snapshots/*.json`, `metrics-reports/*.md`, `dashboard.html`). Backlog, not urgent — candidate fix: a single shared field-descriptions source, surfaced directly inside all three generated artifacts (a `field_guide` key in the snapshot JSON itself, a "Field Guide" appendix in the markdown report, and header tooltips in the HTML dashboard).

### Story 5.1: INSTALL.md — Numbered Steps, No Prose (small)

> ✅ **Complete** — 2026-07-14 · [PR #25](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/25) (squash-merged to `enhancements-v2`, 9130a94; branch preserved). Review found 1 real, correctly-flagged issue (a pipe-escaping edge case in the Prerequisites table) — verified to predate this PR (Story 1.7) but fixed anyway since the file was already being touched.

Strip `INSTALL.md`'s lengthy descriptive prose down to plain numbered steps ("Step 1.", "Step 2.", ...) for both the docs-only and JIRA flows separately, matching the step-list style the user has been using throughout pilot testing. Also make the archive→snapshot step explicit — state the literal `uv run tools/snapshot-assembler/main.py --repo-root .` (or the `opsx-wrapper` one-command equivalent) command to run after archiving, not just "produces a snapshot."

### Story 5.2: Real Cost and Token Fields Per Story (medium)

> ✅ **Complete** — 2026-07-14 · [PR #26](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/26) (squash-merged to `enhancements-v2`, 2593c02; branch preserved). Live E2E against a real Claude Code session transcript (not synthetic) found and fixed a real bug (stale reason shadowing real token data). Review found 2 more real, correctly-attributed defects (a `TypeError` crash risk on mixed-offset timestamps; a transcript memory-efficiency improvement) — both fixed and tested before merge.

Two things, both feeding a story's per-story cost picture:
1. **Real token counts** — the transcript-parsing enhancement scoped out 2026-07-13 (see `project_pm_metrics_pipeline.md` memory): `tools/hooks/claude/session_end.py` already receives `transcript_path` in its hook payload but doesn't read it; Claude Code's own local transcript `.jsonl` contains real per-turn `usage.input_tokens`/`output_tokens` (confirmed by direct inspection). Sum these across a session's transcript instead of emitting a bare null token_cost.
2. **Cost fields**, mirroring `developer_handover.md`'s formulas exactly:
   - `Estimated Cost = hourly_rate × duration` (duration already computable from `first_event_at`/`last_event_at`)
   - `AI Token Cost = (input_tokens × ai_input_rate / 1,000,000) + (output_tokens × ai_output_rate / 1,000,000)`
   - Rates (`hourly_rate`, `ai_input_rate`, `ai_output_rate`) belong in **`.story-config.yaml`** (this project's existing config file), not a new `.env` — stay consistent with the established config convention rather than introducing a second one.

**Caveat carried over from the original transcript-parsing discussion:** Claude Code's transcript format is an internal/unversioned schema, not a stable public API — this couples the implementation to whatever that format looks like today.

### Story 5.3: `metrics-<date>.md` Generator (medium, builds on 5.2 but doesn't require it first)

> ✅ **Complete** — 2026-07-14 · [PR #27](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/27) (squash-merged to `enhancements-v2`, 1339056; branch preserved). Live E2E against this project's own real accumulated snapshots (not synthetic fixtures) found and fixed 2 real gaps (a missing Goal line; a duration fallback for pre-Story-5.2-schema snapshots). Also fixed a small, previously-undiscovered gap: `pm_metrics.name` had been in `.story.yaml` since Story 1.7 but was never carried into the snapshot. Review found 2 more real defects (malformed-date-field guards) plus 1 stale/incorrect finding, correctly identified as such by diffing against the actual PR before acting.

A new tool that reads `snapshots/*.json` (kept as the canonical machine-readable artifact per AD-3 — this does not replace JSON, it renders a human-readable view alongside it) and writes/updates one markdown file per day (e.g. `metrics-07142026.md`) formatted like this repo's own existing hand-maintained `docs/metrics.md` — one section per story, with whatever fields are actually available (points, goal, engineering metrics, phase1/phase2 points, cost/token fields once 5.2 lands). Fields not yet captured (e.g. defect counts, before 5.4 exists) are shown honestly as "not yet tracked," never a fake zero — same null-with-reason philosophy as the rest of this pipeline.

### Story 5.4: Bug/Defect + Review-Efficiency Tracking

> ✅ **Complete** — PR #33, merged 934da7f. Resolved by studying `aep-orchestrator`'s reference implementation directly (its formulas are reused; its 100%-manual, two-disconnected-rounds capture mechanism is explicitly not copied, since the user's goal is avoiding developer intervention entirely, which that tool doesn't actually achieve)

**Final design:** compile/test defects are captured **fully automatically** by extending the existing `PostToolUse` hook to watch Bash tool calls against a project-configured `test_commands`/`build_commands` allowlist in `.story-config.yaml` — a matched command's non-zero exit appends a local `defect.compile`/`defect.test` event, no developer or AI action required, no command output ever captured (same privacy posture as this hook's existing fields). Review defects are captured **as a byproduct of this project's already-established practice** (paste an external review → verify each finding against the diff → fix the real ones) — fixing a verified-real finding now also logs a `defect.review` event and, for JIRA-backed stories, creates a real Jira Subtask via the already-connected Atlassian Remote MCP server (confirmed working with a real write — `AI-140` created as a Subtask under `AI-139` during this story's design phase). A key architectural constraint shapes the split: **MCP tools are only reachable from a live assistant turn, never from a hook subprocess** — so compile/test defects (hook-captured) stay local-only in this story; a Jira-sync step for them is an explicit, deferred non-goal. `testing_efficiency`/`review_efficiency` are `null` with a reason when zero defects were ever logged, never the reference tool's fabricated 100%/0% default. Requires one small prerequisite: persisting the parent Jira issue key in `.story.yaml` at kickoff (currently fetched transiently and discarded). Full story: `_bmad-output/implementation-artifacts/5-4-bugdefect-review-efficiency-tracking.md`.

### Story 5.5: Leadership HTML Dashboard (depends on 5.3, or reads snapshots directly)

> ✅ **Complete** — 2026-07-14 · [PR #28](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/28) (squash-merged to `enhancements-v2`, b958140; branch preserved). A self-contained, no-publishing-mechanism HTML dashboard (table + honest stat tiles, no chart, per the user's own explicit request and `dataviz`'s choosing-a-form guidance). Live E2E against real snapshot data found and fixed a missing-full-document-structure gap. Review found 1 real defect (a present-but-null snapshot section crash, verified with an actual before/after crash reproduction) and 1 stale finding — the third consecutive PR (#26, #27, #28) where the same already-fixed `TypeError` claim was incorrectly re-raised.

A static, self-contained local HTML file presenting the accumulated `metrics-*.md`/snapshot data as a shareable table for leadership — matching the existing pattern already in this repo (`docs/architecture-diagram-leadership.html`, `docs/new-machine-onboarding.html`). **Not** published via any hosted-link/artifact-publishing tool — this is internal, potentially sensitive leadership data (consistent with `APPROACH.md`'s "how this data will/won't be used" policy) and should stay a local file the user shares at their own discretion. Consult this project's `dataviz` guidance when building the actual table/layout.

### Story 5.6: `token_cost.reason` Is Bare `null` When Zero Sessions Observed

> ✅ **Complete** — opened 2026-07-14, closing out the 2026-07-11 finding (see Story 2.4's finding note above), confirmed with a live repro during 2026-07-14 pilot testing; PR #32, merged

Narrow fix to `tools/snapshot-assembler/main.py`'s `token_cost_of()`: when zero `session_end` events exist (`sessions_observed: 0`), `reason` currently comes back bare `null` instead of an explanatory string, violating AD-10's null-with-reason rule — confirmed live (`ai_sessions: 1`, `sessions_observed: 0`, "not tracked — no reason given" rendered in both the dashboard and metrics report). Does **not** attempt to make `ai_sessions` and `sessions_observed` match — they measure genuinely different things (sessions *started* vs. sessions that *ended cleanly with token data*) and a mismatch is expected whenever a session doesn't end gracefully (e.g. the VS Code window closed abruptly instead of `/exit`/`Ctrl+C`).

### Story 5.7: `post_tool_use.py` Reads `exit_code` From the Wrong Payload Location

> ✅ **Complete** — 2026-07-14 · [PR #36](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/36) (squash-merged to `enhancements-v2`, fc54d3e).

Root cause, confirmed against Claude Code's official hooks documentation: `post_tool_use.py` read `exit_code` from `tool_output.exit_code`, but Claude Code actually places it as a **top-level** `exit_code` key in the PostToolUse payload — so the guard never fired, for any command, ever. Story 5.4's own test suite didn't catch this because its hook-input fixtures baked in the same wrong (nested) shape, so 322 green tests validated against a payload shape Claude Code doesn't actually send. Fixed both the read and the fixtures, added a dedicated regression test, and verified live via two real subprocess runs of the actual hook script (one failing/matched, one passing) confirming `defect_compile` now fires correctly and only when it should. **Superseded almost immediately by Story 5.8** — the very next live test found the docs were wrong again, more fundamentally.

### Story 5.8: Automatic Defect Capture Cannot Rely on a Nonexistent `exit_code` Field

> ✅ **Complete** — built and merged 2026-07-15 ([PR #38](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/38), squash-merged to `enhancements-v2`, 4ac30c4), found live during JIRA-flow testing (`story-20260714-733705`) immediately after Story 5.7 shipped. **Live-verified same day** on v0.8.0 in a fresh JIRA test round (`story-20260715-ebfe10`): a real broken `hello-complie-error.ts` produced the injected `__AI_METRICS_EXIT__:2` marker in real stdout, and `.story-events.jsonl` shows 3 real `ai.claude-code.defect_compile` events across 3 failing `tsc` runs — confirming Claude Code's `PreToolUse` `updatedInput` mechanism genuinely works live, closing the one gap (Subtask 5.3) this story shipped with.

A deliberately broken `tsc --noEmit` (real `TS2322`, confirmed `exit 1`) still didn't produce `defect_compile` even after Story 5.7's fix. Root-caused via a real captured payload (a temporary, never-committed debug tap): Claude Code's PostToolUse payload has **no `exit_code` field at all**, ever — and the response key is `tool_response`, not `tool_output` as documented. Confirmed as a known, currently-unfixed Claude Code platform gap (`anthropics/claude-code#33656`, `rohitg00/agentmemory#539`), not fixable in this project's own code. Redesigned around Claude Code's documented `PreToolUse` `updatedInput` mechanism: `pre_tool_use.py` now silently rewrites a matched `test_commands`/`build_commands` command to append a distinctive exit-code marker to stdout, and `post_tool_use.py` parses that marker back out instead of trusting a structured field. Config format (`test_commands`/`build_commands`, comma-separated substrings) is completely unchanged — no user migration needed. 331 tests passing (up from 324), verified via real subprocess runs at every stage (the rewrite itself, the rewritten command actually executed in a real shell, the resulting real output fed back into the hook) — but the claim that Claude Code actually honors `updatedInput` live has not yet been proven with a real Claude Code session, only researched/documented, and this project has now caught Claude Code's own hook docs wrong twice in one week. Story stays open pending that real-session verification.

### Story 5.9: One-Click Team Dashboard via GitHub Actions

> ✅ **Complete** — built and merged 2026-07-15 on `enhancements-v3` (PR #42, 1343020) — followed directly from a live demo: the user asked to see a real consolidated report across all pilot-test snapshots to date (7 real snapshots manually gathered from 5 different local test folders into one `snapshots/` directory, run through the existing unmodified `metrics-report`/`dashboard` tools — proving zero new code is needed for aggregation, since `snapshots/*.json` is already meant to be committed to git). **Live-verified same day** in `ai-project-metrics-bmad-testing`: a real `workflow_dispatch` run succeeded in 14s and produced a correct downloadable dashboard artifact. Getting there surfaced two real environment gaps, fixed live: `workflow_dispatch` workflows must exist on the repo's *default* branch to be listed/runnable at all (a genuine GitHub platform requirement, not a bug), and that test repo had never actually committed `tools/`/`snapshots/` to any branch across the whole pilot — everything had only ever existed locally.

Ships `.github/workflows/generate-dashboard.yml` in the release artifact — a `workflow_dispatch`-only workflow anyone with repo Write access can trigger with one click from the Actions tab, no local install or code push needed. Runs the same `metrics-report`/`dashboard` tools already documented for local use, uploading the result as a downloadable workflow artifact — deliberately **not** committed to the repo or published anywhere public, preserving Story 5.5's "you decide whether and how to share it" boundary. Optionally gated behind a GitHub Environment (`dashboard-publish`) with required reviewers, a one-time manual Settings step (documented, not automatable without an admin token this tooling never holds) for teams that want approval-gating beyond GitHub's own Write-access baseline. Of the three trigger options discussed with the user (manual local command, CI-on-every-merge, one-click `workflow_dispatch`), only the one-click option was built this story — CI-on-every-merge deliberately deferred to a later story until real team merge cadence is understood.

### Story 5.10: `token_cost.reason` Doesn't Distinguish "Never Closed" From "Closed But Failed"

> ✅ **Complete** — 2026-07-16 · [PR #49](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/49), merged 55480f1. `token_cost_of()` now exposes `sessions_started` alongside `sessions_observed`, and when a story has at least one closed session but also at least one session_start that never got a matching session_end, `reason` names the gap explicitly instead of surfacing an unrelated closed session's own `reasons[0]`. Live-verified by reproducing the exact pilot bug (`story-20260716-ea94fb`) in a scratch repo — the reason changed from the misleading `"no assistant usage data found in transcript"` to `"1 of 3 AI session(s) for this story never sent session_end..."`. Gemini's review raised a false "will revert PR #45's rounding" claim (wrong branch-ancestry premise) and the same long-recurring stale 5-bullet "Unpatched Defects" block — both empirically refuted (`git diff --name-only` + direct grep of the claimed-missing code) before merge.

As someone reading a story's `token_cost`,
I want the surfaced `reason` to reflect what actually happened to the session that did the real work,
so that a null token cost isn't explained by an unrelated, near-empty session's own failure reason.

**Context:** logged as a 🔍 pilot-testing finding (2026-07-16, this epic's blockquote block, formalized into this story now). `token_cost_of()` sums input/output tokens across every `session_end` event for a story; when none carry real token counts, it falls back to `reasons[0]` — the `token_cost_reason` from the chronologically *first* `session_end`. Confirmed live in a real JIRA-flow pilot repo (`D:\mywork\myPOCs\test-metrics\v0.9.3-jira-only`, story `story-20260716-ea94fb`): 3 `session_start` events existed, but only 2 `session_end` events — both from short, empty reconnect blips (`session_ids` `58af4d1c...`'s first ~2-minute life, and `311a6897...`'s ~1-second life). The session that did essentially all the real work (`58af4d1c...`'s second life, 96 of 98 session-tagged events, including the final real commit and a `defect_review` event) never sent `session_end` at all — the already-documented VS Code "x"-button `SessionEnd` gap (see `INSTALL.md`'s "Known limitations"). The displayed reason (`"no assistant usage data found in transcript"`) was technically accurate for the blip session it came from, but misleading about the real work session's fate.

**Acceptance Criteria (draft):**

1. **Given** a story where every `session_start` has a matching `session_end`, and none of them yield real token counts
   **When** the assembler computes `token_cost`
   **Then** `reason` is unchanged from today — `reasons[0]` from the closed sessions (no regression to the already-tested Story 5.2/5.6 behavior)
2. **Given** a story where zero `session_end` events exist at all
   **When** the assembler computes `token_cost`
   **Then** `reason` is unchanged from today — `"no AI session_end event observed for this story"` (no regression to Story 5.6)
3. **Given** a story where at least one `session_end` exists (so the zero-session_end case above doesn't apply) but the count of `ai.<tool>.session_start` events exceeds the count of `session_end` events
   **When** the assembler computes `token_cost`
   **Then** `reason` explicitly says N of M sessions never sent `session_end`, rather than surfacing an unrelated closed session's own `reasons[0]`
4. **Given** any story
   **When** the assembler computes `token_cost`
   **Then** the returned dict also exposes a `sessions_started` count (alongside the existing `sessions_observed`) so the gap between "sessions that began" and "sessions that cleanly ended" is visible directly in the snapshot, not just inferable from the reason text
5. **Given** this fix
   **When** `INSTALL.md`'s "Known limitations" section is reviewed
   **Then** it gets one sentence noting `token_cost.reason` now distinguishes an unclosed session from a closed-but-failed one, and that `sessions_started`/`sessions_observed` together show the gap

### Story 5.11: Snapshot and Report Fields Explain Their Own Purpose

> ✅ **Complete** — 2026-07-16 · [PR #50](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/50), merged 3e23f82. New `tools/hooks/_field_guide.py` holds one shared, static dict of field purpose + calculation, bridge-imported the same way `_events.py` already is by three consumers: the snapshot JSON gets a `field_guide` section (real and `--dry-run`), the markdown report gets a "Field Guide" appendix, and the dashboard gets native `title=""` tooltips on headers/stat tiles. Built in parallel with Story 5.10 off `main`; after PR #49 merged first, `main` was merged into this branch and a flagged one-entry follow-up (`FIELD_GUIDE["token_cost.sessions_started"]`) closed the resulting gap before this PR merged. Gemini's review repeated the same false "will revert PR #45's rounding" claim seen on PR #49 — refuted the same way (direct grep of the merged branch), and self-contradicted by its own "Positive Findings" section acknowledging `sessions_started` was already integrated. Live-verified across all three tools (assembler → metrics-report → dashboard) in a real scratch repo.

As someone reading a generated snapshot, markdown report, or dashboard,
I want each field to explain what it means and how it's calculated right next to where I'm reading it,
so that I don't have to go find `tools/snapshot-assembler/main.py`'s docstrings or `INSTALL.md` every time I get confused.

**Context:** logged as a 🔍 pilot-testing finding (2026-07-16, this epic's blockquote block, formalized into this story now). Field explanations today live only in code docstrings and `INSTALL.md`'s prose — neither is visible from the actual artifacts a developer or leadership reader looks at day to day (`snapshots/*.json`, `metrics-reports/*.md`, `dashboard.html`). Recurring confusion reported live during pilot testing over fields like `story_point_cost.phase1_points`/`phase2_points`/`variance`, `token_cost.sessions_observed` vs. `engineering_metrics.ai_sessions`, and `estimated_cost.duration_minutes`'s active-time-vs-raw-span distinction.

**Acceptance Criteria (draft):**

1. **Given** a single shared, static field-descriptions source (one dotted-path-keyed dict, covering every field currently emitted by the six snapshot sections)
   **When** it's authored
   **Then** each description states both the field's purpose and — where the value is computed rather than copied verbatim from a source system — a one-line summary of the calculation, in plain language a non-author can follow
2. **Given** the snapshot assembler writes a snapshot (real or `--dry-run`)
   **When** the JSON is produced
   **Then** it includes a `field_guide` section (sourced from the shared descriptions in AC1) directly in the snapshot itself — no external doc lookup needed to understand any field in the file you're already looking at
3. **Given** `tools/metrics-report/main.py` generates a `metrics-<date>.md` file
   **When** the report is rendered
   **Then** it includes a "Field Guide" appendix (sourced from the same shared descriptions) explaining every field that appears in each story's block above it
4. **Given** `tools/dashboard/main.py` generates `dashboard.html`
   **When** the table/stat-tiles are rendered
   **Then** each column header and stat tile carries a hover tooltip (sourced from the same shared descriptions) explaining that field — no separate legend page needed, and no new script/CDN dependency introduced
5. **Given** this story only adds documentation-carrying fields/attributes
   **When** existing consumers (tests, other tools) read a snapshot
   **Then** nothing that reads specific data fields today breaks — `field_guide` is strictly additive, same precedent as `estimated_cost`/`defect_metrics` being added without a `schema_version` bump

---

## Epic 6: JIRA Ticket Lifecycle Sync

A JIRA-backed story's ticket reflects real progress automatically — moves to "In Progress" at kickoff, "Done" at close, and carries back real story-point estimates — without any manual JIRA click.

> 🆕 **Opened 2026-07-17** — inspired by directly reading a reference tool's own docs (`D:\mywork\myPOCs\mcp-google-stitch\docs\engineering_flow.md`, `developer_handover.md`, and a real completed-ticket walkthrough) after the user recalled discussing this idea in personal notes never actually shared with this assistant before. Confirmed via that reference material: real JIRA status transitions at both start (`POST /issue/{key}/transitions` → In Progress) and close (→ Done), plus a story-points value set on every defect sub-task and synced back to the parent ticket at close (`PUT` to the parent issue). This project currently does none of that — kickoff only ever *reads* JIRA fields, and Story 5.4's defect sub-tasks carry no points value at all.
>
> **Explicitly out of scope, confirmed with the user:** bulk backlog/ticket creation from a PRD (a fundamentally different product surface — PM-authoring vs. this project's "metrics as a byproduct" mission); Confluence-side status/points sync (pages have no workflow-status concept, and the MCP server already can't write labels back — a separate, already-documented gap, see Story 1.10's Known Limitations note); the reference tool's "save telemetry JSON to a JIRA issue entity property" idea (a nice-to-have, not in this batch).
>
> **A real architecture constraint this surfaces:** MCP tools are only reachable from a live assistant turn, never from a hook/CLI subprocess — the same constraint Story 5.4 already documented for defect sub-task creation. Kickoff is already a skill (assistant turn), so the "In Progress" transition fits naturally there (Story 6.1). But *closing* a story today is a pure CLI command (`tools/snapshot-assembler/main.py` / `tools/opsx-wrapper/main.py archive`), which cannot reach MCP tools on its own — the "Done" transition needs a new conversational step wrapping the existing close command, not a change to the script itself (Story 6.2).
>
> **Two design decisions confirmed with the user before formalizing this epic:** (1) Story 6.4 writes back `story_point_cost.phase2_points` (this project's own after-the-fact computed estimate), not the developer-confirmed `pm_metrics.points` and not an at-close developer prompt — the user chose the recommended option. (2) Story 6.2's close-time step is a **new dedicated skill** (mirroring `story-kickoff`'s own structure), not an extension of the existing kickoff skill into a combined one — also the recommended option.

### Story 6.1: Kickoff Transitions the JIRA Issue to "In Progress"

As a developer kicking off a JIRA-backed story,
I want the ticket to automatically move to "In Progress" the moment I start work,
so that the board reflects reality without a manual JIRA click.

**Acceptance Criteria (draft):**

1. **Given** `source_of_truth: jira` and a successful kickoff fetch (`story-kickoff/SKILL.md` step 4a, MCP or script fallback)
   **When** the manifest is about to be written
   **Then** the skill resolves the issue's available transitions (`getTransitionsForJiraIssue`), matches the "In Progress"-equivalent one, and calls `transitionJiraIssue` for that issue key
2. **Given** a JIRA workflow that doesn't literally call its active-work state "In Progress" (workflow schemes vary across projects)
   **When** matching a transition
   **Then** match case-insensitively against a small allow-list of common names ("In Progress", "In Development", "Doing"), with a `.story-config.yaml` override (`jira_in_progress_transition`) if auto-match fails or the project wants a specific one
3. **Given** the transition fails for any reason (no matching state found, permission denied, issue already in that state)
   **When** kickoff continues
   **Then** kickoff is never blocked (FR5, same non-blocking philosophy as every other degradation in this skill) — tell the developer plainly what happened and proceed with the rest of kickoff exactly as if this story didn't exist
4. **Given** `source_of_truth: confluence` or `docs-only`
   **When** kickoff runs
   **Then** nothing changes — no transition is attempted (Confluence pages have no workflow-status concept; docs-only has no ticket at all)

### Story 6.2: A New "Close Story" Skill Wraps Transition-to-Done + the Existing Archiver

As a developer finishing a JIRA-backed story,
I want the ticket to automatically move to "Done" when I close the story,
so that I don't have to separately update JIRA by hand.

**Context:** closing a story today is a pure CLI command with no MCP access (see this epic's architecture-constraint note above). This story introduces a new, small skill — analogous to `story-kickoff` — that a developer invokes conversationally (e.g. "close this story") to wrap the existing close command with a JIRA transition step for JIRA-backed stories.

**Acceptance Criteria (draft):**

1. **Given** `source_of_truth: jira`
   **When** the developer invokes the new close skill
   **Then** it transitions the issue to a Done-equivalent state via MCP **before** invoking the existing close command (`tools/opsx-wrapper/main.py archive <name>` or `tools/snapshot-assembler/main.py --repo-root .`) — this ordering is deliberate: a failed archive run must never leave the ticket falsely marked Done
2. **Given** the transition fails (no matching state, permission denied)
   **When** the close skill continues
   **Then** same non-blocking philosophy as Story 6.1 — warn plainly, then still run the archiver so the developer isn't blocked from closing their story just because the JIRA-side write failed
3. **Given** `source_of_truth: confluence` or `docs-only`
   **When** the developer invokes the close skill
   **Then** it's a pure passthrough to today's close command — no new behavior, nothing to transition
4. **Given** this is a brand-new skill, not a modification of `story-kickoff`
   **When** it's built
   **Then** it reuses existing helpers (manifest reading, `.story-config.yaml` reading) rather than duplicating them — exact code-sharing mechanism to be resolved during `create-story`

### Story 6.3: Defect Sub-tasks Carry a Story-Points Value

As a JIRA board viewer,
I want each defect sub-task to carry a small point estimate,
so that sub-tasks show up realistically in JIRA reporting rather than as unestimated.

**Context:** Story 5.4 already creates a JIRA Subtask for review defects via MCP (`createJiraIssue`) but never sets a points value on it. The reference tool always sets one (defaulting to 1, override-able).

**Acceptance Criteria (draft):**

1. **Given** a review defect is logged for a JIRA-backed story (Story 5.4's existing flow)
   **When** the subtask is created
   **Then** the create call includes a story-points value on the subtask, defaulting to **1**, using the same `jira_points_field` config key already used for reading points at kickoff (no new config key introduced)
2. **Given** compile/test defects
   **When** they're captured
   **Then** nothing changes — still local-only, still the explicit non-goal Story 5.4 already documented (hooks can't reach MCP)

### Story 6.4: Parent Ticket's Story Points Sync Back at Close

As someone viewing the JIRA board,
I want the ticket's points field to reflect what was actually estimated by the end of the story,
so that JIRA isn't left showing a stale pre-work guess.

**Acceptance Criteria (draft):**

1. **Given** `source_of_truth: jira` and the close-time MCP step introduced by Story 6.2
   **When** the story closes
   **Then** `story_point_cost.phase2_points` (this project's own after-the-fact computed estimate, Story 2.6) is written back to the issue's points field via `editJiraIssue` — **not** `pm_metrics.points` and **not** an at-close developer prompt (decided with the user when this epic was scoped)
2. **Given** `phase2_points` is null for any reason
   **When** the close-time sync runs
   **Then** it skips the write entirely rather than writing a null/zero (AD-10 null-with-reason philosophy, applied here to an outbound write instead of a snapshot field)
3. **Given** the write fails (permission denied, custom field misconfigured)
   **When** the close skill continues
   **Then** same non-blocking philosophy as Stories 6.1/6.2 — warn plainly, still complete the close
