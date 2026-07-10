---
baseline_commit: 48658bed39178b337c7f5194dcbe6fcb2d81e15a
---

# Story 2.5: Story Points Are Estimated Automatically at Kickoff

Status: review

## Story

As a developer,
I want my story's points estimated automatically from its scope and complexity,
so that I don't have to guess a number myself.

## Acceptance Criteria

1. **Given** a story at kickoff, **when** the Phase-1 formula runs, **then** it computes base points from task count in `tasks.md`, plus a volatility bonus from openspec stage maturity, plus a novelty modifier from pattern-matching prior story records (AD-6).
2. The resulting complexity classification feeds **only** this point estimate, never a capture on/off decision (FR5) — nothing about the estimate may gate, skip, or reduce any capture behavior in this or any other component.

## Tasks / Subtasks

- [x] Task 1: Phase-1 estimator `tools/estimate-phase1/main.py` (AC: 1)
  - [x] CLI: `--repo-root DIR` (required), `--change-dir DIR` (optional override, relative or absolute)
  - [x] **Change discovery (user-approved, no CLI dependency — NFR2 local-first):** if `--change-dir` given, use it verbatim (must contain `tasks.md` else exit 2). Else scan `{repo-root}/openspec/changes/*/` for subdirectories: zero found → `phase1_points: null` with `phase1_points_reason: "no openspec change found — task count unknowable"` (honest null, AD-10-style — estimation degrades, capture never does, AC 2); exactly one found → auto-select it; two or more found → exit 2 naming them, requiring `--change-dir`
  - [x] **Task count:** count lines matching `- [ ]` or `- [x]` (any checkbox state — total scope, not remaining work) in the selected change's `tasks.md`; missing `tasks.md` in an otherwise-found change dir → same null-with-reason path as "no change found"
  - [x] **Base points (AD-6 buckets, deterministic edges — Fibonacci-aligned):** 1–5 tasks → 2; 6–15 → 5; 16–30 → 13; 31+ → 20 with `must_split: true` (informational flag only — never blocks, never gates capture, per AC 2)
  - [x] **Volatility bonus:** count how many of `{proposal.md, design.md, specs/}` exist (non-empty) under the change dir; `bonus = round(5 * (3 - present_count) / 3)` → 0 present → 5, 1 → 3, 2 → 2, 3 (all) → 0. This linear rule is this story's own deterministic fill between AD-6's two stated endpoints (`/opsx:explore`-only = +5, proposal+specs+design = 0) — document it as such in the module docstring, it is not copied from anywhere
  - [x] **Novelty modifier (reinterpreted source — see Dev Notes):** since `.story.yaml` itself never persists across stories (AD-5 refuses overwrite; nothing yet clears it after archive — a pre-existing gap, out of scope here), pattern-match against the `pm_metrics` of every committed `snapshots/*.json` in the repo instead: zero prior snapshots anywhere → `×1.5` (first-time); prior snapshots exist but none share this kickoff's `source_of_truth` → `×1.0` (standard); at least one prior snapshot shares both `source_of_truth` AND the same base-points bucket as this estimate → `×0.8` (existing-pattern-reuse)
  - [x] **Combine:** `phase1_points = round((base_points + volatility_bonus) * novelty_modifier)` (order per the epic text's "base ...; plus volatility ...; times novelty"); round half up to nearest integer
  - [x] Ack (one JSON line, exit 0 on the normal and null-degraded paths; exit 2 only for ambiguous multi-change or bad `--repo-root`/explicit `--change-dir`): `{ok, phase1_points, phase1_points_reason, task_count, base_points, volatility_bonus, novelty_modifier, must_split, change_dir}` — every field present even when `phase1_points` is null
- [x] Task 2: `story-kickoff` SKILL.md wiring (AC: 1, 2)
  - [x] New step between "resolve source of truth" (step 1) and the three-field elicitation (step 3/3a/3b): run the estimator; if it returns a non-null `phase1_points`, present it to the developer as a **suggested** points value ("Phase-1 estimate: N points — accept or override?"); if null, tell the developer why (surface `phase1_points_reason`) and fall back to a plain ask, exactly as today
  - [x] The estimate is *never* silently written — the developer's confirmed value (accepted or overridden) is what goes to `--points` on the writer, preserving the existing re-prompt rule and CAP-1's human-confirmation guarantee verbatim
  - [x] Explicitly state in the skill: a null/degraded estimate, a `must_split` flag, or any estimator error must never skip, shorten, or disable capture for this story (AC 2) — the kickoff flow continues exactly as before regardless of what the estimator returns
- [x] Task 3: Tests `tests/estimate_phase1/test_estimate.py` (AC: 1, 2)
  - [x] Base-point boundaries (§6): task counts 5/6, 15/16, 30/31 → 2/5, 5/13, 13/20+`must_split`
  - [x] Volatility: 0/1/2/3 of `{proposal.md, design.md, specs/}` present → 5/3/2/0
  - [x] Novelty: no snapshots dir/empty → ×1.5; snapshots exist with a different `source_of_truth` → ×1.0; snapshot exists with same `source_of_truth` and same base-points bucket → ×0.8
  - [x] Change discovery: zero `openspec/changes/*` dirs → null+reason, exit 0; exactly one → auto-selected; two or more without `--change-dir` → exit 2 naming both; explicit `--change-dir` always wins even when auto-detection would differ; change dir exists but has no `tasks.md` → null+reason, exit 0 (not exit 2 — a missing artifact degrades, it does not fail the kickoff)
  - [x] Full combination test: crafted scenario (e.g. 8 tasks, 1 of 3 artifacts present, no prior snapshots) → verify the exact arithmetic end-to-end
  - [x] Ack always carries all documented keys, including when `phase1_points` is null
- [x] Task 4: Full regression + lint (all ACs) — no E2E requirement beyond the unit suite; this component reads only local files it creates fixtures for, no new pipe/encoding surface (2.2/2.3's BOM lessons don't apply here — no stdin, no subprocess)

## Dev Notes

- **Scope:** Phase-1 estimation only. Phase-2 actual/variance is Story 2.6 — do not touch `story_point_cost.phase2_points` or `.variance`; this story only ever *informs* the human-confirmed `points` value at kickoff, which the existing writer already stores. No changes to `docs-only/main.py`, `resolve.py`, `jira/main.py`, `confluence/main.py`, or the snapshot assembler.
- **Two genuine gaps found during research, deliberately not fixed here (out of scope, noted for awareness):**
  1. Nothing today clears `.story.yaml` after a story archives, so a second kickoff in the same repo would hit the AD-5 refuse-to-overwrite guard. This predates 2.5 and isn't this story's problem to solve — but it does mean the novelty modifier's data source had to be `snapshots/*.json` (which persists) rather than historical `.story.yaml` files (which don't).
  2. `openspec new change` resolves its own "planning home" via the CLI (possibly a registered store, not always `./openspec/changes/`) — this story deliberately does NOT invoke `openspec` at all (NFR2, and consistent with the opsx-wrapper's "must work with or without the CLI" philosophy) and instead scans the conventional `openspec/changes/*/` path directly. If a project uses a non-default store location, auto-detection will find nothing and degrade to null+reason — exactly the same graceful path as no active change, not a special case.
- **AD-6 formula, as literally specified, has only two named points on the volatility and novelty scales** (`+5`/`0` and `×1.5`/`×1.0`/`×0.8` are the three novelty tiers already, so novelty is fully specified — only *volatility's* middle values needed filling). The volatility linear-interpolation rule in Task 1 is this story's own documented invention filling that one gap; do not present it as if it came from the architecture doc.
- **FR5 / AC 2 is a hard invariant, not just this story's behavior:** search the codebase mentally before finishing — no code path anywhere may branch capture behavior (hook installation, event emission, snapshot assembly) on `phase1_points`, `must_split`, task count, or volatility. This estimator is read-only and side-effect-free; it must never write `.story.yaml`, the event log, or any snapshot.
- **Previous story intelligence:** `main(argv)`/ack/fail patterns; one-line JSON ack with `ok`; explicit `--repo-root`; exit 0/2 contract; §6 boundary-testing (test the exact n/n+1 edges, not just "large" and "small"); stdlib-only (no regex needed beyond simple string checks for `- [ ]`/`- [x]`); grep-verify any hallucinated review finding; hypothetical-input hardening counts as an improvement not a defect in the metrics log.
- **Process:** branch `story/2.5-phase1-estimator`; PR `Story 2.5: Story Points Are Estimated Automatically at Kickoff` linking FR2 (CAP-2, Phase-1 half), FR5, AD-6 (Phase-1 half — Phase-2 is 2.6), NFR2; squash-merge; epics annotation inside PR; metrics entry provisional→final.

### References

- [epics.md § Story 2.5](../planning-artifacts/epics.md) (lines 225–236) · [ARCHITECTURE-SPINE.md § AD-6](../planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md) (Phase-1 formula, the two named endpoints) · [SPEC.md § CAP-2](../specs/spec-pm-metrics-ai-engineering-flow/SPEC.md) · [.claude/skills/openspec-propose/SKILL.md](../../.claude/skills/openspec-propose/SKILL.md) (confirms `proposal.md`/`design.md`/`tasks.md`/`specs/` artifact names and the `- [ ]` checkbox convention, via `openspec-apply-change/SKILL.md`) · [project-context.md](../../project-context.md) §3 (ack/exit codes, never-trust-input), §6 (boundary testing) · [2-4 story file](2-4-story-closes-and-a-snapshot-is-created-automatically.md) (snapshot envelope shape this story reads `pm_metrics` from) · [.claude/skills/story-kickoff/SKILL.md](../../.claude/skills/story-kickoff/SKILL.md) (current state to extend)

## Dev Agent Record

### Agent Model Used

claude-sonnet-5 (create-story context engineering)

### Debug Log References

- RED: collection error, `tools/estimate-phase1/main.py` absent (16 tests authored first). GREEN: 163/163 after implementation.
- **Live CLI E2E caught a real defect the unit suite missed:** `novelty_modifier_for` re-derived a bucket from a prior snapshot's recorded `points` by feeding it back through `base_points_for()` — treating a Fibonacci-style points *value* (e.g. `5`) as if it were a task *count*. My own unit test happened to use `points=2` matching `base_points_for(2)==2` by coincidence, so it passed despite the bug. The E2E used `points=5` against a bucket of `5` and got `novelty_modifier: 1.0` instead of the expected `0.8`. Fixed by comparing `pm["points"] == base_points` directly — there is nothing to re-derive, since `base_points` is always already one of the bucket constants `{2,5,13,20}`. Added a regression test (`test_novelty_reuse_requires_matching_bucket_not_task_count_confusion`) plus a same-family negative test. Final: 165/165.
- Lint: ruff check/format clean.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created
- Implemented `tools/estimate-phase1/main.py`: read-only, side-effect-free AD-6 Phase-1 estimator. Change discovery scans `openspec/changes/*/` directly (no CLI call, NFR2); zero/ambiguous/missing-tasks.md all degrade to `phase1_points: null` + reason rather than guessing, except genuinely ambiguous multi-change (exit 2, names both, requires `--change-dir`). Base points from `- [ ]`/`- [x]` checkbox count in 4 Fibonacci-aligned buckets (2/5/13/20, `must_split` above 30 — informational only). Volatility bonus: documented linear fill (`round(5*(3-present)/3)`) between AD-6's two literal endpoints. Novelty modifier: since `.story.yaml` never persists across stories (a pre-existing, out-of-scope gap — noted, not fixed), pattern-matches against committed `snapshots/*.json` `pm_metrics` instead of literal prior manifests — this substitution is documented prominently in the module docstring and story Dev Notes as this story's own interpretation, not an architecture-doc quote.
- Wired into `story-kickoff` SKILL.md as a new step 3 (renumbering 3→4, 3a/3b→4a/4b, 4→5): runs after the double-kickoff refusal, before field elicitation; presents a non-null estimate as a suggestion the developer can accept or override; a null estimate falls back to the unassisted ask exactly as before Story 2.5. FR5 stated as a hard rule in both the skill and the story's Boundaries section — nothing from the estimator may ever gate capture.
- AC→test traceability: AC 1 → base/volatility/novelty unit tests at all documented boundaries + full-combination arithmetic test + live CLI E2E; AC 2 → explicit FR5 rule stated in code docstring, skill, and Dev Notes (no code path anywhere branches on the estimate — verified by inspection, since this is an invariant about the *rest* of the codebase, not testable in isolation).

### Change Log

- 2026-07-10: Story 2.5 implemented — Phase-1 estimator (change discovery, base/volatility/novelty formula), story-kickoff skill wiring (advisory-only). 18 new tests (165 total). Live E2E caught and fixed a real novelty-modifier defect (task-count/points-value confusion) the unit suite's own fixture coincidentally masked. Status → review.

### File List

- tools/estimate-phase1/main.py (new)
- tests/estimate_phase1/test_estimate.py (new)
- .claude/skills/story-kickoff/SKILL.md (modified — new step 3, renumbered 4/4a/4b/5)
- _bmad-output/implementation-artifacts/2-5-story-points-are-estimated-automatically-at-kickoff.md (modified — this story file)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — status transitions)
- _bmad-output/planning-artifacts/epics.md (modified — §12 annotation, inside PR)
