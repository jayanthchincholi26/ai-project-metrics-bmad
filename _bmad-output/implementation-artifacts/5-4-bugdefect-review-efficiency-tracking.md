---
baseline_commit: eaf29b2
---

# Story 5.4: Bug/Defect + Review-Efficiency Tracking

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer and as the leadership audience reading `metrics-reports/`,
I want compile/test defects and peer-review defects captured automatically per story, with honest testing/review efficiency percentages,
so that defect data is a byproduct of normal work (never a separate logging chore) and the numbers are trustworthy — never fabricated when nothing was actually tracked.

## Background — how this design was reached

This story's mechanism was scoped by studying a reference tool (`aep-orchestrator`'s `developer_handover.md`/`orchestrator.js`) the user pointed to, **then correcting course once its actual source was read**: that tool's defect capture is **100% manual, in two disconnected rounds** — a developer-invoked `orchestrator.js bug <key> "..." "..."` CLI call per defect, and then a *separately, by-hand-tallied* `compileBugs testBugs reviewBugs` integer set typed again at `complete` time, with no code linking the two. There is no folder-scan, no automated detection anywhere in that reference implementation, despite the user's initial (reasonable, but incorrect) assumption that one existed. This story deliberately does **not** copy that model — the user's explicit goal is avoiding developer intervention entirely, which the reference tool doesn't actually achieve.

