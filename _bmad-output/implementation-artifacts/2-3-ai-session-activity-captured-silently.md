---
baseline_commit: 43d93e9975be55af02f1a27d4fbfa504c7eb92db
---

# Story 2.3: AI Session Activity Captured Silently

Status: done

## Story

As a developer using Claude Code,
I want my AI session activity (tool use, prompts, token usage) captured automatically,
so that cost and phase metrics exist without manual reporting.

## Acceptance Criteria

1. **Given** Claude Code hooks are configured (Story 2.1), **when** an AI session runs, **then** it appends `ai.claude-code.*` namespaced events via the normalized AD-10 adapter shape — same fixed envelope as 2.2, `source: "ai"`.
2. A signal Claude Code cannot report is emitted **null-with-reason**, never defaulted to zero (AD-10) — concretely: hooks expose no per-session token usage, so `session_end` carries `token_cost: null` + `token_cost_reason`.
3. A failed append follows the same retry-then-surface rule as Story 2.2 (AD-9) — and **no Claude hook ever exits non-zero** (a PreToolUse exit 2 would block the developer's tool call; capture must never break the dev flow — the commit-msg precedent, extended).

## Tasks / Subtasks

- [x] Task 1: Emitter extraction (USER-APPROVED architecture decision — shared module + spine amendment) (AC: 1, 3)
  - [x] Move `tools/hooks/git/_events.py` → `tools/hooks/_events.py`; `emit(source, event_type, payload)` gains the `source` parameter (`"git"` | `"ai"`); everything else (envelope, O_APPEND single-write, pending spool, 4-attempt retry, stderr surface) unchanged
  - [x] Add `read_stdin_json() -> dict` helper: `json.loads(sys.stdin.read() or "{}")`, tolerant of empty/malformed stdin (returns `{}`) — Claude Code passes hook input as JSON on stdin
  - [x] Refactor the four git hooks: one documented bridge line `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` before `import _events`; call sites pass `"git"`; delete `tools/hooks/git/_events.py`
  - [x] Update `tests/hooks/test_git_hooks.py` for the new location/signature — all 17 existing behaviors must stay green unchanged
- [x] Task 2: Spine amendment (same PR, §12 lockstep) (AC: 1)
  - [x] `ARCHITECTURE-SPINE.md`: Structural Seed gains `tools/hooks/_events.py  # shared emitter (AD-1/1b/9), source-parameterized; hooks reach it via a one-line documented sys.path bridge`; bump frontmatter `updated:`; one sentence in the Stack table row for hooks noting the sanctioned shared helper
  - [x] Comment on closed Issue #7: superseded by this deliberate amendment (link PR)
- [x] Task 3: Six real Claude Code producers replacing the 2.1 placeholders (AC: 1, 2, 3)
  - [x] Common shape: read stdin JSON via `_events.read_stdin_json()`; emit; **`return 0` unconditionally** (PreToolUse exit 2 blocks the tool call; other events' non-zero exits surface errors into the session — never acceptable for capture loss; stderr from `emit` is the AD-9 visibility)
  - [x] `session_start.py` → `ai.claude-code.session_start`, payload `{session_id}`
  - [x] `session_end.py` → `ai.claude-code.session_end`, payload `{session_id, token_cost: null, token_cost_reason: "claude-code hooks do not report token usage"}` — the AC 2 null-with-reason, a real null the dashboard must distinguish from zero
  - [x] `pre_tool_use.py` → `ai.claude-code.tool_start`, payload `{session_id, tool_name}` — **NEVER tool inputs** (may contain secrets/credentials; NFR4 spirit)
  - [x] `post_tool_use.py` → `ai.claude-code.tool_use`, payload `{session_id, tool_name}`
  - [x] `user_prompt_submit.py` → `ai.claude-code.prompt`, payload `{session_id, prompt_chars}` — **length only, never prompt content** (privacy; the event log is local but shareable-adjacent)
  - [x] `stop.py` → `ai.claude-code.stop`, payload `{session_id}`
  - [x] Missing stdin fields → honest nulls (e.g. `session_id: null`), event still emitted
- [x] Task 4: Namespace decision, documented (AC: 1)
  - [x] Events emit under `ai.claude-code.*` **always** — these hooks ARE the Claude Code adapter; facts beat declarations. Story 1.5's manifest `ai_tool` field tells the *skill and assembler* which adapter family is expected; a declared/actual mismatch stays detectable rather than falsified. Document this reading of the 1.5 AC in `_events.py` or the hook docstrings (one place, referenced)
- [x] Task 5: Tests `tests/hooks/test_claude_hooks.py` (AC: 1, 2, 3)
  - [x] Same loading pattern as test_git_hooks (register `_events` in `sys.modules` first); monkeypatch `read_stdin_json`/`repo_root`; `RETRY_DELAY_SECONDS = 0`
  - [x] Envelope: five keys, `source == "ai"`, `ai.claude-code.*` types (AC 1)
  - [x] `session_end` carries `token_cost: null` AND a non-empty `token_cost_reason` (AC 2)
  - [x] Tool events carry tool_name but the payload has NO input/arguments keys even when stdin includes `tool_input` (secrets guard); prompt event carries `prompt_chars` but never the prompt text even when stdin includes it (assert the raw text absent from the event file)
  - [x] Missing/empty/malformed stdin → nulls, event still emitted, exit 0
  - [x] Pre-manifest → pending spool with `story_id: null` (shared path, but assert once for the ai family)
  - [x] AD-9: total append failure → stderr `METRICS CAPTURE FAILED` AND **return 0** for every one of the six hooks (AC 3 — differs from post-commit's exit 1!)
  - [x] Also update `tests/test_setup_hooks.py::test_all_claude_placeholder_hooks_exit_0` — the placeholders are gone; rework/remove per what it still meaningfully asserts (likely: delete, superseded by the new suite)
- [x] Task 6: Full regression + lint + CLI E2E (all ACs)
  - [x] 115+ tests green, ruff clean
  - [x] CLI E2E: `echo '{"session_id":"s-1","tool_name":"Bash"}' | uv run tools/hooks/claude/post_tool_use.py` against a scratch repo with a manifest → one `ai.claude-code.tool_use` event; and a git commit E2E re-run proving the refactored git family still captures

## Dev Notes

- **The architecture decision is made and user-approved** (this session): ONE emitter at `tools/hooks/_events.py`, source-parameterized, one-line sys.path bridge in each hook, spine amended in the same PR. Do not re-litigate; do not use any other sharing mechanism. Issue #7 closes-as-superseded with a comment.
- **UPDATE files (read-before-touch):** `tools/hooks/git/_events.py` (moves — content is current as of PR #11, includes the retry ladder and BOM-tolerant story_id reader), the four git hooks (import + call-site change ONLY; payloads/behavior byte-identical), the six claude placeholders (2.1 shape), `tests/hooks/test_git_hooks.py` (loader paths + emit signature), `tests/test_setup_hooks.py` (placeholder test now obsolete), `ARCHITECTURE-SPINE.md` (Structural Seed + Stack row + `updated:` — smallest possible diff).
- **Claude Code hook reality:** hook input arrives as JSON on stdin (fields incl. `session_id`, `hook_event_name`, `tool_name`, `tool_input`, `prompt` depending on event). `settings.json` wiring from 2.1 is already correct — commands and filenames DO NOT change, so `setup-hooks.py` and its tests need zero edits (verify, don't touch).
- **Two privacy guards are non-negotiable:** no `tool_input` (secrets can appear in tool arguments — NFR4 spirit), no prompt text (only `prompt_chars`). Test both by asserting the sensitive string is absent from the written event file, not just absent from the payload dict.
- **Exit-code table (document in each docstring or once in _events):** git post-* → 1 on final failure (harmless, honest); git commit-msg → 0 always (abort risk); **claude all six → 0 always** (block/disrupt risk). AD-9 visibility = stderr in every case.
- **token_cost null-with-reason is the AC showcase** — a future transcript-parsing enhancement could compute real usage from `transcript_path`, but that is explicitly OUT of scope (would need transcript-format coupling; note as a possible future story, don't build).
- **Previous story intelligence (2.2):** loading pattern for sibling modules in tests; counting-fake for retry boundaries (reuse the helper shape); real-git E2E recipe; Gemini watches DRY (this story resolves it), import placement, and hallucinated findings (grep-verify).
- **Process:** branch `story/2.3-claude-session-capture`; PR `Story 2.3: AI Session Activity Captured Silently` linking FR1/FR7 (CAP-1/CAP-7 capture side), AD-10, AD-1a, AD-9, NFR1 (hooks only — no Claude Code internals touched); squash-merge; epics annotation inside PR; metrics provisional→final; CI green.

### References

- [epics.md § Story 2.3](../planning-artifacts/epics.md) (lines 197–209) · [ARCHITECTURE-SPINE.md § AD-10, AD-1a, Stack (six wired events)](../planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md) · [SPEC.md § CAP-7](../specs/spec-pm-metrics-ai-engineering-flow/SPEC.md) · [project-context.md](../../project-context.md) §3/§4/§5–6 · [2-2 story file](2-2-git-activity-captured-silently-while-you-work.md) (emitter internals + escalation note) · Issues #7 (superseded), #2/#5 (still-declined packaging)

## Dev Agent Record

### Agent Model Used

claude-fable-5 (create-story context engineering)

### Debug Log References

- RED: collection errors (shared `_events.py` absent); GREEN: 125/125 after emitter move + 6 producers
- **The stdin decode saga (dev E2E gold):** unit suite green but the live PowerShell pipe yielded null payloads. Layer 1: pipes prepend a UTF-8 BOM. Layer 2: the "fix" and its test both used an *invisible literal* BOM char that silently became an empty string — `lstrip("")` no-op, test passing vacuously. Layer 3 (root cause, found via instrumented probe): uv-managed Python decodes stdin as **cp1252**, so the BOM bytes arrive as three mojibake chars, not `﻿`. Final fix: `stdin.reconfigure(encoding="utf-8-sig")` before reading + explicit-escape strip fallbacks; codepoints byte-verified in source. Live pipe then parsed correctly: `session_id`, `tool_name`, `prompt_chars` all real.
- Final: 127/127; ruff clean; live E2E: ai + git events interleaved in ONE `.story-events.jsonl` under the same story_id; secret string from `tool_input` asserted absent from the log

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created
- Emitter extracted to `tools/hooks/_events.py` per the user-approved decision: `emit(source, type, payload)`, one retry ladder/parser/append across both families; hooks reach it via the one-line sys.path bridge (E402 per-file-ignore documented in pyproject); `tools/hooks/git/_events.py` deleted; all 17 git-hook behaviors green unchanged.
- Spine amended in the same PR (§12): Structural Seed shows `_events.py`, Stack table documents the sanctioned exception, `updated:` bumped. Issue #7 to be commented as superseded when the PR exists.
- Six real Claude producers: session_start/session_end/tool_start/tool_use/prompt/stop under `ai.claude-code.*`; `session_end` carries `token_cost: null` + reason (AC 2's null-with-reason showcase); **privacy guards tested at the file level** — `tool_input` and prompt text never reach the event log; all six return 0 unconditionally (AC 3).
- `read_stdin_json()`: utf-8-sig reconfigure + BOM/mojibake fallbacks (see Debug Log — a genuine field bug that would have silently nulled every Windows capture).
- AC→test traceability: AC 1 → envelope/namespace/per-hook-type tests + live-pipe E2E; AC 2 → token-null-with-reason test; AC 3 → all-six-return-0-on-total-failure test + stderr surfacing count.

### Change Log

- 2026-07-10: Story 2.3 implemented — shared emitter (user-approved spine amendment), six Claude producers with privacy guards, stdin cp1252/BOM fix. 12 new tests (127 total). Status → review.
- 2026-07-10: Gemini review of PR #12 — zero findings (second clean §9 pass; the one that closes the DRY thread). Reviewer highlighted privacy enforcement, emitter consolidation, BOM handling, fail-safe exits.
- 2026-07-10: PR #12 squash-merged to `develop` (8c8a0c6). Status → done.

### File List

- tools/hooks/_events.py (new — moved from git/, source-parameterized, read_stdin_json)
- tools/hooks/git/_events.py (deleted)
- tools/hooks/git/post-commit.py, post-checkout.py, post-merge.py, commit-msg.py (modified — bridge + source arg)
- tools/hooks/claude/session_start.py, session_end.py, pre_tool_use.py, post_tool_use.py, user_prompt_submit.py, stop.py (modified — placeholders → real producers)
- tests/hooks/test_claude_hooks.py (new)
- tests/hooks/test_git_hooks.py (modified — shared-emitter loader)
- tests/test_setup_hooks.py (modified — placeholder test → existence check)
- pyproject.toml (modified — E402 per-file-ignore for the sanctioned bridge)
- _bmad-output/planning-artifacts/architecture/.../ARCHITECTURE-SPINE.md (modified — §12 amendment)
- _bmad-output/implementation-artifacts/2-3-ai-session-activity-captured-silently.md (modified — this story file)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — status transitions)
- _bmad-output/planning-artifacts/epics.md (modified — §12 annotation, inside PR)
