---
baseline_commit: 2dab9f0ead36f2450eafa4ac2e69d6985d0ed372
---

# Story 2.4: Story Closes and a Snapshot Is Created Automatically

Status: review

## Story

As a developer,
I want closing my story to automatically produce a metrics snapshot,
so that I never manually compile a report.

## Acceptance Criteria

1. **Given** a developer runs `opsx archive` (via the wrapper), **when** the CLI wrapper intercepts the command, **then** the snapshot assembler reduces the full event log (Stories 2.2, 2.3) into the fixed envelope: `{schema_version, story_id, revision, pm_metrics, engineering_metrics, story_point_cost, token_cost}` (AD-3a).
2. Every close produces a **new immutable revision** — `revision` increments, nothing is ever overwritten in place (AD-3/AD-3b), and a prior revision file survives byte-identical.
3. Pending-spool events (AD-1b) are backfilled with the manifest's story_id and included in the reduction — buffered events finally reach their story, never dropped.

## Tasks / Subtasks

- [x] Task 1: Snapshot assembler `tools/snapshot-assembler/main.py` (AC: 1, 2, 3)
  - [x] CLI: `--repo-root DIR` (required); manifest must exist → else exit 2 ("no `.story.yaml` — kickoff before closing"); reads `.story.yaml` (full flat-YAML parse — local copy of the established parser, adapters-family single-file convention per the #7 resolution language), `.story-events.jsonl`, `.story-events.pending.jsonl`
  - [x] **Backfill (AC 3):** pending lines get `story_id` = manifest's; included in reduction; after a successful snapshot write, backfilled lines are appended to the main log (one atomic append per line) and the spool is deleted — the assembler is the reducer, the only actor allowed this; malformed JSONL lines are counted+skipped with a stderr warning, never fatal (§3 never-trust-input)
  - [x] **Reduction:** only events whose `story_id` matches the manifest (a shared log may carry other stories' events — filter, don't pollute); malformed/foreign lines excluded from counts
  - [x] **Envelope (AC 1):** exactly the seven AD-3a top-level keys, `schema_version: 1`. `pm_metrics` ← manifest `{points, goal, sprint, source_of_truth, ai_tool, created}`. `engineering_metrics` ← reduction: `{commits, checkouts, merges, ai_sessions, tool_uses, prompts, event_count, first_event_at, last_event_at}` (counts from `git.commit`, `git.checkout`, `git.merge`, `ai.*.session_start`, `ai.*.tool_use`, `ai.*.prompt`). `story_point_cost` ← `{phase1_points: null, phase2_points: null, variance: null}` — the AD-3a keys exist from day one; 2.5/2.6 fill them (honest nulls, never zeros). `token_cost` ← `{total_tokens, reason, sessions_observed}`: sum of non-null session_end token_costs (today always null → `total_tokens: null` + first non-empty reason propagated)
  - [x] **Immutable revisions (AC 2):** write to `snapshots/{story_id}.v1.rev{N}.json` (repo root; committed per spine § Deployment — do NOT gitignore); `N` = 1 + max existing revision for this story_id+version (filename scan); create the file with `open(..., "x")`-semantics after an atomic temp write + `os.rename` to a name verified free — refuse (exit 2) rather than ever replacing an existing revision
  - [x] Ack: one JSON line `{ok, snapshot, revision, events_reduced, pending_backfilled}`, exit 0
- [x] Task 2: opsx CLI wrapper `tools/opsx-wrapper/main.py` (AC: 1)
  - [x] Pure passthrough for any subcommand ≠ `archive`: exec the underlying CLI (`openspec` else `opsx`, whichever is on PATH) via subprocess arg-list, mirror its exit code, no capture — NFR1: wrap, never modify
  - [x] `archive`: run the underlying CLI first; **only on its success** → emit `opsx.archive` event (`{"args": [...]}`) via the shared emitter (sys.path bridge to `tools/hooks`, the third producer family the amendment anticipated) → invoke the assembler via subprocess (`uv run tools/snapshot-assembler/main.py --repo-root ...`) and relay its ack
  - [x] Underlying CLI not on PATH → visible note ("no openspec/opsx CLI found — capture proceeding without passthrough") and continue with capture; underlying CLI fails → mirror its exit code, NO event, NO snapshot (a failed archive is not a close)
  - [x] Assembler failure → surface its stderr and exit 1 even though the archive succeeded (a close without a snapshot is precisely what must never pass silently — AD-9 philosophy)
- [x] Task 3: Tests (AC: 1, 2, 3) — mirror paths per §5: `tests/snapshot_assembler/test_reduce.py`, `tests/opsx_wrapper/test_wrapper.py`
  - [x] Assembler: envelope has exactly the 7 keys + schema_version 1; reduction counts from a crafted log (2 commits, 1 checkout, 1 merge, 1 session, 3 tool_uses, 2 prompts); events with a different story_id excluded; malformed lines skipped with warning, valid ones still reduced; first/last timestamps correct
  - [x] Revisions: two runs → rev1 and rev2 files, rev1 byte-identical after the second run; forged pre-existing target for the next rev → refused, exit 2
  - [x] Backfill: pending events included in counts with the manifest story_id, appended to main log, spool deleted; no pending spool → `pending_backfilled: 0`
  - [x] story_point_cost all-null trio present; token_cost null-with-reason propagated from session_end payloads; empty log → zero counts, null timestamps, snapshot still produced
  - [x] No manifest → exit 2, nothing written
  - [x] Wrapper (subprocess + emitter mocked): non-archive passes through untouched (no event, no assembler); archive success → event emitted + assembler invoked with the right `--repo-root`; underlying exit 3 → mirrored, no event/assembler; missing CLI → note + capture proceeds; assembler failure → exit 1 with stderr surfaced
- [x] Task 4: Full regression + lint + real E2E (all ACs)
  - [x] Scratch-repo E2E extending 2.2/2.3's recipe: init + hooks + kickoff → real commit + piped claude events + pending event (pre-manifest trick or hand-written spool) → run the wrapper's archive path (no openspec installed → the missing-CLI branch, which is itself a test) → inspect `snapshots/*.rev1.json`; run again → rev2 exists, rev1 untouched

## Dev Notes

- **Scope:** close-time reduction only. NOT here: the AD-6 Phase-1 estimate (2.5) and Phase-2 reconciliation (2.6) — the null trio is their landing pad; `.active-story`/time slices (Epic 3 — engineering_metrics gains time fields later); any central upload (deferred; the snapshot IS the boundary, AD-3).
- **AD-3/AD-3a/AD-3b are the contract:** seven fixed top-level keys; `story_point_cost` is the ONLY home for the phase1/phase2/variance trio; every close = new sequential revision, consumers take the highest revision as current, priors are audit history. The snapshot is the only thing that ever crosses to a central layer — never the raw log.
- **The assembler is the pipeline's only reducer** — the single component allowed to READ the event log and to resolve the pending spool. Producers stay append-only; nothing else changes.
- **UPDATE files: none in `tools/`** — both scripts are NEW (seed paths `tools/opsx-wrapper/main.py`, `tools/snapshot-assembler/main.py`, verbatim). The shared emitter is imported (bridge), not modified. `.gitignore` unchanged — snapshots are committed artifacts.
- **Windows/JSONL learnings apply (2.2/2.3):** read both event files with `encoding="utf-8"` and per-line `json.loads` in try/except; write the snapshot with `json.dumps(..., indent=2)` + `newline="\n"`; timestamps are envelope strings — compare lexicographically (ISO-8601 with fixed offset format sorts correctly for same-offset producers; note the caveat in a comment).
- **Wrapper exit-code table:** passthrough mirrors underlying always; archive+capture-failure → 1 (visible, never silent); missing CLI → capture-only path exits per assembler result. Document in docstring like the hooks' table.
- **Previous story intelligence:** `main(argv)`/ack/fail patterns; counting-fake test helpers; file-level assertions for anything sensitive; grep-verify hallucinated review findings; E2E over mocks for anything touching real pipes/encodings — this project's entire defect history (BOM×3) says the E2E leg is not optional.
- **Process:** branch `story/2.4-snapshot-assembler`; PR `Story 2.4: Story Closes and a Snapshot Is Created Automatically` linking FR1/FR6 (CAP-1/CAP-6), AD-3, AD-3a, AD-1b (backfill), NFR1, NFR3; squash-merge; epics annotation inside PR; metrics provisional→final; CI green.

### References

- [epics.md § Story 2.4](../planning-artifacts/epics.md) (lines 211–223) · [ARCHITECTURE-SPINE.md § AD-3/AD-3a, Consistency, Structural Seed, Deployment](../planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md) · [review-adversarial.md Finding on AD-3b](../planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/reviews/review-adversarial.md) (revision naming) · [SPEC.md § CAP-6](../specs/spec-pm-metrics-ai-engineering-flow/SPEC.md) · [project-context.md](../../project-context.md) §3/§5 (mirror paths named verbatim)/§6 · [2-3 story file](2-3-ai-session-activity-captured-silently.md) (emitter bridge, E2E discipline)

## Dev Agent Record

### Agent Model Used

claude-fable-5 (create-story context engineering)

### Debug Log References

- RED: collection errors (both scripts absent; 20 tests authored first). GREEN: 147/147 — one test-fixture timestamp expectation corrected (implementation was right), no implementation defects
- Full-arc E2E (scratch git repo): pre-manifest event → kickoff (8 pts) → setup-hooks → real commit → piped Claude session → wrapper `archive`. Bonus finding: a real npm `openspec` CLI exists on this machine and refused the non-OpenSpec project — the wrapper correctly mirrored the failure with NO event/snapshot (the failed-archive rule, proven in the wild). Success arc via a stub CLI: rev1 snapshot with all 7 AD-3a keys, `events_reduced: 7`, `pending_backfilled: 1` (spool deleted, early-bird event joined the story), second close → rev2 beside byte-stable rev1
- Lint: ruff check/format clean

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created
- Assembler: the pipeline's only reducer — full flat-YAML manifest read, per-line tolerant JSONL reads (malformed lines counted + warned, never fatal), story_id filtering (foreign events excluded), AD-1b backfill (pending → reduction → appended to main log → spool deleted, only after a successful snapshot write), AD-3a envelope with honest null trio and token null-with-reason, AD-3b exclusive-create revisions (`open(..., "x")` — an existing revision file is refused, never replaced).
- Wrapper: passthrough-first (NFR1), archive-success-gated capture, `opsx.archive` emitted via the shared emitter bridge (third producer family), assembler invoked via subprocess; snapshot failure after a successful archive exits 1 loudly.
- AC→test traceability: AC 1 → envelope/reduction/pm/token tests + wrapper archive-flow tests + E2E; AC 2 → rev2-with-byte-identical-rev1 + forged-target-refused tests + E2E second close; AC 3 → backfill tests (counts, main-log append, spool deletion, ack count) + E2E `pending_backfilled: 1`.
- Epic 2's capture→reduce arc is now complete end-to-end; 2.5/2.6 fill the story_point_cost trio.

### Change Log

- 2026-07-10: Story 2.4 implemented — snapshot assembler (reducer, backfill, immutable revisions) + opsx wrapper (passthrough, success-gated capture). 20 new tests (147 total) + full-arc E2E producing the pipeline's first real snapshot. Status → review.

### File List

- tools/snapshot-assembler/main.py (new)
- tools/opsx-wrapper/main.py (new)
- tests/snapshot_assembler/test_reduce.py (new)
- tests/opsx_wrapper/test_wrapper.py (new)
- _bmad-output/implementation-artifacts/2-4-story-closes-and-a-snapshot-is-created-automatically.md (modified — this story file)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — status transitions)
- _bmad-output/planning-artifacts/epics.md (modified — §12 annotation, inside PR)