Two live facts were confirmed directly against this project's own architecture before finalizing scope (see AD references below):
1. **The official Atlassian Remote MCP server can create a real Jira Subtask** — confirmed with a real write (`AI-140` created as a Subtask under `AI-139`, status "To Do") via `createJiraIssue`, no personal API token needed (consistent with AD-4/NFR4's existing "no personal token" guarantee).
2. **`.story.yaml` does not currently persist the parent Jira issue key** — kickoff's JIRA path (`story-kickoff` step 4a) uses the issue key transiently to fetch fields, then discards it. This story's write-to-Jira half needs that key persisted; without it, defect subtasks would have no parent to attach to.
3. **MCP tools are reachable only from a live Claude Code assistant turn — never from a hook subprocess or a plain `uv run` script.** This is the load-bearing architectural constraint that shapes this story's scope split below: automatic hook-driven capture (compile/test) can only ever write locally; only an assistant-turn-driven flow (the review-defect logging convention) can also create a real Jira subtask in the same action.

## Scope split (read this before the ACs)

- **Compile/test defects: fully automatic, local-only.** Detected by extending the existing `PostToolUse` hook to watch Bash tool calls against a small project-configured command allowlist; a matched command's non-zero exit appends a local `defect.compile`/`defect.test` event. **No Jira subtask is created for these in this story** — that would require a new assistant-turn-driven "sync" step, deliberately deferred (see Non-Goals) rather than built speculatively.
- **Review defects: automatic as a byproduct of work already happening, dual-write (local + Jira).** Formalizes this project's own established practice (paste an external review → verify each finding against the diff → fix the real ones) so that fixing a *verified-real* finding also logs a `defect.review` event locally and, when `source_of_truth: jira` and a persisted issue key exist, creates a real Jira subtask — as part of the fix, not a new step the developer has to remember.
- **Known, explicit simplification:** compile/test defect counting is "one non-zero exit = one instance," with no fail→pass reconciliation across retries of the same broken command. A flaky or repeatedly-rerun failure is deliberately allowed to count more than once rather than building cross-event correlation logic speculatively.
- **Known, explicit ambiguity, resolved via null-with-reason (per the user's own stated preference):** zero `defect.*` events for a story can mean either "genuinely clean" or "nothing was ever tracked" (e.g. an older story that predates this feature, or a docs-only story where no PR review pass happened at all) — these are indistinguishable without a stronger signal this story does not attempt to add. `testing_efficiency`/`review_efficiency` are `null` with an explanatory `reason` in that case, never a fabricated 100%/0% (unlike the reference tool).

## Acceptance Criteria

1. **Given** a JIRA-backed story is kicked off (`source_of_truth: jira`)
   **When** `story-kickoff` writes `.story.yaml`
   **Then** the manifest gains a new field, `jira_issue_key` (the issue key the developer provided at step 4a, e.g. `AI-139`) — `null` for `confluence`/`docs-only` stories, since there is no Jira parent to attach anything to

2. **Given** `.story-config.yaml` declares `test_commands`/`build_commands` (new, optional keys — e.g. `test_commands: ["pytest", "npm test"]`, `build_commands: ["tsc --noEmit", "ruff check"]`)
   **When** a Bash tool call's command matches one of these patterns (a substring match against the invoked command line) **and** its exit code is non-zero
   **Then** the `PostToolUse` hook appends a `defect.test` (if matched by `test_commands`) or `defect.compile` (if matched by `build_commands`) event to `.story-events.jsonl` — **containing no command output, no stdout/stderr, nothing beyond the matched pattern name and timestamp** (privacy guard, same posture as every other field this hook already emits)

3. **Given** neither `test_commands` nor `build_commands` is configured (the default, absent state)
   **When** the hook runs
   **Then** it behaves exactly as it does today — no new event type is ever emitted without an explicit opt-in config, and the hook's existing `ai.claude-code.tool_use` emission and idle-detection `record_activity()` call are unaffected

4. **Given** an external review (e.g. a pasted Gemini PR review) has been verified finding-by-finding against the actual diff, and a finding is confirmed real and fixed
   **When** the fix is applied
   **Then** a `defect.review` event is appended locally (`uv run tools/log-defect/main.py --repo-root . --type review --summary "..." --description "..." [--points N] [--jira-subtask-key AI-140]`), and — only when `source_of_truth: jira` and `.story.yaml`'s `jira_issue_key` is present — a real Jira Subtask is created first (via the assistant's own `createJiraIssue` MCP call, the same mechanism confirmed working against this project's own JIRA site) with its resulting key passed into the script call so the local event records it too

5. **Given** this convention (AC 4) is a new practice, not obvious from existing code
   **When** this story is done
   **Then** it's documented as an explicit step in this project's own process docs (`project-context.md` or a small skill addition) — not left as tribal knowledge only visible in past chat transcripts

6. **Given** a story closes (the existing `uv run tools/snapshot-assembler/main.py` command — unchanged, no new step for the developer)
   **When** the snapshot assembler reduces the event log
   **Then** the envelope gains a new top-level section, `defect_metrics`, containing `{total_defects, compile_defects, test_defects, review_defects, testing_efficiency, review_efficiency, reason}` — `testing_efficiency = (compile_defects + test_defects) / total_defects × 100`, `review_efficiency = review_defects / total_defects × 100` (mirroring the reference tool's formulas, which the user confirmed are the right formulas even though its capture mechanism isn't copied) — all fields `null` with a `reason` string when zero `defect.*` events exist for the story (AD-10), never AEP's fabricated 100%/0% default

7. **Given** `ARCHITECTURE-SPINE.md`'s AD-3a currently fixes the envelope's top-level keys as an exact set
   **When** `defect_metrics` is added
   **Then** AD-3a is updated in the same PR to include it — same precedent Story 5.2 set when it added `estimated_cost`

8. **Given** `tools/metrics-report/main.py` and `tools/dashboard/main.py` currently render defect fields as literal placeholder text ("not yet tracked")
   **When** this story is done
   **Then** both render the real `defect_metrics` values when present, and the existing null-with-reason rendering convention (`"not tracked — <reason>"`) when absent — no new placeholder strings invented, reusing the pattern Stories 5.3/5.5 already established for every other optional field

## Non-Goals (explicitly deferred, not silently out of scope)

- **No Jira subtask sync for compile/test defects.** These are hook-captured (no live assistant turn, no MCP access — see the architectural constraint in Background). A future story could add an assistant-turn-driven "sync local defects to Jira" step at story-close time; this story does not build it speculatively.
- **No fail→pass reconciliation.** A defect is counted once per observed failing run of a matched command, not once per underlying root cause. Documented as a known simplification (see Scope split), not solved here.
- **No automatic detection of *which* review comment was fixed by *which* code change.** The assistant still verifies findings against the diff and decides what's real, exactly as today — this story only adds the logging side-effect to that existing judgment call, it doesn't try to automate the judgment itself.
- **No change to Story 4.1/4.3's distribution mechanism, no change to any other manifest field, no change to Phase-1/Phase-2 point estimation (AD-6).**

## Tasks / Subtasks

- [ ] Task 1: persist `jira_issue_key` at kickoff (AC 1)
  - [ ] Subtask 1.1 (RED): a manifest-writer test asserting `--jira-issue-key AI-139` produces `jira_issue_key: "AI-139"` in `.story.yaml`, and that it's `null` when omitted (confluence/docs-only paths)
  - [ ] Subtask 1.2 (GREEN): add `--jira-issue-key` to `tools/adapters/docs-only/main.py`'s writer (same optional-field pattern as `--name`/`--points-estimated`); update `.claude/skills/story-kickoff/SKILL.md` step 4a to pass it through, and step 5's writer-invocation docs

- [ ] Task 2: extend `PostToolUse` for compile/test defect capture (AC 2, 3)
  - [ ] Subtask 2.1 (RED): a hook test asserting a matched, failing Bash command (mocked `tool_response.exit_code != 0`, `tool_input.command` matching a configured pattern) emits `defect.compile`/`defect.test` with no command text/output in the payload; asserting a non-matched or successful command emits nothing new; asserting default (no `test_commands`/`build_commands` configured) behaves identically to today
  - [ ] Subtask 2.2 (GREEN): read `test_commands`/`build_commands` from `.story-config.yaml` (reuse the existing config-reading helper already used for `hourly_rate`/`ai_input_rate`); match `tool_input.get("command", "")` by substring against each configured pattern; on a match with non-zero `tool_response` exit code, emit the new event type via the shared `_events.emit()` — payload carries only the matched pattern string and nothing else sourced from `tool_input`/`tool_response`
  - [ ] Subtask 2.3: confirm the existing `ai.claude-code.tool_use` emission and `record_activity()` call are unconditional and unaffected — this is additive, not a replacement of the hook's existing behavior

- [ ] Task 3: `tools/log-defect/main.py` — the local-ledger writer for review defects (AC 4)
  - [ ] Subtask 3.1 (RED): a test asserting the script appends a well-formed `defect.review` event to `.story-events.jsonl` (or `.pending.jsonl` per the existing spool-fallback convention every other producer already follows) with `summary`, `description`, `points` (default 1, matching the reference tool's bug-subtask default), and `jira_subtask_key` (optional, `null` when omitted)
  - [ ] Subtask 3.2 (GREEN): implement the script — stdlib-only, PEP 723 metadata, same pattern as every other `tools/*/main.py` — this script itself **never calls MCP tools**; it only appends the local event. The Jira subtask creation happens as a separate, prior action the assistant performs directly (AC 4) before invoking this script with the resulting key

- [ ] Task 4: document the review-defect logging convention (AC 5)
  - [ ] Subtask 4.1: add the convention to `project-context.md` (or a small dedicated skill, whichever this project's existing structure favors on inspection) — precisely: after verifying a pasted review's finding is real and fixing it, create the Jira subtask first (if applicable), then run `log-defect` with the resulting key

- [ ] Task 5: snapshot assembler reduces `defect.*` events (AC 6, 7)
  - [ ] Subtask 5.1 (RED): tests for `defect_metrics_of()` — zero defect events → all fields `null` with a reason; a mix of compile/test/review events → correct counts and both efficiency percentages; confirm the formulas exactly match AC 6
  - [ ] Subtask 5.2 (GREEN): implement `defect_metrics_of()` in `tools/snapshot-assembler/main.py`, wire it into the envelope alongside `token_cost`/`estimated_cost`
  - [ ] Subtask 5.3: update `ARCHITECTURE-SPINE.md`'s AD-3a to add `defect_metrics` to the fixed top-level key set (AC 7), same precedent as Story 5.2's `estimated_cost` addition

- [ ] Task 6: report and dashboard render real defect data (AC 8)
  - [ ] Subtask 6.1: update `tools/metrics-report/main.py`'s `render_story()` and `tools/dashboard/main.py`'s `render_row()`/`aggregate_stats()` to read `defect_metrics` — real values when present, `"not tracked — <reason>"` when absent, removing the literal "not yet tracked" placeholder strings Stories 5.3/5.5 left in place for this

- [ ] Task 7: full regression and live E2E (AC 1-8)
  - [ ] Subtask 7.1: `uv run pytest` full suite green; `uv run ruff check .`; `uv run ruff format --check tools tests`
  - [ ] Subtask 7.2: live E2E in a real scratch repo — kick off a JIRA story with a real issue key, fabricate a matched-and-failing test command via the hook path, log a review defect (creating a real Jira subtask via MCP the same way `AI-140` was created during this story's design phase), close the story, confirm the snapshot's `defect_metrics` reflects reality, confirm the report and dashboard render it correctly

## Dev Notes

### Architecture compliance (binding invariants)

- **AD-3a** — this story adds a 9th top-level envelope key (`defect_metrics`), updated in the same PR (Task 5.3), same precedent as Story 5.2's `estimated_cost`.
- **AD-4/NFR4** — Jira subtask creation goes through the already-connected Atlassian Remote MCP server (OAuth), confirmed working with a real write during this story's design phase. No personal API token is introduced by this story.
- **AD-10** — `defect_metrics`'s null-with-reason behavior on zero events is this story's central AD-10 compliance point, explicitly chosen over the reference tool's fabricated 100%/0% default (user's own call, made explicitly during scoping).
- **Privacy guard (existing, `post_tool_use.py`'s own docstring)** — `tool_input`/`tool_response` content is never emitted verbatim; this story's hook extension reads them only to test a match and an exit code, never persisting the command text or its output into any event payload.

### The one constraint everything else in this story is shaped by

MCP tools (`createJiraIssue`, etc.) are only callable from a live Claude Code assistant turn — never from a hook subprocess (`post_tool_use.py` et al.) or a plain `uv run tools/*/main.py` script invocation. This is why compile/test defects (hook-captured) stay local-only, while review defects (already logged during a live assistant turn, by design) can dual-write to Jira. Do not attempt to make the hook call MCP tools directly — it structurally cannot.

### Testing standards (project-context.md §5/§6)

- Standard `pytest` RED→GREEN for Tasks 1, 2, 3, 5 — follow this project's existing test patterns exactly (`tests/snapshot_assembler/test_reduce.py`'s `event()`/`write_events()`/`run()` helpers for Task 5; the existing hook test file's mocking pattern, if one exists, for Task 2 — check before inventing a new one).
- Task 4 (documentation) and the Jira-subtask-creation half of Task 3/4 have no automated test surface — verified via live E2E only (Task 7.2), same precedent as every MCP-touching story so far (1.6, story-kickoff's JIRA path).

### Source tree touched

```text
tools/adapters/docs-only/main.py         UPDATE  --jira-issue-key flag, new manifest field
.claude/skills/story-kickoff/SKILL.md    UPDATE  step 4a persists the issue key; step 5 writer invocation
tools/hooks/claude/post_tool_use.py      UPDATE  test_commands/build_commands matching, new event types
tools/log-defect/main.py                 NEW     local defect.review ledger writer (no MCP calls itself)
project-context.md                       UPDATE  documents the review-defect logging convention (or a new skill file, TBD during Task 4)
tools/snapshot-assembler/main.py         UPDATE  defect_metrics_of(), wired into the envelope
tools/metrics-report/main.py             UPDATE  render_story() reads real defect_metrics
tools/dashboard/main.py                  UPDATE  render_row()/aggregate_stats() read real defect_metrics
ARCHITECTURE-SPINE.md                    UPDATE  AD-3a envelope key set gains defect_metrics
tests/...                                UPDATE  new tests across adapters, hooks, snapshot-assembler, report, dashboard
```

### References

- [Source: D:\mywork\myPOCs\aep-orchestrator\docs\developer_handover.md, .agent\scripts\orchestrator.js] — the reference tool studied for this story; its QA efficiency *formulas* are reused (AC 6), its *manual, disconnected two-round capture mechanism* is explicitly not copied (see Background)
- [Source: tools/hooks/claude/post_tool_use.py] — the hook this story extends; its existing privacy guard (`tool_input` never emitted) is the model this story's own new fields must follow
- [Source: tools/adapters/docs-only/main.py] — the manifest writer this story adds one optional field to, following the exact pattern `--name`/`--points-estimated` already established
- [Source: .claude/skills/story-kickoff/SKILL.md, step 4a] — where the Jira issue key is already elicited (transiently) today; this story persists it, changing nothing else about that flow
- [Source: tools/snapshot-assembler/main.py] — where `token_cost_of()`/`estimated_cost_of()` already establish the null-with-reason pattern this story's `defect_metrics_of()` follows exactly
- [Source: ARCHITECTURE-SPINE.md, AD-3a] — the envelope-shape invariant this story extends (Task 5.3)
- [Source: project-context.md] — §1 stdlib-only (log-defect/main.py), §3 event shape (defect.* namespacing consistent with git.*/ai.<tool>.*), AD-10 reference (null-with-reason)

## Dev Agent Record

### Agent Model Used

_to be filled by dev-story_

### Debug Log References

_to be filled by dev-story_

### Completion Notes List

_to be filled by dev-story_

### File List

_to be filled by dev-story_
