---
baseline_commit: 8b6dbcd
---

# Story 6.8: Close Commands Reliably Trigger the JIRA-Sync Skill

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer closing a JIRA-backed story,
I want the close command to reliably trigger `story-close`'s JIRA sub-task/parent sync no matter how I invoke it,
so that I don't have to remember special phrasing to get the same "avoid developer interaction" outcome Story 6.2 was built for.

## Acceptance Criteria

1. **Given** a JIRA-backed story (`.story.yaml`'s `source_of_truth: jira` with a non-null `jira_issue_key`)
   **When** either close command (`tools/opsx-wrapper/main.py archive <name>` or `tools/snapshot-assembler/main.py`, without `--dry-run`) is about to run as a Bash tool call, **and** the `story-close` skill's own steps have not run first (no ack marker present)
   **Then** the `PreToolUse` hook **denies** the tool call and returns `additionalContext` (visible to the assistant, not just the human) instructing it to follow `.claude/skills/story-close/SKILL.md` in full, then retry the exact same command

2. **Given** the `story-close` skill has actually been followed (its own step 6 creates a local ack marker immediately before running the close command)
   **When** the close command is retried
   **Then** the `PreToolUse` hook allows it through and consumes (deletes) the marker — single-use, never left lying around to silently bypass a future close

3. **Given** a non-JIRA story (`source_of_truth` is `docs-only`/`confluence`, or `jira` with no `jira_issue_key`)
   **When** either close command runs
   **Then** nothing changes — no gate, no marker, byte-for-byte the same behavior as before this story (mirrors `story-close`'s own step 2 passthrough)

4. **Given** `--dry-run` is passed to `tools/snapshot-assembler/main.py`
   **When** it runs
   **Then** it is never gated — a dry run is side-effect-free and touches no JIRA state, so there is nothing for this story's mechanism to protect

5. **Given** this is a reliability mechanism, not a security boundary (the hook can only observe that a marker file exists, not that the skill's steps were genuinely followed)
   **When** implementing this
   **Then** design and document it as a nudge that makes the *intended* path the path of least resistance, not as tamper-proof enforcement — consistent with this project's own hook-safety posture elsewhere (`pre_tool_use.py`'s existing docstring: hooks must never disrupt or hard-block metrics capture; this is a narrow, deliberate, documented exception scoped only to the two close commands on JIRA-backed stories)

## Tasks / Subtasks

- [ ] Task 1: `tools/hooks/_events.py` — a generalized `.story.yaml` reader (AC: 1, 3)
  - [ ] Subtask 1.1 (RED): add tests for a new `read_manifest(root)` function — returns a dict of every flat scalar key/value in `.story.yaml` (mirroring `read_story_config()`'s existing shape for `.story-config.yaml`), and `{}` when the file is absent
  - [ ] Subtask 1.2 (GREEN): implement `read_manifest()`, reusing the existing `parse_scalar()` helper — don't duplicate `read_story_config()`'s body, generalize the shared bit if that's cleaner, but don't touch `story_id()` (already works, not this story's concern)

- [ ] Task 2: `tools/hooks/claude/pre_tool_use.py` — detect and gate the two close commands (AC: 1, 2, 3, 4, 5)
  - [ ] Subtask 2.1 (RED): tests for a new `_is_close_command(command)` helper — matches `tools/snapshot-assembler/main.py` (any flags), matches `tools/opsx-wrapper/main.py ... archive ...`, does **not** match either when `--dry-run` is present anywhere in the command, does not match an unrelated command
  - [ ] Subtask 2.2 (GREEN): implement `_is_close_command()`
  - [ ] Subtask 2.3 (RED): tests for the gating behavior end to end via `main()`: a JIRA-backed story with no ack marker → `permissionDecision: "deny"` with a non-empty `additionalContext` mentioning `story-close`/`SKILL.md`; the same story with the ack marker present → `permissionDecision` is **not** `"deny"` (either absent entirely, i.e. falls through to the existing rewrite-or-no-op path, or `"allow"`) **and** the marker file no longer exists afterward (consumed); a non-JIRA story (or no `.story.yaml` at all) → never gated regardless of the marker; `--dry-run` on the assembler → never gated even with no marker and a JIRA-backed story
  - [ ] Subtask 2.4 (GREEN): implement the gate in `main()`'s existing `Bash` branch — check `_is_close_command()` + JIRA-backed (`read_manifest()`'s `source_of_truth`/`jira_issue_key`) *before* the existing test/build-command rewrite logic; on deny, `return 0` immediately (print the deny JSON, skip the rest of the Bash branch entirely) so the two mechanisms never both fire for the same call
  - [ ] Subtask 2.5: update this file's module docstring — the existing "Returns 0 unconditionally... metrics capture must never [block the tool call]" claim needs a narrow, explicit carve-out for this one new case, so a future reader doesn't treat this story's deny path as a violation of that rule

- [ ] Task 3: `.claude/skills/story-close/SKILL.md` — step 6 creates the marker; document the new backstop (AC: 1, 2)
  - [ ] Subtask 3.1: extend step 6 with an explicit sub-step, immediately before running the close command: create the ack marker (`touch .story-close-ack`, with the PowerShell equivalent noted for Windows users without a `touch` alias) — runs every time step 6 runs, regardless of whether step 4 was confirmed or declined (step 6's own "always, last, unconditionally" framing is unchanged)
  - [ ] Subtask 3.2: add a short paragraph near the top (after the existing "Real limitation, not a design gap" note) explaining the new deterministic backstop in plain terms: a `PreToolUse` hook (Story 6.8) now denies the two close commands outright for a JIRA-backed story unless this skill's own step 6 has already created the marker — so even a raw pasted command gets redirected back to this skill's flow, not silently skipped
  - [ ] Subtask 3.3: a one-line caveat in Boundaries: this is a reliability nudge, not tamper-proofing — the hook can only see that the marker exists, not that steps 3-5 were genuinely followed

- [ ] Task 4: `tools/setup-hooks.py` — ship the new `.gitignore` entry (AC: 2)
  - [ ] Subtask 4.1: add `.story-close-ack` to `GITIGNORE_ENTRIES` — a local, single-use marker, same "never git-tracked" reasoning as the other four entries
  - [ ] Subtask 4.2: rename `tests/test_setup_hooks.py::test_fresh_install_creates_gitignore_with_all_four_entries` to stay accurate now that there are five (the test body already iterates `GITIGNORE_ENTRIES` dynamically, so no assertion logic changes — just the now-stale name)

- [ ] Task 5: `tools/build-release/INSTALL.md` — document the new backstop briefly (AC: 1)
  - [ ] Subtask 5.1: a short addition to the JIRA flow's step 7 (or a new Known Limitations entry) noting that a raw/pasted close command may get denied-and-redirected on the first attempt for a JIRA-backed story — expected behavior, not an error, and following the redirect's instructions gets you to the same place `story-close` always intended

- [ ] Task 6: live verification (AC: 1, 2, 3, 4, 5)
  - [ ] Subtask 6.1: in a real Claude Code session against a real JIRA-backed test story (reuse the pattern from the user's own v0.11.0 pilot test — a real issue, real sub-tasks), paste the raw close command as a literal chat message with **no** ack marker present — confirm the tool call is genuinely denied, confirm `additionalContext` is visible to the assistant (i.e. it actually reacts and starts following `story-close`'s steps in the same turn, not a second user message), then confirm retrying the same command succeeds once the skill's step 6 has created the marker
  - [ ] Subtask 6.2: confirm a second, immediate re-run of the same close command (simulating a re-close) gets gated again — the marker was single-use and is gone
  - [ ] Subtask 6.3: confirm a docs-only story's close command is never gated (no marker ever created, no denial)
  - [ ] Subtask 6.4: run the full test suite (`uv run pytest -q`) to confirm no regressions

## Dev Notes

### Why this story exists (real bug, not a hypothetical)

Found 2026-07-23 during the user's own live pilot testing of the v0.11.0 release — [GitHub Issue #52](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/issues/52). The user pasted the exact close command `INSTALL.md`'s JIRA flow step 7 tells them to type, as a literal chat message. The assistant ran it directly via Bash with zero awareness of `story-close` — no sub-task discovery, no confirmation, no transition, no points sync. Root cause: `story-close`'s implicit trigger (Story 6.2's whole design premise) is a judgment call the assistant makes per turn from the skill's frontmatter `description`, not a deterministic interceptor. This story replaces "hope the model recognizes intent" with a real, code-enforced backstop.

### Research already done during story authoring (confirmed, not assumed)

- **The exact `PreToolUse` deny mechanism**, confirmed against Claude Code's real, current hook documentation (not memory, not a guess):
  ```json
  {
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "deny",
      "permissionDecisionReason": "<shown to the human/UI only>",
      "additionalContext": "<shown to the assistant model, wrapped as a system reminder>"
    }
  }
  ```
  printed to stdout with **exit 0** (not exit 2 — exit 2 is the stderr-as-reason path, not the JSON path). Valid `permissionDecision` values: `allow`, `deny`, `ask`, `defer`. **Critical, easy-to-get-wrong detail:** `permissionDecisionReason` is UI-only — the assistant model never sees it. Only `additionalContext` reaches the model, so the redirect instructions (telling the assistant to follow `story-close` and retry) **must** go in `additionalContext`, not `permissionDecisionReason`. Getting this backwards would silently reproduce the exact bug this story fixes (a message nobody but the human sees, so the assistant still doesn't react).
- **No new hook registration needed.** `tools/setup-hooks.py`'s `CLAUDE_EVENTS` already wires `PreToolUse` unconditionally (every Bash call reaches `pre_tool_use.py`; the script itself filters on `tool_name == "Bash"`) — this story is a pure extension of the already-shipped, already-tested Story 5.7/5.8 mechanism, not a new integration point.
- **`_events.py` has no existing full `.story.yaml` reader** — only `story_id()` (reads just that one key). `read_story_config()` already establishes the exact pattern needed (a flat-scalar dict reader) for the *other* file, `.story-config.yaml` — Task 1 mirrors it for the manifest rather than inventing a third parsing style.

### The marker-gate mechanism, and why it's shaped this way

A `PreToolUse` hook is a stateless-ish subprocess with no direct visibility into what the assistant did earlier in the conversation — it can't know "did the model actually run `story-close`'s discovery/confirmation/JIRA-sync steps" from the Bash call alone. The design resolves this with a single-use local marker file (`.story-close-ack`): `story-close`'s own step 6 creates it immediately before running the close command (regardless of whether the developer confirmed or declined the JIRA sync — step 6 already runs unconditionally either way); the hook only allows a close command through when that marker exists, and deletes it the moment it does (so a stale marker can never silently wave through a *future*, unrelated close).

This means:
- A raw pasted command with no marker → denied, with `additionalContext` pointing the assistant at the skill.
- A properly-invoked `story-close` flow → never actually blocked in practice, since its own step 6 creates the marker right before the gated command runs.
- Re-closing (e.g. after a fix, producing rev2/rev3 — already an established, supported pattern in this pipeline) goes through the gate again each time, which is fine: `story-close`'s own discovery step already handles "sub-task/parent already Done" gracefully.

**This is explicitly not adversarial-proof (AC 5).** The hook can't verify the skill's steps were genuinely followed, only that a file exists. That's an accepted, deliberate trade-off — the goal is fixing the *observed* failure mode (the assistant never even considering the skill), not defending against a model trying to cheat past its own instructions. Claude Code's own hook docs make the same point generally: "Pattern matching... is best-effort... don't rely on hooks alone for hard security boundaries."

### Architecture compliance (binding invariants)

- **FR5 (never block kickoff/close)** — nuance, not a violation: this story blocks a specific *tool call* to force the correct path, but the close command itself is never prevented from eventually running — it's redirected, not vetoed. `story-close`'s own step 6 ("always, last, unconditionally") is completely unchanged; this story only adds a marker-creation sub-step in front of it.
- **project-context.md §7 (no premature abstraction, no duplication)** — `read_manifest()` reuses `parse_scalar()`; the gate reuses the already-shipped `PreToolUse` registration and the already-confirmed JSON-decision mechanism from Story 5.8, nothing new invented.
- **MCP-unreachable-from-hooks constraint (binding across this whole project)** — unchanged and fully respected: the hook itself never touches JIRA. It only blocks/redirects; the actual JIRA sync still happens exclusively inside the assistant's own turn via `story-close`, which does have MCP access.
- **`pre_tool_use.py`'s own historical "never hard-block" rule** — this story is a deliberate, narrow, explicitly-documented exception (Task 2.5), not a silent departure from it.

### Source tree touched

```text
tools/hooks/_events.py                  UPDATE  new read_manifest() reader
tests/hooks/test_claude_hooks.py        UPDATE  new tests for read_manifest(), _is_close_command(), and the full gate/marker behavior
tools/hooks/claude/pre_tool_use.py      UPDATE  _is_close_command(), the marker-gate check in main(), docstring carve-out
.claude/skills/story-close/SKILL.md     UPDATE  step 6 creates the marker; new backstop explanation; Boundaries caveat
tools/setup-hooks.py                    UPDATE  new .gitignore entry
tests/test_setup_hooks.py               UPDATE  rename the now-stale "all_four_entries" test
tools/build-release/INSTALL.md          UPDATE  brief note on the new deny-and-redirect behavior
```

### Testing standards (project-context.md §5/§6)

Real RED/GREEN pytest surface (Tasks 1-2) in the existing `tests/hooks/test_claude_hooks.py` — mirror its established fixture conventions (`repo`, `feed_stdin`, `write_story_config`) rather than inventing new ones. Task 3/5 (`SKILL.md`/`INSTALL.md`) have no pytest surface, same as every other Epic 6 skill-instruction change — their Definition of Done is Task 6's live verification, which this story treats as non-optional given how directly it's fixing a real, user-reported production gap: a real Claude Code session must actually be denied, actually see and react to `additionalContext`, and actually succeed on retry — not just asserted from unit tests of the hook script in isolation.

### Project Structure Notes

Builds on the `epic-6-jira-lifecycle-sync` integration branch, not `main` — this story's own branch (`story/6.8-...`) should be cut from it and merged back into it, not `main`, same as every other Epic 6 story. Extends `tools/hooks/claude/pre_tool_use.py` and `tools/hooks/_events.py`, both already modified by Stories 2.3/5.7/5.8; extends `story-close/SKILL.md` (Story 6.2/6.4).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.8] — the ask, root cause, and suggested fix direction found during this story's own creation
- [Source: GitHub Issue #52] — the full repro from the user's real v0.11.0 pilot test
- [Source: tools/hooks/claude/pre_tool_use.py] — the existing Story 5.8 `PreToolUse` rewrite mechanism this story's gate sits alongside
- [Source: tools/hooks/_events.py#read_story_config] — the exact flat-YAML reader pattern `read_manifest()` (Task 1) mirrors
- [Source: .claude/skills/story-close/SKILL.md] — step 6, which this story extends with the marker-creation sub-step
- [Source: tools/setup-hooks.py#GITIGNORE_ENTRIES] — the existing local-state `.gitignore` list this story extends
- [Source: tests/hooks/test_claude_hooks.py] — existing `pre_tool_use` test conventions (`repo` fixture, `feed_stdin`, `write_story_config`) to extend, not reinvent
- [Source: https://code.claude.com/docs/en/hooks.md] — the real, current `PreToolUse` decision-control schema confirmed during this story's authoring (exact field names, exit-code requirements, and the `additionalContext`-vs-`permissionDecisionReason` visibility distinction)
- [Source: project-context.md] — FR5, §5, §6, §7

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

## Change Log

- 2026-07-23: Story drafted from epics.md's Epic 6.8 entry, with the exact `PreToolUse` deny/`additionalContext` mechanism confirmed via real documentation research (not assumed) before any code was planned. Status: backlog → ready-for-dev.
