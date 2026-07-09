---
stepsCompleted: [step-01, step-02, step-03, step-04, step-05, step-06]
documentsIncluded:
  prd_equivalent: '_bmad-output/specs/spec-pm-metrics-ai-engineering-flow/SPEC.md'
  architecture: '_bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md'
  epics: '_bmad-output/planning-artifacts/epics.md'
  ux: null
---

# Implementation Readiness Assessment Report

**Date:** 2026-07-09
**Project:** explore-jira-ai-metrics

## Document Inventory

| Document Type | Status | Path |
| --- | --- | --- |
| PRD (equivalent) | Found — `bmad-spec` alternate path used instead of a PRD | `_bmad-output/specs/spec-pm-metrics-ai-engineering-flow/SPEC.md` |
| Architecture | Found, whole document, no duplicates | `_bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md` |
| Epics & Stories | Found, whole document, no duplicates | `_bmad-output/planning-artifacts/epics.md` |
| UX Design | Not present — no UX phase run for this project (confirmed not applicable) | — |

No duplicate whole/sharded document conflicts found. User confirmed `SPEC.md` stands in for the PRD in this assessment.

## PRD Analysis (SPEC.md substituted)

### Functional Requirements Extracted

FR1: A story's PM, engineering, story-point-cost, and token-cost metrics are captured automatically as a byproduct of the dev flow, without the developer re-reporting status or effort. (CAP-1)
FR2: A story's points are estimated automatically at kickoff and reconciled against actuals at close, using defined rules (AD-6), with variance logged rather than overwritten. (CAP-2)
FR3: The system attributes active working time to the correct story as a developer moves between stories, without a manual time-log entry. (CAP-3)
FR4: The kickoff flow adapts its questions and data source to whatever project-management tool (or lack of one) a given project actually uses. (CAP-4)
FR5: The full metrics-capture pipeline runs uniformly for stories of every complexity; complexity classification at kickoff feeds only the Phase-1 point estimate, never a capture on/off decision. (CAP-5)
FR6: Per-story snapshots are producible in a stable, versioned shape that a future central presentation layer can consume without needing raw capture-side event detail. (CAP-6)
FR7: The capture side supports a normalized AI-tool adapter interface so tools other than Claude Code can be added later without redesigning event integrity or the reconciliation formula; only the Claude Code adapter is implemented now. (CAP-7)

Total FRs: 7

### Non-Functional Requirements Extracted

NFR1: No modification of openspec/speckit internals; all interception is external (CLI wrapping, git hooks, Claude Code hooks) since no plugin/extension API exists.
NFR2: Capture must work fully offline / local-first — no producer depends on network availability or a running background service (AD-2).
NFR3: Only a versioned snapshot ever crosses the local-to-central boundary; the raw event log never leaves the developer's machine (AD-3, AD-3a).
NFR4: Adapter credentials (JIRA/Confluence tokens) must never be written into `.story.yaml`, the event log, or any snapshot (AD-4).
NFR5: Branch-per-story is assumed as a hard team convention for time attribution; no per-story time tracking is defined if violated (AD-7, confirmed).
NFR6: A hook that fails to append an event retries up to 3 times, then surfaces a visible error to the developer; it never fails silently (AD-9).
NFR7: An AI-tool field a producer cannot report (e.g. token cost on Copilot) must be emitted as null-with-reason, never defaulted to zero (AD-10).

Total NFRs: 7

### Additional Requirements

- **Non-goals (explicit scope exclusions):** building the central presentation layer/BI tool itself; time attribution when branch-per-story is violated; recalibrating AD-6 weight tables from captured variance; building AI-tool adapters beyond Claude Code (Cursor, Copilot, Gemini); a GitLab source-of-truth adapter (held for later, per user).
- **Assumptions:** a developer focuses on one story at a time; the AD-6 scoring tables are an unvalidated best-guess starting point, pilot-first calibration planned; sanctioned data use is billing justification and process improvement only, never individual performance review.
- **Open questions:** adapter credential provisioning mechanics not designed; central-service/BI-tool technology not yet chosen (no urgency); GitLab adapter held for later.

### PRD (SPEC.md) Completeness Assessment

SPEC.md is complete and internally consistent for its purpose: every capability (CAP-1–7) has both an intent and a testable success criterion, constraints are load-bearing (each rules out a real design choice), 3 explicit non-goals exist, and the success signal is concrete and demonstrable. Assumptions and open questions are both explicitly logged rather than silently resolved. No gaps found at the requirements level.

## Epic Coverage Validation

### Coverage Matrix — Functional Requirements

