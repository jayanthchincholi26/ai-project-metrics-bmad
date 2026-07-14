---
baseline_commit: 8d00fb1
---

# Story 5.2: Real Cost and Token Fields Per Story

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer or lead reviewing a story's snapshot,
I want real AI token counts and computed cost figures instead of a bare `token_cost: null`,
so that a snapshot answers "what did this actually cost" the same way this project's own hand-maintained `docs/metrics.md` ledger already tries to, but automatically.

## Acceptance Criteria

1. **Given** a Claude Code session ends (`SessionEnd` hook fires)
   **When** `tools/hooks/claude/session_end.py` runs
   **Then** it reads `transcript_path` from its own hook input (already present in every Claude Code hook payload, per Story 2.3's own deferred note) and, if that file is readable, sums real `input_tokens`/`output_tokens` across every `type: "assistant"` line's `message.usage` object in that transcript, emitting them in the event payload instead of a bare null

2. **Given** the transcript is missing, unreadable, malformed, or contains no assistant/usage lines
   **When** the hook runs
   **Then** it degrades to `input_tokens: null`, `output_tokens: null`, and a specific `token_cost_reason` string describing which of those happened — never crashes, never blocks the session (same AD-9/exit-0-unconditionally contract `session_end.py` already has today)

3. **Given** `tools/snapshot-assembler/main.py` aggregates `token_cost` across a story's session_end events
   **When** a snapshot is assembled
   **Then** `token_cost` gains `input_tokens`/`output_tokens` (summed across all session_end events for the story, `null` if none are known) alongside the existing `reason`/`sessions_observed`, plus a computed `cost_usd` — `(input_tokens × ai_input_rate / 1,000,000) + (output_tokens × ai_output_rate / 1,000,000)` — **only** when both token counts and both rates are known; `null` otherwise, never a fabricated number from partial inputs

4. **Given** `.story-config.yaml` may declare `hourly_rate`, `ai_input_rate`, `ai_output_rate` (all optional, all absent by default)
   **When** a snapshot is assembled
   **Then** the snapshot gains a new top-level `estimated_cost` section: `{usd, hourly_rate, duration_minutes, reason}` — `duration_minutes` computed from `engineering_metrics.first_event_at`/`last_event_at` (already present), `usd = hourly_rate × (duration_minutes / 60)` only when `hourly_rate` is configured, `reason` stating why `usd` is null otherwise (e.g. `"hourly_rate not configured in .story-config.yaml"`)

5. **Given** this adds a new top-level key to the snapshot envelope
   **When** this story is done
   **Then** `ARCHITECTURE-SPINE.md`'s AD-3a is updated in the same PR to reflect the new fixed envelope `{schema_version, story_id, revision, pm_metrics, engineering_metrics, story_point_cost, token_cost, estimated_cost}` — never let code and planning docs diverge (project-context.md §12)

## Tasks / Subtasks

- [ ] Task 1: real token counts from the transcript (AC: 1, 2)
  - [ ] Subtask 1.1 (RED): add a test feeding `session_end.main()` a fake `transcript_path` pointing to a small fixture `.jsonl` (2-3 lines, mixing `type: "assistant"` lines with `usage.input_tokens`/`output_tokens` and non-assistant lines that must be ignored) — assert the emitted payload's `input_tokens`/`output_tokens` equal the correct sums
  - [ ] Subtask 1.2 (RED): add tests for each degradation path — no `transcript_path` key in stdin data, a `transcript_path` pointing to a nonexistent file, and a transcript file that exists but contains zero assistant/usage lines — each must assert `input_tokens is None`, `output_tokens is None`, and a specific, non-generic `token_cost_reason` string for each distinct case
  - [ ] Subtask 1.3 (GREEN): implement transcript parsing in `session_end.py` — read the file line by line (a transcript can be large; don't require loading the whole file into memory if avoidable, though correctness matters more than micro-optimization here), parse each line as JSON, skip lines that aren't valid JSON or aren't `type: "assistant"`, sum `input_tokens`/`output_tokens` from `message.usage`. Wrap file I/O and JSON parsing in error handling that degrades to the null-with-reason payload — never raise, never a non-zero exit
  - [ ] Subtask 1.4 (GREEN): update `test_session_end_token_cost_is_null_with_reason` (existing test, no `transcript_path` fed) — it now exercises the "no transcript_path" degradation path specifically; confirm its assertions still hold under the new field names (`input_tokens`/`output_tokens`, not the old bare `token_cost`)

- [ ] Task 2: aggregate real tokens + compute AI token cost in the snapshot (AC: 3)
  - [ ] Subtask 2.1 (RED): add/update tests in `tests/snapshot_assembler/test_reduce.py` (or wherever `token_cost_of()` is tested) for: known input+output tokens with both rates configured (real `cost_usd`); known tokens but rates absent (`cost_usd: null`, no crash); rates configured but tokens unknown (`cost_usd: null`); mixed session_end events (some with real tokens, some null) summing only the known ones, same pattern as the existing `total_tokens`/`known` logic
  - [ ] Subtask 2.2 (GREEN): update `token_cost_of()` in `tools/snapshot-assembler/main.py` to read `input_tokens`/`output_tokens` from each session_end event's payload (replacing the old bare `token_cost` field), sum knowns, and compute `cost_usd` per AC 3's formula — reuse the existing "sum only what's known, null the rest" pattern already established for `total_tokens`

- [ ] Task 3: read cost-rate config and compute Estimated Cost (AC: 4)
  - [ ] Subtask 3.1 (RED): add tests for a new `estimated_cost_of()` (or similarly named) function — `hourly_rate` configured → real `usd`/`duration_minutes`; `hourly_rate` absent → `usd: null` with a specific reason; confirm `duration_minutes` arithmetic against known `first_event_at`/`last_event_at` timestamps (reuse whatever ISO-8601 parsing convention `reduce_events()` already establishes for these two fields — don't invent a second timestamp format)
  - [ ] Subtask 3.2 (GREEN): implement reading `hourly_rate`/`ai_input_rate`/`ai_output_rate` from `.story-config.yaml` inside `tools/snapshot-assembler/main.py` — **reuse this file's own existing `parse_scalar()`** (already present, used today for `read_manifest()`) rather than importing `tools/adapters/resolve.py` (that module is scoped to kickoff-time source-of-truth/ai_tool resolution, not scoped for extension to arbitrary numeric config keys) or duplicating a 5th copy of the flat-YAML parser elsewhere. Absent keys default to `None` (not `0` — a missing rate must never silently compute a `$0.00` cost)
  - [ ] Subtask 3.3 (GREEN): wire `estimated_cost` into the snapshot envelope in `main()`, alongside the other five existing sections

- [ ] Task 4: architecture and doc parity (AC: 5)
  - [ ] Subtask 4.1: update `ARCHITECTURE-SPINE.md`'s AD-3a rule text to include `estimated_cost` in the fixed envelope key list, and briefly describe `token_cost`'s expanded shape (`input_tokens`/`output_tokens`/`cost_usd` alongside the existing `reason`/`sessions_observed`)
  - [ ] Subtask 4.2: add the three new optional `.story-config.yaml` keys (`hourly_rate`, `ai_input_rate`, `ai_output_rate`) to `tools/build-release/INSTALL.md`'s `.story-config.yaml` example, with a one-line note that all three are optional and absent-by-default (consistent with this story's whole "never fabricate a number" stance)

- [ ] Task 5: full regression and live E2E (AC: 1-5)
  - [ ] Subtask 5.1: `uv run pytest` full suite green; `uv run ruff check .`; `uv run ruff format --check tools tests`
  - [ ] Subtask 5.2: live E2E — a real Claude Code session doing real work, ended cleanly (same "close VS Code entirely" discipline from the 2026-07-13 session-count investigation, so a real `transcript_path` is available and the session has genuinely ended), then a real `.story-config.yaml` with all three rates configured, archived/snapshotted, and the resulting `token_cost`/`estimated_cost` sections inspected for real, non-null, sane numbers — not just unit-tested in isolation

## Dev Notes

### Scope — what this story is and is not

- This story adds **real numbers where honest nulls existed before** — it does not change anything about *when* a snapshot is produced, how stories are kicked off, or the event log's shape beyond `session_end.py`'s own payload.
- **Do NOT build in this story:** a "rate locked in at kickoff" mechanism (the reference tool the user cited, `developer_handover.md`, locks `hourlyRate` into its own `active_task.json` at task-start time so a mid-task rate change doesn't retroactively affect an in-flight task). This project has no equivalent per-story locking file today, and building one is out of scope here — **explicitly documented limitation**: this story reads whatever `.story-config.yaml` says at *close* time, so a rate changed mid-story does affect the computed cost. If this limitation matters later, locking rates at kickoff (mirroring how `points_estimated` is already locked at kickoff, AD-6a) would be its own follow-up story — do not build it speculatively here.
- **Do NOT track cache tokens** (`cache_creation_input_tokens`/`cache_read_input_tokens`) in this story's cost formula — the reference tool's formula and this story's ACs only ask for `input_tokens`/`output_tokens`. Real transcripts do carry cache-token fields (confirmed by direct inspection, 2026-07-13); ignoring them here is a documented simplification, not an oversight — extending the formula to price cache tokens differently is a plausible future story, not this one.
- **Do NOT extract a shared flat-YAML-config-reading module.** This codebase already has 4 independent copies of `parse_scalar()`/similar (`tools/adapters/resolve.py`, `tools/adapters/jira/main.py`, `tools/hooks/_events.py`, `tools/snapshot-assembler/main.py` itself) — a pre-existing, acknowledged pattern (see `docs/metrics.md`'s Story 2.2/2.3 notes on the "third copy" question). This story adds a 4th *use* of the assembler's own already-present copy, not a 5th independent copy — reuse what's already in this file (Subtask 3.2). Don't take this story as license to finally do the extraction; that's out of scope here.

### The real transcript structure (confirmed by direct inspection, 2026-07-13 — use this, don't guess)

A Claude Code session transcript (the file at the hook payload's `transcript_path`) is JSONL. Each line that represents an assistant turn looks like:
```json
{"type": "assistant", "message": {"usage": {"input_tokens": 6130, "output_tokens": 478, "cache_creation_input_tokens": 20346, "cache_read_input_tokens": 0, ...}, ...}, ...other keys...}
```
Not every line has `type: "assistant"` (there are also `"user"`, tool-result, and other line types) — only sum lines where `type == "assistant"` and `message.usage` exists. A line that fails to parse as JSON, or parses but lacks the expected shape, should simply be skipped (not counted, not a fatal error) — matches this project's established "skip malformed, count and report at the caller if needed" pattern (see `snapshot-assembler`'s own `read_jsonl()`'s `malformed` counter for the precedent to mirror, if useful, though `session_end.py` itself doesn't currently have a "malformed count" concept — a simple skip-and-continue is sufficient here, no need to invent a new reporting mechanism for a hook that already emits null-with-reason on total failure).

### Architecture compliance (binding invariants)

- **AD-3a** — this story explicitly widens the fixed envelope (adding `estimated_cost`) and `token_cost`'s internal shape. AC 5/Task 4.1 requires updating this rule in the same PR — do not leave code and the architecture doc diverging, even temporarily.
- **AD-9** — "Silence is never an acceptable outcome" / "a hook must never fail the session." `session_end.py` already has an unconditional-exit-0 contract; the transcript-parsing addition must preserve it exactly — any file-read or JSON-parse failure degrades to null-with-reason, never an exception that could propagate.
- **AD-10** — "null-with-reason, never a bare zero." Every new numeric field this story introduces (`input_tokens`, `output_tokens`, `cost_usd`, `estimated_cost.usd`) follows this rule strictly: a missing rate or missing token count is `null` with a stated `reason`, never `0` and never a number computed from an assumed default.
- **Existing test infrastructure**: `tests/hooks/test_claude_hooks.py`'s `feed_stdin()` helper (monkeypatches `events.read_stdin_json`) is exactly how to inject a fake `transcript_path` into `session_end.main()` for RED/GREEN tests — no real Claude Code session needed for unit tests. `tests/snapshot_assembler/test_reduce.py` (or the equivalent existing test file for `token_cost_of()`) is where Task 2's tests belong; check current file naming before creating a new one.

### `.story-config.yaml` schema addition

```yaml
hourly_rate: 10        # USD/hr, optional, no default (null → no Estimated Cost)
ai_input_rate: 1.25    # USD per 1,000,000 input tokens, optional, no default
ai_output_rate: 5.00   # USD per 1,000,000 output tokens, optional, no default
```
Mirrors `developer_handover.md`'s own `.env`-based rate config, but placed in this project's existing `.story-config.yaml` (AD-4's "declare once" config file) rather than introducing a second config mechanism.

### Source tree touched

```text
tools/hooks/claude/session_end.py                                 UPDATE  reads transcript_path, sums real input/output tokens, degrades to null-with-reason
tests/hooks/test_claude_hooks.py                                    UPDATE  new tests for real-token-sum + each degradation path; existing null-reason test adjusted to new field names
tools/snapshot-assembler/main.py                                    UPDATE  token_cost_of() aggregates real tokens + cost_usd; new estimated_cost_of(); .story-config.yaml rate reader (reuses existing parse_scalar()); main() wires estimated_cost into the envelope
tests/snapshot_assembler/test_reduce.py (or equivalent)             UPDATE  tests for both new/changed aggregation functions
_bmad-output/planning-artifacts/architecture/.../ARCHITECTURE-SPINE.md   UPDATE  AD-3a's envelope key list + token_cost shape description
tools/build-release/INSTALL.md                                      UPDATE  .story-config.yaml example gains the 3 optional rate keys
```

### Project Structure Notes

No conflicts — extends `session_end.py` (Story 2.3), `snapshot-assembler/main.py` (Stories 2.4/2.6), `.story-config.yaml` (Story 1.2/AD-4), and `INSTALL.md` (Stories 1.6/1.7/2.7/2.11/5.1), all previously-established files.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.2] — the ask and its rationale, including the caveat about Claude Code's transcript format being internal/unversioned
- [Source: _bmad-output/implementation-artifacts/2-3-ai-session-activity-captured-silently.md] — the original deferral note this story finally builds: "a future transcript-parsing enhancement could compute real usage from `transcript_path`... note as a possible future story, don't build" (that note said don't build it *then* — this story is that future
- [Source: tools/hooks/claude/session_end.py] — the exact function this story extends
- [Source: tools/snapshot-assembler/main.py#token_cost_of, story_point_cost_of] — the aggregation pattern to extend/mirror
- [Source: tools/adapters/resolve.py#read_config, parse_scalar] — an existing (4th) copy of the flat-YAML pattern to be aware of, but explicitly NOT the one to extend (Dev Notes above)
- [Source: docs/developer_handover.md] — the reference tool's cost/token formulas this story mirrors (Estimated Cost, AI Token Cost sections specifically — per the user's own scoping instruction, not the JIRA orchestration or defect-tracking parts of that document)
- [Source: ARCHITECTURE-SPINE.md#AD-3a, AD-9, AD-10] — the envelope-fixed, never-silent, and null-with-reason invariants this story must satisfy
- [Source: project-context.md] — §2 no premature abstraction (don't extract the config-reader), §12 Story DoD (architecture doc parity requirement)

## Dev Agent Record

### Agent Model Used

_to be filled by dev-story_

### Debug Log References

_to be filled by dev-story_

### Completion Notes List

_to be filled by dev-story_

### File List

_to be filled by dev-story_
