---
baseline_commit: 40a81d8
---

# Story 5.8: Automatic Defect Capture Cannot Rely on a Nonexistent `exit_code` Field

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer relying on Story 5.4's automatic compile/test defect capture,
I want it to actually work against Claude Code's real PostToolUse payload,
so that a matched failing command is reliably logged as a defect, not silently dropped forever.

## Background

Found live during JIRA-flow testing (2026-07-14/15, story `story-20260714-733705`): a genuinely broken `tsc --noEmit` (real `TS2322` type error, confirmed `exit 1`) never produced a `defect_compile` event, even after Story 5.7's fix.

Root-caused by capturing the actual raw PostToolUse payload (a temporary, never-committed debug tap in a local test-repo copy of `post_tool_use.py`) for a real failing Bash call. The real payload:
- has response data under **`tool_response`**, not `tool_output` as documented;
- has **no `exit_code` field anywhere** — not top-level, not nested.

This is a confirmed, currently-unfixed Claude Code platform gap, not something fixable in this project's own code — see `anthropics/claude-code#33656` and `rohitg00/agentmemory#539`. The official hooks docs describe a schema that doesn't match the real payload; Story 5.7's fix was correct relative to those docs, but the underlying capability the docs described doesn't actually exist. The live session's own assistant had already independently worked around this for its own reasoning, by manually appending `; echo "EXIT:$?"` to a command and reading the exit code back out of stdout text.

## Acceptance Criteria

