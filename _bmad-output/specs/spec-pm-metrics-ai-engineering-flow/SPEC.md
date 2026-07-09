---
id: SPEC-pm-metrics-ai-engineering-flow
companions: ['../../planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md']
sources: ['../../brainstorming/brainstorm-pm-metrics-ai-engineering-flow-2026-07-01/brainstorm-intent.md']
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# PM Metrics as a Byproduct of the AI-Accelerated Engineering Flow

## Why

AI/LLM-accelerated engineering (openspec/speckit, SDD-driven development) now moves faster and less predictably than manual project-management tracking can follow — a pain actively blocking project leads today. Developers using AI tooling deliver quickly, but sprint metrics (committed/delivered stories, points, velocity, start/end dates) still depend on manual entry that lags the real work and burdens developers with double-entry. This spec exists to capture PM, engineering, cost, and token metrics automatically as a byproduct of the existing dev flow, so leadership gets a reliable per-story, per-developer, and per-project dashboard without adding developer overhead.

## Capabilities

- **CAP-1**
  - **intent:** A story's PM, engineering, story-point-cost, and token-cost metrics are captured automatically as a byproduct of the dev flow, without the developer re-reporting status or effort.
  - **success:** At `opsx archive`, a versioned metrics snapshot exists for the story with all four metric families populated, with zero manual PM data entry beyond the two kickoff fields (points confirmation, goal/sprint).

- **CAP-2**
  - **intent:** A story's points are estimated automatically at kickoff and reconciled against actuals at close, using defined rules (architecture spine AD-6) rather than manual entry.
  - **success:** Every archived story has both a Phase-1 estimate and a Phase-2 actual figure logged, plus their variance; neither is ever silently overwritten.

- **CAP-3**
  - **intent:** The system attributes active working time to the correct story as a developer moves between stories, without a manual time-log entry.
  - **success:** Closing a story yields a summed active-time figure built from automatically opened/closed time slices (AD-7), matching the developer's actual branch/session activity.

- **CAP-4**
  - **intent:** The kickoff flow adapts its questions and data source to whatever project-management tool (or lack of one) a given project actually uses.
  - **success:** A project declares `source_of_truth` once (`jira` | `confluence` | `docs-only`), and the kickoff skill never asks which backend applies on a per-story basis (AD-4).

- **CAP-5**
  - **intent:** The full metrics-capture pipeline runs uniformly for stories of every complexity — since capture is silent and near-zero-effort, no story is exempted, which removes any incentive to under-classify a story to dodge tracking.
  - **success:** Full A+B+C capture runs for every story regardless of the LLM-classified complexity at kickoff (task count + volatility, AD-6); complexity classification feeds only the Phase-1 point estimate, never a capture on/off decision.

- **CAP-6**
  - **intent:** Per-story snapshots are producible in a stable, versioned shape that a future central presentation layer can consume without needing to understand raw capture-side event detail.
  - **success:** `opsx archive` produces an immutable, schema-versioned snapshot (AD-3, AD-3a) that leadership can eventually roll up per developer and per project, including a token-cost-per-story-point trend.

- **CAP-7**
  - **intent:** The capture side can be extended to AI tools other than Claude Code (Cursor, Copilot, Gemini, etc.) via a normalized AI-tool adapter, without redesigning event integrity or the reconciliation formula.
  - **success:** A new AI-tool adapter can be added that emits the AD-10 normalized shape under its own `ai.<tool>.*` namespace, and AD-6 Phase-2 reconciliation degrades to reduced-confidence rather than breaking when that tool cannot supply decision-narration or token-cost signals.

## Constraints

- No modification of openspec/speckit internals; all interception is external (CLI wrapping, git hooks, Claude Code hooks) since no plugin/extension API exists.
- Capture must work fully offline / local-first: no producer depends on network availability or a running background service (AD-2).
- Only a versioned snapshot ever crosses the local-to-central boundary; the raw event log never leaves the developer's machine (AD-3).
- Adapter credentials (JIRA/Confluence tokens) must never be written into `.story.yaml`, the event log, or any snapshot (AD-4).
- Branch-per-story is assumed as a hard team convention for time attribution; no per-story time tracking is defined if violated (AD-7, confirmed).
- A hook that fails to append an event retries up to 3 times, then surfaces a visible error to the developer; it never fails silently (AD-9).
- An AI-tool field a producer cannot report (e.g. token cost on Copilot) must be emitted as null-with-reason, never defaulted to zero (AD-10).

## Non-goals

- Building or selecting the central presentation layer/BI tool itself — only its input contract (the versioned snapshot) is fixed here.
- Time attribution when a developer works multiple stories on a single branch (violating branch-per-story) — no manual-override path is designed.
- Recalibrating the AD-6 story-point weight tables based on captured variance data — variance is only captured/logged in this spec, not acted on.
- Building AI-tool adapters for tools other than Claude Code — AD-10 fixes the adapter boundary, but only the Claude Code adapter is built; Cursor, Copilot, Gemini, etc. are out of scope for the pilot.

## Success signal

A project lead can, at any time after a story's `opsx archive`, view a complete PM/engineering/cost/token metrics record for that story — including estimated vs. actual points and active time-on-task — with the developer having done nothing beyond the two kickoff bookend inputs and their normal git/AI workflow.

## Assumptions

- A developer focuses on one story at a time, per the confirmed branch-per-story convention; general multi-tasking time-attribution was explicitly deferred by the user.
- The AD-6 story-point scoring tables (seeded from an existing internal reference document) are usable as a starting point even though the user confirmed they are an unvalidated best guess; a pilot rollout with a small developer group is planned to tweak the formula before wider rollout.
- Sanctioned uses of this data are billing justification and process improvement; not staffing decisions or individual performance review.

## Open Questions

- Adapter credential provisioning mechanics (how a developer's JIRA/Confluence token first gets into their environment) are not designed.
- Central-service/BI-tool technology, hosting, and environment topology are not yet chosen; user confirmed no urgency yet.
- Now resolved: yes — the kickoff manifest carries an `ai_tool` field (AD-10), declared like `source_of_truth`. Remaining open question is *when* to build adapters for tools beyond Claude Code, not *whether* the boundary exists.
- Held for later: a fourth source-of-truth adapter for GitLab, alongside JIRA/Confluence/docs-only (AD-4/CAP-4). Not in scope now; add only if real demand emerges.
