---
baseline_commit: eabe892
---

# Story 2.12: Dry-Run Mode for Snapshot Assembler

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want to preview a story's current metrics without closing the story,
so that testing/inspecting in-progress capture (e.g. verifying the defect-capture hook fires correctly) never accidentally marks a mid-flight story as done.

## Acceptance Criteria

1. **Given** `tools/snapshot-assembler/main.py --repo-root <root> --dry-run`
   **When** the assembler runs
   **Then** it performs the exact same reduction as today (reads `.story-events.jsonl` + the AD-1b pending spool, computes all six envelope sections: `pm_metrics`, `engineering_metrics`, `story_point_cost`, `token_cost`, `estimated_cost`, `defect_metrics`) and prints the computed snapshot JSON to stdout

2. **Given** `--dry-run` is set
   **When** the assembler would otherwise write `snapshots/{story_id}.v{schema}.rev{N}.json`
   **Then** it skips that write entirely — no file is created, no `snapshots/` directory is created if absent, and the printed output's `revision` field is clearly a preview (`would_be_revision`), not a claim that a real revision now exists

3. **Given** `--dry-run` is set
   **When** the assembler would otherwise consume the AD-1b pending spool (append its events to the main log, delete the spool file)
   **Then** it skips that too — the pending spool file is left completely untouched on disk, so a later real (non-dry-run) run still sees and correctly backfills it

4. **Given** `--dry-run` is *not* set (the default)
   **When** the assembler runs
   **Then** behavior is byte-for-byte unchanged from today — this story only adds an opt-in preview path, never alters the existing close-time behavior or its stdout ack shape

5. **Given** `tools/opsx-wrapper/main.py archive <name>`
   **When** evaluating whether to thread `--dry-run` through to the assembler call
   **Then** document the decision either way — see Dev Notes "Why the wrapper is out of scope" for the resolved answer (not threaded, and why)

## Tasks / Subtasks