| FR | Requirement | Epic Coverage | Status |
| --- | --- | --- | --- |
| FR1 | Automatic PM/engineering/cost/token capture | Epic 2, Stories 2.2–2.4 | Covered |
| FR2 | Two-phase story-point estimation + reconciliation | Epic 2, Stories 2.5–2.6 | Covered |
| FR3 | Active-story time attribution | Epic 3, Stories 3.1–3.3 | Covered |
| FR4 | Source-of-truth adapter (kickoff) | Epic 1, Stories 1.1–1.4 | Covered |
| FR5 | Complexity feeds estimate only, never a capture on/off gate | Epic 2, Story 2.5 | Covered |
| FR6 | Stable, versioned snapshot shape | Epic 2, Story 2.4 | Covered |
| FR7 | AI-tool adapter interface | Epic 2, Story 2.3 | **Partially covered** |

### Coverage Matrix — Non-Functional / Additional Requirements

| Requirement | Epic Coverage | Status |
| --- | --- | --- |
| NFR1 (no openspec/speckit modification) | Satisfied by design; no explicit AC | Structurally covered |
| NFR2 (offline/local-first) | Satisfied by design; no explicit AC | Structurally covered |
| NFR3 (snapshot-only boundary) | Story 2.4; no explicit AC for "raw log never leaves machine" | Structurally covered |
| NFR4 (credentials never persisted) | Epic 1, Stories 1.3–1.4 | Covered |
| NFR5 (branch-per-story convention) | Epic 3, Story 3.1 | Covered |
| AD-9 (retry-then-surface) | Epic 2, Stories 2.2–2.3 | Covered |
| AD-10 (null-with-reason) | Epic 2, Story 2.3 | Covered |

### Missing Requirements

**High Priority — FR7 / AD-10: the kickoff manifest's `ai_tool` field is never created by any story.** AD-10 specifies `.story.yaml` carries an `ai_tool` field declared like `source_of_truth`. Epic 1 (Stories 1.1–1.4) only covers `source_of_truth`; no story sets `ai_tool`. Story 2.3 covers the capture-side consequence but assumes the field already exists — Story 2.3 currently has nothing to read to know which adapter to activate.
- **Recommendation:** Add a story to Epic 1 (e.g., Story 1.5: "Kickoff Manifest Declares Which AI Tool Is In Use") mirroring Story 1.2's pattern, or fold it into Story 1.2's acceptance criteria.

**Minor observation (non-blocking):** NFR1–NFR3 are satisfied by the overall design but have no explicit testable AC in any single story. Not a coverage gap today, but worth keeping in mind during Epic 2 implementation since they're easy to accidentally violate.

### Coverage Statistics

- Total FRs: 7
- Fully covered: 6
- Partially covered: 1 (FR7 — capture side covered, manifest-field declaration missing)

## UX Alignment Assessment

### UX Document Status

Not Found

### Alignment Issues

None — not applicable. This project is developer tooling (git hooks, Claude Code hooks, a CLI wrapper, two terminal-based skills), not a rendered UI. Neither `SPEC.md` nor `ARCHITECTURE-SPINE.md` describes any screen, page, or visual component. The eventual central presentation layer (dashboard) is explicitly deferred and out of scope for this epic breakdown.

### Warnings

None. A UX pass would become relevant only if/when the deferred central presentation layer is picked up in a future phase.

## Epic Quality Review

### User Value Focus Check

All three epic titles/goals are user-centric outcomes, not technical milestones. Pass.

### Epic Independence Validation

- Epic 1 stands alone completely.
- Epic 2 depends only on Epic 1's manifest (a previous epic); no story references Epic 3.
- Epic 3 depends only on Epic 1's manifest + Epic 2 Story 2.1 (previous); no story references Epic 2 Stories 2.2–2.6.

No epic independence violations found.

### Within-Epic Story Dependency Check

Walked every story's AC for forward references: Epic 1 (1.2→1.1, 1.3→1.2, 1.4→1.2, all backward), Epic 2 (2.2→2.1, 2.3→2.1, 2.4→2.2+2.3, 2.6→2.2-2.4+2.5, all backward; 2.5 has no within-epic dependency), Epic 3 (3.1→2.1, 3.2→3.1, 3.3→3.1, all backward).

No forward dependencies found.

### Acceptance Criteria Review

- 🟡 Minor — Story 1.1: no AC covers the missing-input/validation error path at kickoff.
- 🟡 Minor — Story 3.2: idle-timeout AC says "~15 minutes" (approximate); should be an exact, configurable threshold for testability.
- 🟡 Minor — Sequencing observation: hook installation (Story 2.1) lands in Epic 2, not Epic 1. Not a violation (Epic 1's docs-only kickoff doesn't need hooks), but worth noting explicitly in sprint planning that the real Day 1 developer sequence spans both epics.

