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
| FR2 (CAP-2) | Epic 4 |
| FR3 (CAP-3) | Epic 5 |
| FR4 (CAP-4) | Epic 1 |
| FR5 (CAP-5) | Epic 1 |
| FR6 (CAP-6) | Epic 2 |
| FR7 (CAP-7) | Epic 1 (manifest field), Epic 2 (capture) |
| NFR1 | Epic 2 |
| NFR2 | Epic 2 |
| NFR3 | Epic 2 |
| NFR4 | Epic 1 |
| NFR5 | Epic 3 |

## Epic List

1. Epic 1: Start a Story With Zero Manual PM Setup
2. Epic 2: Metrics Appear Automatically When You Close a Story
3. Epic 3: Time Tracked Without Logging Hours

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

As a developer,
I want switching story branches mid-AI-session to not corrupt time totals,
So that my time attribution stays accurate even when I context-switch quickly.

**Acceptance Criteria:**

**Given** a live Claude Code session (Story 3.1)
**When** a `git checkout` happens mid-session
**Then** the live session's `SessionStart`/`SessionEnd` boundaries govern time-slice accounting
**And** the checkout re-points which story current activity counts toward, without itself opening or closing a session-level slice (AD-7 precedence rule)