1. **Given** `.story-config.yaml` declares `test_commands`/`build_commands` (unchanged config format/semantics from Story 5.4 — comma-separated substring patterns)
   **When** a Bash tool call's command matches one of those patterns
   **Then** `pre_tool_use.py` rewrites the command (via Claude Code's documented `PreToolUse` `updatedInput` mechanism) to append a distinctive, collision-resistant marker plus the command's own exit code to stdout — without changing what the command actually does

2. **Given** that rewritten command actually runs and exits non-zero
   **When** `post_tool_use.py` processes the resulting `PostToolUse` payload
   **Then** it parses the marker back out of `tool_response.stdout` (the real response key, not `tool_output`) and emits `ai.claude-code.defect_test`/`defect_compile` exactly as Story 5.4 intended — never relying on a structured exit-code field, since Claude Code doesn't send one

3. **Given** no `test_commands`/`build_commands` config, or a command that doesn't match any pattern
   **When** `pre_tool_use.py` processes it
   **Then** no rewriting happens at all — behavior is byte-for-byte unchanged from before this story (same principle as Story 5.4's original opt-in gate)

4. **Given** the marker mechanism itself
   **When** it's used anywhere
   **Then** the marker text and any raw stdout/stderr content are never written into `.story-events.jsonl` — only `{"matched_pattern": ...}`, same privacy guarantee as Story 5.4

5. **Given** this is a workaround for an unverified-by-us claim (that Claude Code's `PreToolUse` `updatedInput` mechanism actually rewrites the executed command, not just a hook-side observation)
   **When** this story is considered done
   **Then** it has been verified with a **real** Claude Code session (not just local hook-subprocess testing) actually running a matched command and confirming the rewrite took effect and a defect was captured — degrading silently (no defect capture, same as absent config) if it turns out not to work, never crashing

## Tasks / Subtasks

- [x] Task 1: shared marker + pattern-matching helpers (AC 1, 2)
  - [x] Subtask 1.1: add `DEFECT_EXIT_MARKER`, `split_config_patterns()`, `matched_config_pattern()` to `tools/hooks/_events.py`, shared between `pre_tool_use.py` and `post_tool_use.py` (both already import `_events`, so no new duplication)
- [x] Task 2: `pre_tool_use.py` command rewriting (AC 1, 3)
  - [x] Subtask 2.1: for a Bash call whose command matches a `test_commands`/`build_commands` pattern, print a `PreToolUse` `updatedInput` JSON response appending `; printf '\n<MARKER>:%s\n' "$?"` to the command, preserving all other `tool_input` fields (e.g. `description`) unchanged
  - [x] Subtask 2.2: absent config or non-matching command → no stdout output at all, unchanged from before this story
- [x] Task 3: `post_tool_use.py` marker parsing (AC 2, 4)
  - [x] Subtask 3.1: read `tool_response.stdout` (not `tool_output`), extract the exit code via the marker (last occurrence wins, in case the command's own output happens to contain something similar), never trust a bare `exit_code` field even if one happens to be present
  - [x] Subtask 3.2: no marker found → no defect capture (silent degrade, not a crash) — same principle as absent config
- [x] Task 4: update docs (informational only, no behavior)
  - [x] Subtask 4.1: `.story-config.yaml.example` and `INSTALL.md` explain the silent command-rewrite behavior plainly, since it's a real (harmless) side effect worth disclosing
- [x] Task 5: verify
  - [x] Subtask 5.1: full test suite green, `ruff check`/`ruff format --check` clean
  - [x] Subtask 5.2: live E2E — real subprocess run of `pre_tool_use.py` confirming the exact rewritten command JSON shape; that rewritten command then actually executed in a real shell, confirming the marker mechanism itself works (real non-zero exit surfaced correctly); the resulting real stdout fed into a real subprocess run of `post_tool_use.py`, confirming `defect_compile` fires; a zero-exit case confirmed to emit nothing
  - [x] Subtask 5.3: **real Claude Code session verification (AC 5)** — confirmed 2026-07-15 in a real v0.8.0 JIRA test session (`story-20260715-ebfe10`): a real `npx tsc --noEmit` against a genuinely broken `hello-complie-error.ts` produced the injected `__AI_METRICS_EXIT__:2` marker in real stdout, and `.story-events.jsonl` shows 3 real `ai.claude-code.defect_compile` events (`matched_pattern: "tsc --noEmit"`) across the session's 3 failing compile runs. `PreToolUse`'s `updatedInput` mechanism is confirmed to actually work live, not just per documentation/research.

## Dev Notes

### Scope

Redesigns the *detection mechanism* only — `test_commands`/`build_commands` config format, matching semantics (substring, comma-separated), the `defect_test`/`defect_compile` event types, and the privacy guarantee are all unchanged from Story 5.4. Existing `.story-config.yaml` files need no migration.

### Why not other options

Considered and rejected (see architecture discussion, 2026-07-15):
- **Park automatic capture entirely**, keep only manual `log-defect` — rejected because it abandons the user's original explicit goal (minimize developer intervention in defect logging) more than necessary; the manual path stays available regardless and is unaffected by this bug.
- **Heuristic stdout/stderr text sniffing** per tool (e.g. grep for "error"/"FAILED") — rejected as fragile and tool-specific, exactly what Story 5.4's config-pattern approach was designed to avoid.
- **Chosen approach (command rewriting via `PreToolUse`)**: deterministic, doesn't guess, reuses Claude Code's own documented extension point, and mirrors what the live assistant was already doing manually for its own reasoning (`; echo "EXIT:$?"`) — just made automatic and opt-in via existing config, rather than depending on the assistant remembering to do it.

### Verification risk (binding — do not close without Subtask 5.3)

The claim that `PreToolUse`'s `updatedInput` actually causes Claude Code to execute the *rewritten* command (not just observe the original) came from documentation/agent research, not yet from a real live Claude Code test — and this project has now found Claude Code's hooks docs wrong twice in one week (Story 5.7's `exit_code` location, and this story's `tool_output`→`tool_response`/no-exit-code-at-all finding). Per [[feedback-verify-live-hook-payloads]], trust but verify: this story's local subprocess E2E only proves the *hook's own logic* is correct in isolation, not that Claude Code actually respects the rewrite live. Subtask 5.3 is the real proof and must happen before declaring this fully done — if it turns out `updatedInput` doesn't work as documented either, the fallback is the same silent-no-capture degradation as today, not a crash, so there's no regression risk either way.

### Source tree touched

```text
tools/hooks/_events.py                          UPDATE  DEFECT_EXIT_MARKER, split_config_patterns(), matched_config_pattern()
tools/hooks/claude/pre_tool_use.py               UPDATE  command rewriting for matched Bash calls
tools/hooks/claude/post_tool_use.py              UPDATE  marker parsing from tool_response.stdout instead of exit_code
tests/hooks/test_claude_hooks.py                 UPDATE  fixtures moved to real tool_response shape; new pre_tool_use rewrite tests; round-trip test
tools/build-release/.story-config.yaml.example   UPDATE  doc comment explains the rewrite behavior
tools/build-release/INSTALL.md                   UPDATE  same doc update, embedded example
```

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5

### Debug Log References

Full suite: 331 passed (up from 324 — 7 new tests: 4 `pre_tool_use` rewrite tests, 1 round-trip test, 2 `extract_exit_code` unit tests). `ruff check`/`ruff format --check` clean. Live E2E (local subprocess only, per the Verification risk note above): real `pre_tool_use.py` subprocess run confirmed correct rewrite JSON; the exact rewritten command was then run in a real shell (`npx tsc` with no tsc installed, exit 1) confirming the marker mechanism itself; that real captured stdout fed into a real `post_tool_use.py` subprocess run confirmed `defect_compile` fired with `matched_pattern: "tsc --noEmit"`; a mirrored exit-0 case confirmed no defect event.

### Completion Notes List

- Story is now fully verified end-to-end, including live: real subprocess E2E (2026-07-15 dev round) plus a real v0.8.0 Claude Code session (2026-07-15, `story-20260715-ebfe10`) confirming Claude Code's `PreToolUse` `updatedInput` mechanism genuinely rewrites the executed command and 3 real `defect_compile` events were captured from real failing `tsc` runs.
- Chose to keep `test_commands`/`build_commands` config format completely unchanged — only the detection mechanism changed, so no user-facing config migration is needed.

### File List

tools/hooks/_events.py (updated)
tools/hooks/claude/pre_tool_use.py (updated)
tools/hooks/claude/post_tool_use.py (updated)
tests/hooks/test_claude_hooks.py (updated)
tools/build-release/.story-config.yaml.example (updated)
tools/build-release/INSTALL.md (updated)