### Database/Entity & Starter Template Checks

Local files are each created only by the story that first needs them. No starter template specified in the architecture — not applicable.

### Findings Summary

- Critical Violations: None
- Major Issues: None beyond the FR7/AD-10 manifest-field gap already flagged in Epic Coverage Validation
- Minor Concerns: 3 (see Acceptance Criteria Review above)

## Summary and Recommendations

### Overall Readiness Status

NEEDS MINOR WORK

### Critical Issues Requiring Immediate Action

None. No critical or major violations were found across document discovery, requirements coverage, UX alignment, or epic/story quality.

### Issues Requiring Attention Before Implementation

1. FR7/AD-10 gap: no story creates the `.story.yaml` `ai_tool` field that Story 2.3 assumes already exists. Add Story 1.5 (or fold into Story 1.2's AC) before Epic 2 implementation begins.
2. Minor AC gaps: Story 1.1 lacks an error/validation path for missing kickoff inputs; Story 3.2's idle-timeout AC should state an exact threshold, not "~15 minutes."
3. Sequencing note: confirm in sprint planning that a developer's Day 1 setup spans Epic 1 (kickoff config) and Epic 2 Story 2.1 (hook install).

### Recommended Next Steps

1. Add the missing `ai_tool` manifest story/AC to Epic 1.
2. Tighten Story 1.1 and Story 3.2's acceptance criteria per the notes above.
3. Proceed to `bmad-sprint-planning` once the above is addressed — everything else is implementation-ready as-is.

### Final Note

This assessment identified 1 high-priority coverage gap and 3 minor concerns across 5 review categories (document discovery, PRD/spec analysis, epic coverage, UX alignment, epic quality). None are blocking in the sense of requiring a redesign. Address them now, or proceed to sprint planning as-is and fix them when Epic 1/2 implementation reaches those stories.

## Resolution Update (2026-07-09)

All 4 findings from this assessment were fixed in `epics.md` immediately after this report was generated:

1. **FR7/AD-10 gap — resolved.** Added **Story 1.5: Kickoff Manifest Declares Which AI Tool Is In Use** to Epic 1, mirroring Story 1.2's pattern. `.story.yaml` now gets an `ai_tool` field the same way it gets `source_of_truth`; Story 2.3 has something to read. FR coverage map updated: FR7 now spans Epic 1 (manifest field) and Epic 2 (capture).
2. **Story 1.1 AC gap — resolved.** Added an explicit re-prompt-on-missing-input criterion.
3. **Story 3.2 AC imprecision — resolved.** Idle threshold changed from "~15 minutes" to an exact, configurable default (15 minutes).
4. **Sequencing note — acknowledged**, no document change needed; carried forward as guidance for sprint planning (Day 1 developer setup spans Epic 1 + Epic 2 Story 2.1).

**Revised Overall Readiness Status: READY** — all identified gaps closed; no remaining blockers before `bmad-sprint-planning`.

## Addendum: A Gap in This Review's Own Coverage (2026-07-09)

After this assessment closed, the user asked what tech stack had been decided and why it wasn't flagged here. Worth recording honestly: **it wasn't caught because this skill's checklist doesn't check for it.**

Step 5 (Epic Quality Review) checks specifically for a *starter template* ("does Architecture specify a starter/greenfield template? If yes, Epic 1 Story 1 must set it up"). That's a narrower, different question than "does the Stack section actually name a concrete implementation language/runtime." Since this project has no starter template, that check correctly returned N/A — but no step in this workflow asks the broader question. `ARCHITECTURE-SPINE.md`'s Stack table named *mechanisms* (git hooks, Claude Code hook config, CLI-wrapping) without ever pinning a language, and this assessment passed that through without comment.

**Consequence:** the READY verdict above was accurate for everything this skill actually checks, but not fully exhaustive — a dev agent starting Story 2.1 without the follow-up conversation would have hit "wait, what language?" as a real blocker despite the report saying READY.

**Resolution:** the gap was closed via a follow-up architecture decision — **Python 3.8+ via `uv run`** for all hook logic, the CLI wrapper, and the snapshot assembler, ratifying the existing `_bmad/scripts/*.py` convention in this repo. `ARCHITECTURE-SPINE.md`'s Stack table and Structural Seed, and `epics.md`'s Additional Requirements, were updated accordingly (see their memlogs, 2026-07-09).

**Process note for future runs of `bmad-check-implementation-readiness` on this or other projects:** consider explicitly verifying the Architecture document's Stack/tech-decisions section is populated with concrete, buildable choices — not just mechanism names — as part of Step 5, alongside the existing starter-template check.
