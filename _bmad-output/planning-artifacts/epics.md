---
stepsCompleted: [step-01]
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
| FR6 (CAP-6) | Epic 3 |
| NFR1 | Epic 2 |
| NFR2 | Epic 2, Epic 3 |
| NFR3 | Epic 3 |
| NFR4 | Epic 1 |
| NFR5 | Epic 5 |

## Epic List

1. Epic 1: Project Onboarding & Kickoff Bookend
2. Epic 2: Local Capture Substrate (Manifest, Event Log, Hooks)
3. Epic 3: Snapshot Assembly & Close Trigger
4. Epic 4: Story-Point Estimation & Reconciliation
5. Epic 5: Active-Story Time Attribution
