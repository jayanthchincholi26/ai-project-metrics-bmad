---
baseline_commit: 94fbfa1
---

# Story 5.7: `post_tool_use.py` Reads `exit_code` From the Wrong Payload Location

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer relying on Story 5.4's automatic compile/test defect capture,
I want `post_tool_use.py` to read the Bash exit code from where Claude Code actually puts it,
so that `ai.claude-code.defect_test`/`defect_compile` events are ever emitted at all.

## Background

Found live during JIRA-flow testing (2026-07-14, story `story-20260714-9429f0`, repo `test-metrics/install-irm`): a deliberately failing `tsc --noEmit` run never produced a `defect_compile` event in `.story-events.jsonl`, despite `build_commands: tsc --noEmit` being correctly uncommented in `.story-config.yaml`.

Root cause, confirmed against Claude Code's official hooks documentation (via a `claude-code-guide` agent query): the PostToolUse hook's JSON payload has `exit_code` as a **top-level key**, not nested under `tool_output`. `tools/hooks/claude/post_tool_use.py` reads:

```python
exit_code = data.get("tool_output", {}).get("exit_code")
```

which always evaluates to `None`, so the `if exit_code not in (None, 0):` guard can never be true — `defect_test`/`defect_compile` can never fire, for any command, regardless of `.story-config.yaml`.

This escaped Story 5.4's own test suite because `tests/hooks/test_claude_hooks.py`'s fixtures baked in the same wrong shape (`"tool_output": {"exit_code": 1, ...}`), so 322 green tests validated the code against a payload shape that doesn't match what Claude Code actually sends. This is Story 5.4's Definition of Done gap, caught only by live E2E testing against a real Claude Code session rather than hand-built hook-input fixtures.

## Acceptance Criteria

1. **Given** a Bash tool call whose command matches a configured `test_commands`/`build_commands` pattern and exits non-zero (per Claude Code's real top-level `exit_code` field)
   **When** `post_tool_use.py` processes the PostToolUse hook payload
   **Then** it reads `exit_code` from the top level of the payload (not from `tool_output`), and emits the matching `ai.claude-code.defect_test`/`defect_compile` event exactly as Story 5.4 intended

2. **Given** the existing test suite's hook-input fixtures
   **When** this story is done
   **Then** every fixture representing a real Claude Code PostToolUse payload places `exit_code` at the top level (matching the real schema), so a future regression here would actually be caught by the suite

3. **Given** a Bash call that is not `test_commands`/`build_commands`-matching, or exits 0
   **When** `post_tool_use.py` processes it
   **Then** behavior is unchanged (no defect event, `ai.claude-code.tool_use`/activity-recording still fire) — this is a pure bug fix, no behavior change beyond making the intended Story 5.4 behavior actually work

## Tasks / Subtasks

- [ ] Task 1: fix the payload read (AC 1)
  - [ ] Subtask 1.1: change `post_tool_use.py`'s `exit_code` read from `data.get("tool_output", {}).get("exit_code")` to `data.get("exit_code")`
- [ ] Task 2: fix the test fixtures (AC 2)
  - [ ] Subtask 2.1: update every hook-input fixture in `tests/hooks/test_claude_hooks.py` that sets `exit_code` to place it at the top level of the payload dict instead of nested under `tool_output`
- [ ] Task 3: verify live (AC 1, AC 3)
  - [ ] Subtask 3.1: full test suite green
  - [ ] Subtask 3.2: real E2E — a real failing Bash tool call (e.g. `tsc --noEmit` against a genuinely broken `.ts` file, left broken rather than auto-fixed) against a live hook invocation, confirming a `defect_compile`/`defect_test` event actually appears in `.story-events.jsonl`
  - [ ] Subtask 3.3: confirm a passing command (exit 0) and a non-matching failing command still produce no defect event (AC 3 regression guard)

## Dev Notes

### Scope

Single-line-cause bug fix in `tools/hooks/claude/post_tool_use.py`, plus correcting the test fixtures that concealed it. No design change to Story 5.4's defect-capture feature itself — the feature was correctly designed, just reading the wrong JSON path.

### Source tree touched

```text
tools/hooks/claude/post_tool_use.py       UPDATE  read exit_code from payload top level
tests/hooks/test_claude_hooks.py          UPDATE  fixtures: exit_code moves to top level
```

### Reference: confirmed real PostToolUse payload shape (Claude Code hooks docs)

Top-level keys: `session_id`, `prompt_id`, `transcript_path`, `cwd`, `permission_mode`, `hook_event_name`, `tool_name`, `tool_input`, `tool_output`, `exit_code`. For Bash: `tool_input.command` (correct, unchanged), `exit_code` (top-level — this is the fix), `tool_output.stdout`/`tool_output.stderr` (unaffected, not read by this hook).

## Dev Agent Record

### Agent Model Used

(pending)

### Debug Log References

(pending)

### Completion Notes List

(pending)

### File List

(pending)
