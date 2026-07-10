---
baseline_commit: ede225b693181dbed391694ba205e25b1cdf41e4
---

# Story 2.6: Story Points Are Reconciled Against What Actually Happened

Status: review

## Story

As a developer,
I want my estimate compared against what actually happened when I close the story,
so that leadership sees real variance instead of a static guess.

## Acceptance Criteria

1. **Given** a story with an event log (Stories 2.2–2.4) and a Phase-1 estimate (Story 2.5), **when** the story closes, **then** the Phase-2 formula computes actual points from review cycles, agent-narrated decision events, and testing-type weights (AD-6).
2. The variance between the Phase-1 estimate and Phase-2 actual is logged, with **neither number overwritten** — both persist distinctly in the snapshot.

## Tasks / Subtasks

- [x] Task 0: Close a real gap from Story 2.5 — persist the Phase-1 estimate (AC: 2)
  - [x] **Discovered while researching this story:** Story 2.5's estimator is advisory-only and its output was never written anywhere; only the developer-confirmed `points` survives past kickoff. AD-6a (the adversarial architecture review) explicitly requires the manifest to store **both** `points` (confirmed) and `points_estimated` (the raw Phase-1 number, "never substituted"), as two always-distinct fields. Without this fix, Story 2.6 has no Phase-1 number to reconcile against at close time — this task is a prerequisite, not scope creep.
  - [x] `tools/adapters/docs-only/main.py` (UPDATE): add optional `--points-estimated` (a number, may be omitted/null — no validation beyond "parses as a number if given"); manifest key order becomes `story_id, source_of_truth, ai_tool, points, points_estimated, goal, sprint, description, created` (inserted right after `points`, per AD-6a "always distinct, never merged"); everything else about the writer is unchanged
  - [x] `.claude/skills/story-kickoff/SKILL.md` (UPDATE): step 5's writer invocation gains `--points-estimated <raw estimate>` when step 3's estimator returned a non-null `phase1_points` (pass the raw suggestion, **not** the developer's possibly-overridden confirmed value — that distinction is the entire point of AD-6a); omit the flag when step 3 returned null
  - [x] `tests/adapters/test_docs_only.py` (UPDATE): manifest carries `points_estimated` when given, `null` when omitted; `MANIFEST_KEYS` order updated
- [x] Task 1: Phase-2 computation, extending the existing reducer (AC: 1, 2)
  - [x] `tools/snapshot-assembler/main.py` (UPDATE — this is the pipeline's only reducer; Phase-2 belongs here, not a new script, since it needs the same full event log + manifest Phase-1 already reads)
  - [x] **Review cycles** (AD-6's literal "UserPromptSubmit follow-up count" — maps directly onto our `ai.*.prompt` events, no invention needed): `review_cycles = max(0, prompt_event_count - 1)` (the first prompt starts the work; only *follow-ups* are review cycles)
  - [x] **Agent-narrated decision events — genuinely unmeasurable today (documented gap, not invented):** no producer in this pipeline emits a "decision" event type (Stories 2.2/2.3 fixed the full producer set; adding one is out of scope here). `decision_events = 0` always, and the snapshot carries `story_point_cost.reduced_confidence: true` + a reason string — the same AD-10 vocabulary already used for missing-signal degradation, applied here to a Claude-Code-native gap rather than a non-Claude-Code-tool gap
  - [x] **Verification complexity — reuse the shared git helper, do not reimplement subprocess safety:** for each `git.commit` event's `hash` in this story's reduced event set, bridge-import `_events` from `tools/hooks/` (same `sys.path.insert` pattern the opsx-wrapper already uses) and call `_events.git_out("show", "--stat", "--format=", <hash>)`; parse changed file paths from the stat output; union across all commits (dedup by path). A path is a **test file** if it contains `test` case-insensitively (matches this repo's own `tests/` convention and common `test_*`/`*_test` naming) — everything else is a **context file**
  - [x] **AD-6 asks for sub-type weights (unit ×0.5/integration ×1/manual QA ×1.5/perf ×2) the event schema cannot currently distinguish — document this limitation explicitly, do not fake a classifier:** apply a uniform ×1 (integration-equivalent) to every identified test file; state this as a known simplification in the module docstring, not silently
  - [x] **Combination formula — AD-6 lists four inputs but specifies no arithmetic to combine them (unlike Phase-1's explicit "base + volatility, times novelty"); this story defines one, documented as its own invention exactly like Phase-1's volatility fill was:** `phase2_points = round(review_cycles * 1.0 + verification_files * 1.0 + context_files * 0.2)` (decision_events contributes 0, always, today)
  - [x] **Degradation, not failure:** git unavailable, a commit hash not found locally (e.g. history rewritten), or any `git show` failure for a given commit → skip that commit's file-stat contribution silently (the commit still counts toward `engineering_metrics.commits` as before) — never fail the whole close over an unreadable diff
  - [x] **Variance:** `phase1_points` now comes from the manifest's `points_estimated` (Task 0), not the always-null placeholder; `variance = phase2_points - phase1_points` only when `phase1_points` is not null, else `variance: null` (honest null — can't diff against nothing); `story_point_cost` becomes `{phase1_points, phase2_points, variance, reduced_confidence, reduced_confidence_reasons}` — phase1/phase2 are two independently-sourced, never-overwritten numbers exactly per AC 2
- [x] Task 2: Tests (AC: 1, 2) — extend the existing suites, do not create new test modules for the same reducer/writer
  - [x] `tests/snapshot_assembler/test_reduce.py`: review-cycle count from N prompt events (incl. the "only 1 prompt → 0 cycles" edge); decision_events always 0 with `reduced_confidence: true` and a non-empty reason; verification/context file counts from a crafted `git_out` fake (mock `_events.git_out`, no real git in unit tests per §5); a commit hash `git_out` can't resolve → skipped, no crash; phase1_points sourced from manifest `points_estimated`; variance arithmetic exact; `points_estimated` absent from manifest → `phase1_points: null`, `variance: null`
  - [x] `tests/adapters/test_docs_only.py`: `--points-estimated` recorded; omitted → `null`; existing 1.1–1.3 tests unaffected (key order test updated)
- [x] Task 3: Full regression + lint + real E2E (all ACs)
  - [x] Extend the established full-arc recipe (2.4's scratch-repo test) one more step: kickoff **with** `--points-estimated` supplied → real commits touching a test file and a non-test file → close → inspect the snapshot's `story_point_cost` for real, non-null `phase1_points`/`phase2_points`/`variance` and a sane `reduced_confidence` reason — this is the first time this project's own metrics-by-hand exercise (the day's `docs/metrics.md` entries) could in principle be replaced by a real snapshot

## Dev Notes

- **Scope:** Phase-2 computation + variance only, plus the Task 0 prerequisite fix. NOT here: any UI/reporting on variance, any feedback loop that *acts* on variance to retune AD-6's weights (spine § Deferred explicitly defers this), a real decision-narration producer (would be its own future story), sub-type test classification beyond the documented uniform weight.
- **Two gaps found during research, resolved deliberately (not silently) here:**
  1. **The AD-6a manifest fix (Task 0)** — without it, AC 2 ("neither number overwritten") is structurally impossible to satisfy, since only one points-shaped number (the confirmed `points`) exists anywhere past kickoff today.
  2. **Decision-narration events don't exist** — rather than inventing a fake signal or silently treating it as "0 decisions, full confidence," the gap is surfaced honestly via `reduced_confidence` (borrowing AD-10's already-established vocabulary for exactly this situation, just applied to a same-tool gap instead of a cross-tool one).
- **UPDATE files (read-before-touch, both fully read this session):**
  - `tools/adapters/docs-only/main.py` — current behavior: validate-before-write, atomic write, refuse-overwrite, ack pattern, key order `story_id, source_of_truth, ai_tool, points, goal, sprint, description, created`. This story ONLY inserts one new optional field (`points_estimated`) into that order; every existing validation/atomicity/test must remain green unchanged.
  - `tools/snapshot-assembler/main.py` — current behavior: manifest+log read, story_id filtering, AD-1b backfill, `engineering_metrics` reduction, `token_cost_of`, exclusive-create revisions. This story adds a Phase-2 computation function and changes `story_point_cost` from the static all-null dict to a computed one; nothing about backfill, revisioning, or `engineering_metrics` changes.
  - `.claude/skills/story-kickoff/SKILL.md` — current step 3 (estimator) and step 5 (writer invocation); step 5's command line gains one optional flag.
- **Reuse, don't reinvent, the git-query helper:** `tools/hooks/_events.py`'s `git_out()` already solves "call git safely, arg-list not shell=True (§4), degrade to None on any failure" — bridge-import it (`sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))`, same pattern `opsx-wrapper/main.py` already uses) rather than re-deriving subprocess-safety logic a third time. This is a deliberate reuse decision, worth being explicit about since Issue #7's resolution language distinguishes "shared mechanics with real drift risk" (reuse) from "small stable single-file copies" (duplicate) — subprocess safety is squarely the former.
- **Previous story intelligence:** `main(argv)`/ack/fail patterns; §5 mirror test paths (extend existing files, don't fragment); §6 boundary tests (0/1/N prompts for review cycles); grep-verify hallucinated review findings; live E2E is not optional for anything touching git or file I/O (this project's defect history — 3 BOM bugs + 1 novelty-formula bug — was caught exclusively by E2E, never by unit suites alone).
- **Process:** branch `story/2.6-phase2-reconciliation`; PR `Story 2.6: Story Points Are Reconciled Against What Actually Happened` linking FR2 (CAP-2, Phase-2 half), AD-6, AD-6a (the Task 0 fix); squash-merge; epics annotation inside PR; metrics provisional→final. **Merging this story completes Epic 2 (6/6)** — epic flips to done, §13 retro note due in the close-out.

### References

- [epics.md § Story 2.6](../planning-artifacts/epics.md) (lines 238–248) · [ARCHITECTURE-SPINE.md § AD-6](../planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md) (Phase-2 formula inputs, no combination arithmetic given) · [review-adversarial.md Finding 6 / AD-6a](../planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/reviews/review-adversarial.md) (the manifest-persistence requirement this story's Task 0 satisfies) · [SPEC.md § CAP-2](../specs/spec-pm-metrics-ai-engineering-flow/SPEC.md) · [project-context.md](../../project-context.md) §4 (subprocess arg-lists), §5–6 (mirror paths, boundary tests) · [2-4](2-4-story-closes-and-a-snapshot-is-created-automatically.md)/[2-5](2-5-story-points-are-estimated-automatically-at-kickoff.md) story files (assembler and estimator patterns this story extends)

## Dev Agent Record

### Agent Model Used

claude-sonnet-5 (create-story context engineering)

### Debug Log References

- RED: 17 new/updated tests authored first across `test_docs_only.py` and `test_reduce.py`. GREEN after implementation, but the run surfaced **two real defects, both in already-merged code, neither hypothetical**:
  1. **Latent null-parsing bug in `snapshot-assembler/read_manifest`** (present since Story 2.4, never triggered before): the flat-YAML reader never converted a bare unquoted `null` token back to Python `None` — it returned the literal string `"null"`. Nothing broke previously because no manifest field was ever used in arithmetic; `points_estimated` is the first one. Caught immediately as a `TypeError` on first test run (not by E2E this time — the unit suite itself failed loudly). Fixed in `read_manifest`.
  2. **cwd-addressing bug in the new `touched_files()` code**, caught only by the full-arc E2E: `_events.git_out()` runs `git` against the ambient process cwd, never the assembler's own `--repo-root`. My first E2E run (invoking the assembler from the wrong directory after a `Pop-Location`) produced a plausible-looking but wrong result (`phase2_points: 1` when it should have been `3`) — silently querying the wrong repository's git history rather than erroring. Fixed by adding an explicit `cwd` parameter to the shared `_events.git_out()` (backward compatible, defaults to today's ambient behavior for git hooks, which is correct since git itself sets their cwd) and threading `root` through `touched_files`/`verification_and_context_counts`/`story_point_cost_of`. Regression test pins that `git_out` is always called with `cwd=<repo-root>`.
- Full-arc E2E (corrected, cwd held throughout): kickoff with `--points-estimated 5` → 2 real commits (one touching only a source file, one adding a real test file) → 2 real prompt events → close. Result: `phase1_points: 5`, `phase2_points: 3` (1 review cycle + 1 verification file + 5 context files × 0.2), `variance: -2` — hand-verified arithmetic against the real git history.
- Final: 177/177 tests; ruff check/format clean.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created
- **Task 0 (AD-6a fix):** `docs-only/main.py` gained `--points-estimated` (optional, nullable, independent validation from `--points`); manifest now stores both fields distinctly, exactly as AD-6a requires. `story-kickoff` SKILL.md updated: step 3 now tells the developer to remember the *raw* estimate (not the possibly-overridden confirmed value) for step 5's new flag.
- **Task 1 (Phase-2):** extended (not replaced) the existing reducer. `review_cycles` maps directly onto AD-6's literal "UserPromptSubmit follow-up count" via existing `ai.*.prompt` events — no invention needed. `decision_events` stays honestly `0` with `reduced_confidence: true` + a stated reason (no producer exists for this signal — flagged, not faked). Verification/context file classification reuses the shared `_events.git_out()` helper (bridge-imported, not reimplemented) rather than re-deriving subprocess safety a third time. The combination formula and the uniform test-file weight are both explicitly documented as this story's own inventions, matching how Phase-1's volatility fill was documented in Story 2.5.
- **Both defects found were fixed at the root, not worked around:** the null-parsing bug is fixed in the shared parser (benefits any future nullable manifest field, not just this one); the cwd bug is fixed in the shared `_events.git_out()` (benefits any future caller that needs repo-pinned git queries, not just this reducer).
- AC→test traceability: AC 1 → review-cycle/verification/context/decision-events tests + full combination arithmetic + E2E; AC 2 → phase1-sourced-from-manifest tests, variance-only-when-phase1-present test, and the manifest itself now genuinely carries two independent numbers (provable by inspection of `docs-only/main.py`'s key order).
- **This story completes Epic 2 (6/6).**

### Change Log

- 2026-07-10: Story 2.6 implemented — AD-6a manifest fix (Task 0), Phase-2 reconciliation extending the snapshot assembler (Task 1). 17 new tests (177 total). Two real defects found and fixed: a latent manifest null-parsing bug (caught by the unit suite itself) and a git cwd-addressing bug (caught only by the full-arc E2E). Status → review. Epic 2 complete pending merge.

### File List

- tools/adapters/docs-only/main.py (modified — `--points-estimated` flag + manifest field + docstring)
- tools/snapshot-assembler/main.py (modified — Phase-2 computation, `read_manifest` null-parsing fix, git bridge-import, cwd-correct git queries)
- tools/hooks/_events.py (modified — `git_out()` gains an explicit `cwd` parameter)
- .claude/skills/story-kickoff/SKILL.md (modified — step 3/step 5 wiring for `--points-estimated`)
- tests/adapters/test_docs_only.py (modified — `points_estimated` tests + key order)
- tests/snapshot_assembler/test_reduce.py (modified — Phase-2 tests, cwd regression test, `_events` bridge loading)
- _bmad-output/implementation-artifacts/2-6-story-points-are-reconciled-against-what-actually-happened.md (modified — this story file)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — status transitions)
- _bmad-output/planning-artifacts/epics.md (modified — §12 annotation + epic-2 completion, inside PR)
