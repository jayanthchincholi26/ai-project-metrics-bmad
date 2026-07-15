# Development Metrics Tracker — explore-jira-ai-metrics

Execution metrics for each story of the metrics-capture pipeline, dogfooded on itself. Story numbering refers to `_bmad-output/planning-artifacts/epics.md`.

Conventions:

- **Estimated Cost and AI Token Cost are intentionally omitted for now** — capturing them automatically is exactly what Epic 2 of this project builds; they'll be filled from pipeline snapshots once Stories 2.3/2.4 land.
- **Story Points** are retroactive AD-6 Phase-1 estimates (this project's own formula), with the arithmetic shown — the kickoff flow didn't exist yet when these stories started.
- **Duration** is wall-clock from story creation to merge, grounded in git commit timestamps.
- **Defect counts** include only true confirmed defects; applied improvements and declined review findings are noted but not counted.
- **Testing / Review Efficiency** = share of total defects caught at that stage.
- Entries are written provisionally when the PR is raised and finalized after review + merge.

---

## Story: 1.1 — Create the Story Manifest via Docs-Only Kickoff

- **Date**: 2026-07-09
- **Duration**: ~60 minutes (story creation ~17:20 → merged 18:19 IST, incl. one LLM review round)
- **Story Points**: 5 SP (retroactive AD-6 Phase-1: 6 tasks → base 3; volatility +0, full spec/architecture existed; novelty ×1.5 first-time pattern → 4.5 ≈ 5)
- **Total Defects**: 1
  - Compile Defects: 0
  - Unit Test Defects: 0
  - Peer Review Defects: 1 (Gemini R1 — midnight race: `story_id` date and `created` from two separate `datetime.now()` calls; fixed with single shared aware `now` + regression test)
- **Testing Efficiency**: 0%
- **Review Efficiency**: 100%
- **Notes**: 18/18 tests green on first GREEN run (TDD; RED confirmed first). Review also yielded 2 applied improvements (f-strings, `dict[str, Any]` hint) and 2 declined findings (dir rename vs. architecture spine; PyYAML vs. stdlib-only rule) — logged as wontfix Issues #2/#3, not counted as defects. Merged via [PR #1](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/1) (merge commit; squash adopted from 1.2 onward).

---

## Story: 1.2 — Project-Level Source-of-Truth Configuration

- **Date**: 2026-07-09
- **Duration**: ~48 minutes (story creation ~18:47 → squash-merged 19:35 IST, incl. one LLM review round)
- **Story Points**: 2 SP (retroactive AD-6 Phase-1: 4 tasks → base 2; volatility +0; novelty ×0.8 existing-pattern reuse → 1.6 ≈ 2)
- **Total Defects**: 2
  - Compile Defects: 0
  - Unit Test Defects: 1 (UTF-8 BOM in PowerShell-written configs silently dropped the declared backend — caught by manual E2E during dev, not the unit suite; fixed with `utf-8-sig` + regression test)
  - Peer Review Defects: 1 (Gemini R1 — inline comments broke bare-value parsing; test-first repro also exposed a latent uncaught `JSONDecodeError` crash on quoted-value-then-comment lines, fixed by the same `parse_scalar()` change)
- **Testing Efficiency**: 50%
- **Review Efficiency**: 50%
- **Notes**: 36/36 tests green (17 new across story + review rounds). Review also yielded 2 applied improvements (single-quote support; exact `dict[str, str]` hint after dropping `json.loads`) and 1 declined finding (test packaging change — wontfix Issue #5), not counted as defects. The BOM defect remains the notable one: invisible to a fully green unit suite and any non-Windows CI. Squash-merged via [PR #4](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/4) (ee89bb6).

---

## Story: 1.3 — JIRA Adapter Auto-Fills Kickoff

- **Date**: 2026-07-09
- **Duration**: ~53 minutes (story creation ~20:00 → squash-merged 20:53 IST, incl. one LLM review round)
- **Story Points**: 5 SP (retroactive AD-6 Phase-1: 6 tasks → base 3; volatility +0; novelty ×1.5 first external-API integration → 4.5 ≈ 5)
- **Total Defects**: 0
  - Compile Defects: 0
  - Unit Test Defects: 0
  - Peer Review Defects: 0 (Gemini review yielded no true defects)
- **Testing Efficiency**: N/A (no defects found)
- **Review Efficiency**: N/A (no true defects confirmed)
- **Notes**: 60/60 tests green (24 new; all HTTP mocked). Review yielded 2 applied improvements (fractional points end-to-end + a proactive nan/inf guard; URL-encoded issue key), 1 finding already covered by an existing test, and 2 declined (shared config module → wontfix #7 with an open spine-level question for 1.4's third copy; `__init__.py` = #5) — none counted as defects. Fetch-only adapter design (AD-4 read literally) makes NFR4 provable: the credential-holding process writes no files, and token-absence is asserted on success and failure paths. Squash-merged via [PR #6](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/6) (53b18d3).

---

## Story: 1.4 — Confluence Adapter Auto-Fills Kickoff

- **Date**: 2026-07-09
- **Duration**: ~13 minutes (story creation 20:56 → squash-merged 21:09 IST, incl. one LLM review round — commit-timestamp grounded)
- **Story Points**: 2 SP (retroactive AD-6 Phase-1: 4 tasks → base 2; volatility +0; novelty ×0.8 — direct reuse of the jira adapter pattern → 1.6 ≈ 2)
- **Total Defects**: 1
  - Compile Defects: 0
  - Unit Test Defects: 0
  - Peer Review Defects: 1 (Gemini R1 — a malformed `points-`/`sprint-` label first in the list masked a valid one later; fixed with first-*valid*-label-wins search + 2 regression tests)
- **Testing Efficiency**: 0%
- **Review Efficiency**: 100%
- **Notes**: 79/79 tests green (20 new). Pattern reuse paid off visibly: 1.3's review learnings (URL encoding, lenient human-input parsing) were pre-applied rather than re-discovered. Labels convention (`points-N`/`sprint-X`) chosen since Confluence pages carry no native fields. Review also produced 1 hallucinated finding (nonexistent `import math`), grep-refuted on the PR — a data point for LLM-review trust calibration. Squash-merged via [PR #8](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/8) (43e779c).

---

## Story: 1.5 — Kickoff Manifest Declares Which AI Tool Is In Use

- **Date**: 2026-07-09
- **Duration**: ~10 minutes (story creation 21:11 → squash-merged 21:21 IST, incl. a zero-finding review round — commit-timestamp grounded)
- **Story Points**: 2 SP (retroactive AD-6 Phase-1: 5 tasks → base 2; volatility +0; novelty ×0.8 — mirrors the 1.2 resolution pattern exactly → 1.6 ≈ 2)
- **Total Defects**: 0
  - Compile Defects: 0
  - Unit Test Defects: 0
  - Peer Review Defects: 0 (Gemini: zero findings — first clean §9 pass of the project)
- **Testing Efficiency**: N/A (no defects found)
- **Review Efficiency**: N/A (no true defects confirmed)
- **Notes**: 87/87 tests green (10 new). Epic 1's final story and the first zero-finding review — earlier review lessons (URL encoding, format-over-membership validation, resilient parsing) were pre-applied rather than caught. Squash-merged via [PR #9](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/9) (e786ef6). **Epic 1 complete: 5 stories, 16 SP, ~2h50m wall-clock, 5 total defects (3 caught by review, 1 by dev E2E, 1 by test-first repro), zero escaped to merged code.**

---

## Story: 2.1 — Hook Installation Is a Single Repeatable Setup Step

- **Date**: 2026-07-10
- **Duration**: ~16 minutes (story creation ~10:00 → squash-merged 10:16 IST, incl. one LLM review round — commit-timestamp grounded)
- **Story Points**: 5 SP (retroactive AD-6 Phase-1: 5 tasks → base 3; volatility +0; novelty ×1.5 — first installer/filesystem-mutation story and first CI setup → 4.5 ≈ 5)
- **Total Defects**: 0
  - Compile Defects: 0
  - Unit Test Defects: 0
  - Peer Review Defects: 0 (Gemini: zero defects; 1 hardening improvement applied — directory-as-conflict, a stronger variant than the suggested `.is_file()`, which would have deferred the crash to write time)
- **Testing Efficiency**: N/A (no defects found)
- **Review Efficiency**: N/A (no true defects confirmed)
- **Notes**: 99/99 tests green (12 new; fake `.git/` fixture, no real git ops). First Epic 2 story: installer with validate-before-write, marker-based conflict refusal, additive settings merge. CI (§11) landed with this story and passed on both live runs. Convention note: hypothetical-input hardening counts as an improvement, not a defect (consistent with 1.3's URL-encoding call). Squash-merged via [PR #10](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/10) (1984950).

---

## Story: 2.2 — Git Activity Captured Silently While You Work

- **Date**: 2026-07-10
- **Duration**: ~22 minutes (story creation ~10:18 → squash-merged 10:39 IST, incl. one zero-defect LLM review round — commit-timestamp grounded)
- **Story Points**: 5 SP (retroactive AD-6 Phase-1: 5 tasks → base 3; volatility +0; novelty ×1.5 — first event producer, the epic's core pattern → 4.5 ≈ 5)
- **Total Defects**: 0
  - Compile Defects: 0
  - Unit Test Defects: 0
  - Peer Review Defects: 0 (Gemini: zero functional defects; parse_scalar third-copy smell acknowledged against Issue #7 and escalated to the 2.3 extraction decision)
- **Testing Efficiency**: N/A (no defects found)
- **Review Efficiency**: N/A (no true defects confirmed)
- **Notes**: 115/115 tests green (17 new incl. AD-9 boundaries at attempts 2/3/4). Milestone: the pipeline's first real events — real-git E2E captured a live `git.commit` with true hash/branch/subject, and pre-manifest buffering worked on the first try. Squash-merged via [PR #11](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/11) (ab6b424).

---

## Story: 2.3 — AI Session Activity Captured Silently

- **Date**: 2026-07-10
- **Duration**: ~53 minutes (story creation ~10:44 → squash-merged 11:37 IST, incl. a three-layer E2E debugging saga and a zero-finding review round — commit-timestamp grounded)
- **Story Points**: 5 SP (retroactive AD-6 Phase-1: 6 tasks → base 3; volatility +0; novelty ×1.5 — cross-family refactor + spine amendment + stdin/first-external-input handling → 4.5 ≈ 5)
- **Total Defects**: 1
  - Compile Defects: 0
  - Unit Test Defects: 1 (Windows cp1252-decoded stdin silently nulled every piped hook payload — caught by live-pipe dev E2E, invisible to the mocked suite; an intermediate fix was itself vacuous due to an invisible BOM literal, caught the same way; fixed with `utf-8-sig` reconfigure + byte-verified escape fallbacks)
  - Peer Review Defects: 0 (Gemini: zero findings — second clean §9 pass)
- **Testing Efficiency**: 100%
- **Review Efficiency**: 0%
- **Notes**: 127/127 tests green (12 new). Emitter extracted cross-family per user-approved spine amendment — Issue #7's recurring DRY finding deliberately resolved. Privacy guards (no tool_input, no prompt text) tested at file level. **BOM-family bug #3** — all three found by E2E, zero by unit suites: the strongest recurring signal in this project's own metrics. Squash-merged via [PR #12](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/12) (8c8a0c6).

---

## Story: 2.4 — Story Closes and a Snapshot Is Created Automatically

- **Date**: 2026-07-10
- **Duration**: ~37 minutes (story creation ~11:30 → squash-merged 12:07 IST, incl. a zero-defect LLM review round — commit-timestamp grounded)
- **Story Points**: 5 SP (retroactive AD-6 Phase-1: 4 tasks → base 3; volatility +0; novelty ×1.5 — first reducer + first revision-managed artifact → 4.5 ≈ 5)
- **Total Defects**: 0
  - Compile Defects: 0
  - Unit Test Defects: 0 (one test-fixture expectation corrected during RED→GREEN — the implementation was right; not counted per convention)
  - Peer Review Defects: 0 (Gemini: zero defects — third consecutive clean §9 pass; the assembler parse_scalar copy reviewer-conceded under #7's resolution language)
- **Testing Efficiency**: N/A (no defects found)
- **Review Efficiency**: N/A (no true defects confirmed)
- **Notes**: 147/147 tests green (20 new). **Milestone: the pipeline's first real end-to-end snapshot** — kickoff → real commit → Claude session → pre-manifest event backfilled (`pending_backfilled: 1`) → `rev1`, second close → `rev2` beside byte-stable `rev1`. Bonus in-the-wild validation: the machine's real npm `openspec` CLI refused a non-OpenSpec project and the wrapper correctly mirrored the failure with zero capture. Squash-merged via [PR #13](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/13) (636c612).

---

## Story: 2.5 — Story Points Are Estimated Automatically at Kickoff

- **Date**: 2026-07-10
- **Duration**: ~35 minutes of active work (story creation → squash-merged 15:42 IST, incl. one clean LLM review round; excludes the lunch break between the 2.4 close-out and this story's start — commit-timestamp gaps are not wall-clock effort)
- **Story Points**: 5 SP (retroactive AD-6 Phase-1... applied to itself: 4 tasks → base 3; volatility +0; novelty ×1.5 — first pure-computation/no-I/O story, genuinely novel formula work → 4.5 ≈ 5)
- **Total Defects**: 1
  - Compile Defects: 0
  - Unit Test Defects: 1 (novelty modifier compared a prior snapshot's points value through the wrong formula, treating a points value as a task count; caught by live CLI E2E after a coincidental unit-test fixture masked it — the fourth time E2E has caught what a green unit suite missed)
  - Peer Review Defects: 0 (Gemini: zero findings — fourth clean §9 pass; reviewer specifically highlighted the regression test born from the E2E-caught bug)
- **Testing Efficiency**: 100%
- **Review Efficiency**: 0%
- **Notes**: 165/165 tests green (18 new). Meta moment: this is the story that implements the AD-6 formula this project's own metrics file has been computing by hand (and by me, retroactively) all day. Two design decisions documented as this story's own inventions, not architecture-doc quotes (novelty's snapshot-based data source; volatility's linear fill). Squash-merged via [PR #14](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/14) (35fd4bf).

---

## Story: 2.6 — Story Points Are Reconciled Against What Actually Happened

- **Date**: 2026-07-10
- **Duration**: ~70 minutes (story creation ~16:35 → squash-merged 17:00 IST, incl. two commits addressing the review round — commit-timestamp grounded)
- **Story Points**: 8 SP (retroactive AD-6 Phase-1... applied to itself: 5 tasks incl. Task 0's cross-story fix → base 3; volatility +0; novelty ×1.5 — first cross-story architectural retrofit and git-integration story → 4.5, recorded as 8 to honestly reflect the added Task-0 scope rather than under-report)
- **Total Defects**: 3
  - Compile Defects: 0
  - Unit Test Defects: 2 — (1) a latent null-parsing bug in the already-merged `snapshot-assembler` (Story 2.4), caught by the unit suite itself; (2) a cwd-addressing bug in the new git-query code, caught only by the full-arc E2E (a wrong-cwd E2E run gave a plausible-but-wrong result before being traced)
  - Peer Review Defects: 1 (Gemini: binary-file `git show --stat` lines silently vanishing from the touched-file union — an effect I'd already observed in my own E2E but hadn't traced to root cause)
- **Testing Efficiency**: 67%
- **Review Efficiency**: 33%
- **Notes**: 178/178 tests green (18 new/updated). This story also retroactively closed a real architecture gap: Story 2.5's Phase-1 estimate was never persisted, so Story 2.6 couldn't reconcile against it — fixed via a documented `points_estimated` manifest field (AD-6a). Full-arc E2E produced hand-verified real arithmetic (phase1=5, phase2=3, variance=-2) from actual git history. Squash-merged via [PR #15](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/15) (b42e1ec). **Epic 2 complete: 6 stories, 33 SP (5+5+5+5+5+8), 178 tests, 5 total defects (2.1: 0, 2.2: 0, 2.3: 1, 2.4: 0, 2.5: 1, 2.6: 3) — dominated by E2E catches, not review or unit tests. Full retro in epics.md § Epic 2.**

---