- [ ] Task 1: `--dry-run` CLI flag and output shape (AC: 1, 2)
  - [ ] Subtask 1.1 (RED): add a test that writes a real, non-degraded story (manifest + a `standard_log()`-style event set) and runs the assembler with `--dry-run`; assert stdout contains a JSON object with `"dry_run": true` and a `"snapshot"` key whose value is the *full computed snapshot dict* (all six envelope sections present, matching what a real run's written file would contain) — assert `snapshots/` does not exist on disk afterward
  - [ ] Subtask 1.2 (GREEN): add `p.add_argument("--dry-run", action="store_true", help="compute and print the snapshot without writing it or consuming the pending spool")` in `main()`'s argparse block
  - [ ] Subtask 1.3 (GREEN): after building the `snapshot` dict (unchanged — `next_revision()` is a read-only glob scan, safe to call in dry-run too, since it never creates `snapshots/` itself), branch on `args.dry_run`: print `json.dumps({"ok": True, "dry_run": True, "snapshot": snapshot, "would_be_revision": snapshot["revision"], "events_reduced": len(ours)}, indent=2)` and `return 0` **before** the `snapshots_dir.mkdir(...)` line — nothing after that point in `main()` may execute on the dry-run path
  - [ ] Subtask 1.4 (RED then GREEN): add a test asserting the *real* (non-dry-run) path's stdout ack shape is completely unchanged — same keys as today (`ok`, `snapshot` as a **path string**, `revision`, `events_reduced`, `pending_backfilled`) — guards against accidentally collapsing the two output shapes into one

- [ ] Task 2: pending spool is untouched in dry-run (AC: 3)
  - [ ] Subtask 2.1 (RED): write a manifest, a main log, **and** a `.story-events.pending.jsonl` with one event; run with `--dry-run`; assert (a) the pending file still exists on disk with its original content afterward, (b) the dry-run's printed `snapshot.engineering_metrics`/other sections still *reflect* the pending event's contribution (it's read and reduced-from, just never persisted/consumed) — this distinguishes "read for computation" from "consumed and deleted"
  - [ ] Subtask 2.2 (GREEN): guard the existing `if pending_events: ... (root / PENDING_FILE).unlink()` block so it only runs when `not args.dry_run`
  - [ ] Subtask 2.3: add a regression test — dry-run followed immediately by a **real** (non-dry-run) run in the same test — asserting the real run's `pending_backfilled` count and resulting snapshot are identical to what they'd have been with no intervening dry-run call at all (proves dry-run truly leaves zero trace)

- [ ] Task 3: `--dry-run` degraded-story parity (AC: 4)
  - [ ] Subtask 3.1: re-run (or parametrize) a representative sample of this file's existing degraded-signal tests (null `token_cost`, null `estimated_cost`, null `defect_metrics`, `reduced_confidence: true`) once each in `--dry-run` mode, asserting the printed `snapshot` section matches field-for-field what the equivalent non-dry-run test asserts from the written file — proves the two code paths compute identically, only the output destination/side-effects differ

- [ ] Task 4: full regression, live E2E, and doc parity (AC: 1-5)
  - [ ] Subtask 4.1: `uv run pytest` full suite green; `uv run ruff check .`; `uv run ruff format --check tools tests`
  - [ ] Subtask 4.2: live E2E reproduction of the exact scenario this story fixes — a real repo, a real `.story.yaml`, real events from real git commits/hook invocations, deliberately including at least one `ai.claude-code.defect_compile` event (mirroring the pilot-testing incident) — run `uv run tools/snapshot-assembler/main.py --repo-root . --dry-run`, confirm the printed snapshot correctly reflects the defect event, confirm `snapshots/` is not created, then run a **real** kickoff-guard check (or `story-kickoff`'s own logic, reasoning through it if not directly invokable) confirming the story still reads as "open" (no snapshot exists) — this is the actual real-world scenario that motivated the story, not just a unit-test abstraction
  - [ ] Subtask 4.3: update `tools/build-release/INSTALL.md` — add a line under the existing "Daily use" close-out steps (or a short new callout near them) documenting `--dry-run` as the way to preview current metrics mid-story without closing it; cross-reference the Known Limitations section's existing AD-3 "snapshot = closed" framing so a reader understands *why* this flag exists, not just that it does

## Dev Notes

### Scope — what this story is and is not

- This extends Story 2.4's tool (`tools/snapshot-assembler/main.py`) with one new opt-in flag on the same script — no new file, no new command, no change to the manifest/event-log/config file formats.
- **Do NOT build in this story:** threading `--dry-run` through `tools/opsx-wrapper/main.py archive` — see "Why the wrapper is out of scope" below, a design decision already made, not left open for the dev agent to re-litigate. Do NOT change `next_revision()`'s own logic (it's already side-effect-free — a `.glob()` scan, safe to call from the dry-run path unmodified). Do NOT add a `--dry-run` flag to `tools/metrics-report/main.py` or `tools/dashboard/main.py` — those are already non-destructive, read-many-snapshots tools with no "closes anything" side effect to preview around.

### Why this matters (severity context)

Found live during pilot testing (2026-07-16) of `explore-jira-ai-metrics`'s own downstream tool, in a separate test repo (`test-metrics/v0.9.2-docs-only`). A developer deliberately introduced a compile error to verify Story 5.4/5.8's `PostToolUse` defect-capture hook actually fires `ai.claude-code.defect_compile` — a reasonable, common verification step. To see that event reflected in a human-readable metrics view, the assembler was run directly — which, per AD-3 (a snapshot's mere existence is the authoritative "this story is closed" signal every other producer, including Story 2.10's kickoff double-check, relies on), closed the story for real. The resulting snapshot recorded `engineering_metrics.commits: 0` — a genuinely misleading permanent record, since the real code hadn't been committed yet. It was recoverable (AD-3b: revisions are exclusive-create, never overwritten; a later real close created `rev2` with the true finished state, and the stale `rev1` was left in place as harmless audit history, exactly as the architecture intends) — but the whole detour was avoidable. There is currently no way to answer "what would my metrics look like right now" without permanently and irreversibly triggering the "story closed" signal.

### Architecture compliance (binding invariants)

- **AD-3 / AD-3a** — "Only a versioned snapshot schema crosses the boundary... Snapshot internal shape and immutability." A dry-run preview, by construction, never writes a snapshot file at all — nothing "crosses the boundary" (AD-3's own framing), so it cannot conflict with immutability (AD-3a) or the "closed" signal (AD-3) no matter how many times it's run. This is precisely why dry-run is the right fix rather than, say, a "delete a snapshot" escape hatch (which *would* conflict with AD-3a's immutability guarantee).
- **AD-1b** — pending-spool events "join the reduction... after a successful snapshot write, so a failed close never consumes the buffer." Dry-run extends this same principle one step further: since dry-run never performs "a successful snapshot write" at all, the pending spool must never be consumed by it either — this story doesn't introduce a new invariant, it just makes sure the existing one ("consumption only follows a real write") holds for the new code path too.
- **project-context.md §3** — "exactly one JSON object printed to stdout on success" (the established ack pattern). The dry-run output must honor this too: one JSON object, with an explicit `"dry_run": true` marker so a caller/script can distinguish it from the real close ack (which has no such key) without needing to guess from shape alone.
- **project-context.md §7 "no premature abstraction"** — the fix is a single `if args.dry_run:` early-return branch inserted at exactly one point in the existing `main()`, not a parallel `dry_run_main()` function or a refactor of `main()` into smaller pieces. Reuse everything already computed (`snapshot` dict, `ours`, `next_revision()`) as-is.

### Why the wrapper is out of scope (resolved design decision)

`tools/opsx-wrapper/main.py archive <name>` was evaluated (AC 5) and **deliberately not given a `--dry-run` passthrough** in this story. Its `archive` action always performs a real `openspec archive` first (moves the change directory under `openspec/changes/archive/`, updates `openspec/specs/`) via a real subprocess call to the `openspec`/`opsx` CLI — that step is not itself previewable by this project's own code (it's someone else's CLI), and is arguably not something a "dry run" should skip anyway, since the actual pilot-testing incident this story fixes involved running the **bare assembler directly**, not through the wrapper. Threading `--dry-run` through the wrapper would only skip the *second* half (the snapshot write) while the *first* half (the real, irreversible openspec archive + a real `opsx.archive` event permanently appended to the log) still happened — a confusing "half dry run" that leaves the openspec change archived while the tool's own "story closed" signal (the snapshot) doesn't yet exist. `INSTALL.md` already documents that calling the assembler standalone (`uv run tools/snapshot-assembler/main.py --repo-root .`) is a supported, separate path from the wrapper's combined archive+snapshot step — `--dry-run` slots into that same already-documented standalone path, with zero wrapper changes needed.

### Source tree touched

```text
tools/snapshot-assembler/main.py              UPDATE  add --dry-run argparse flag; branch in main() before the snapshots_dir.mkdir()/write/pending-consume block
tests/snapshot_assembler/test_reduce.py       UPDATE  new tests for dry-run output shape, pending-spool non-consumption, degraded-signal parity, real-ack-shape-unchanged regression
tools/build-release/INSTALL.md                UPDATE  document --dry-run as the way to preview metrics without closing a story
```

`tools/opsx-wrapper/main.py`, `tools/hooks/_events.py`, `tools/metrics-report/main.py`, and `tools/dashboard/main.py` are **not** touched — this story is scoped entirely to the assembler's own CLI.

### Project Structure Notes

No conflicts with the unified project structure — this story extends the same file (`tools/snapshot-assembler/main.py`) Story 2.4 created and Stories 5.2/5.4/3.4 have each already modified once.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.12] — the pilot-testing incident this story fixes, and the resolved "wrapper out of scope" decision
- [Source: tools/snapshot-assembler/main.py#main] — exact insertion point (`snapshot` dict built, then `snapshots_dir.mkdir(...)`/`open(target, "x", ...)`/pending-consume block that dry-run must skip); `next_revision()` — already read-only, safe to reuse unmodified
- [Source: tools/opsx-wrapper/main.py] — confirms `archive`'s real-CLI-subprocess-then-assembler-call shape, the basis for excluding it from this story
- [Source: tests/snapshot_assembler/test_reduce.py] — existing `run()`/`write_manifest()`/`write_events()`/`read_snapshot()`/`standard_log()` helpers and degraded-signal test patterns to extend, not reimplement
- [Source: tools/build-release/INSTALL.md#Known limitations, #Daily use] — where the new flag should be documented, and the AD-3 framing it should cross-reference
- [Source: ARCHITECTURE-SPINE.md#AD-1b, AD-3, AD-3a] — the binding invariants this story must not violate
- [Source: project-context.md] — §3 the stdout-ack contract, §7 no-premature-abstraction

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
