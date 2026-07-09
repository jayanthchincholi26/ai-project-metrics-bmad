---
baseline_commit: b6395ba25dbf3347e147d646df27e06deb0701e5
---

# Story 1.5: Kickoff Manifest Declares Which AI Tool Is In Use

Status: done

## Story

As a developer,
I want my project to declare which AI tool it uses,
so that the capture side knows which adapter to activate without asking me on every story.

## Acceptance Criteria

1. **Given** a project config declares `ai_tool: claude-code` (today's only implemented adapter; extensible per AD-10), **when** the kickoff skill runs for any story in that project, **then** it writes the `ai_tool` field into `.story.yaml` the same way Story 1.2 writes `source_of_truth` — declared once per project by default, or per-story only if a team genuinely mixes tools.
2. AI-session capture producers (Story 2.3) read this field to know which adapter's event namespace (`ai.<tool>.*`) to emit under — so the manifest field name and value format are a stable contract.
3. An unset `ai_tool` config defaults to `claude-code`.

## Tasks / Subtasks

- [x] Task 1: Resolver resolves `ai_tool` (AC: 1, 3)
  - [x] `resolve.py`: read `ai_tool` from the same `.story-config.yaml`; absent file/key → `claude-code` with `ai_tool_declared: false`; declared value must match `^[a-z][a-z0-9-]*$` (it becomes the `ai.<tool>.*` event-namespace segment, AD-1a/AD-10) else exit 2 naming the format rule; ack gains `ai_tool`, `ai_tool_declared`, `ai_tool_implemented` (`true` only for `claude-code` — the sole adapter today, AD-10)
  - [x] An unimplemented-but-valid tool (e.g. `cursor`) resolves with `ai_tool_implemented: false` — same honest pattern as source_of_truth backends; never rejected, never silently swapped
- [x] Task 2: Writer records `ai_tool` in the manifest (AC: 1, 2, 3)
  - [x] `docs-only/main.py`: `--ai-tool` arg (default `claude-code`), validated with the same token regex (exit 2, nothing written, on violation); manifest key order becomes `story_id, source_of_truth, ai_tool, points, goal, sprint, description, created`
  - [x] The flag doubles as the per-story override for tool-mixing teams (AC 1); everything else about the writer unchanged
- [x] Task 3: SKILL.md wiring (AC: 1, 3)
  - [x] Step 1 dispatch note: the resolver ack now carries `ai_tool` — pass it to the writer as `--ai-tool <value>` in every variant (3/3a/3b); mention the per-story override only applies when a team genuinely mixes tools; if `ai_tool_implemented` is false, tell the developer capture will be reduced-confidence until that adapter exists (AD-10) but do NOT block kickoff
- [x] Task 4: Tests (AC: 1, 2, 3)
  - [x] `test_resolve.py`: unset → `claude-code`/declared false/implemented true; declared `claude-code` → declared true; declared `cursor` → declared true + implemented false; invalid format (`Claude Code`, empty) → exit 2; ack key set updated
  - [x] `test_docs_only.py`: default manifest carries `ai_tool: "claude-code"`; `--ai-tool cursor` recorded; invalid `--ai-tool` → exit 2 + nothing written; `MANIFEST_KEYS` order updated
- [x] Task 5: Full regression + lint (all ACs)

## Dev Notes

- **Scope:** manifest field + resolution only. The Claude Code capture adapter itself (events, hooks) is Story 2.3; do not emit anything. Valid-value set is deliberately open (extensible per AD-10) — only the *format* is validated, because the value becomes an event-namespace segment (`ai.<tool>.*`, AD-1a); `claude-code` is the only `implemented` tool.
- **UPDATE files:** `resolve.py` (add a parallel resolution block — same structure as source_of_truth's; keep read-only), `docs-only/main.py` (one arg + regex validation + manifest dict entry; atomicity/refusal/ack untouched), `SKILL.md` (thread `--ai-tool` through; no new elicitation — never ask which tool, same AD-4-style declare-once rule), `test_resolve.py`/`test_docs_only.py` (extend; update `MANIFEST_KEYS`).
- **Previous story intelligence:** same ack/exit/f-string/type-hint patterns; regex validation mirrors 1.3's finite-number lesson (validate the *format* of open-set input, don't enumerate); resolver's flat parser already handles BOM/quotes/comments — `ai_tool: cursor  # trial` must just work (existing `parse_scalar`).
- **Process:** branch `story/1.5-ai-tool-manifest-field`; PR `Story 1.5: Kickoff Manifest Declares Which AI Tool Is In Use` linking FR7 (CAP-7), AD-10, AD-1a; squash-merge; epics annotation inside PR; metrics provisional→final. This completes Epic 1's story set → epic flips to done at merge + §13 epic retro note.

### References

- [epics.md § Story 1.5](../planning-artifacts/epics.md) (lines 149–162) · [ARCHITECTURE-SPINE.md § AD-10, AD-1a](../planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md) · [SPEC.md § CAP-7](../specs/spec-pm-metrics-ai-engineering-flow/SPEC.md) · [project-context.md](../../project-context.md) · [1-2](1-2-project-level-source-of-truth-configuration.md)/[1-3](1-3-jira-adapter-auto-fills-kickoff.md) story files (resolution + validation patterns)

## Dev Agent Record

### Agent Model Used

claude-fable-5 (create-story context engineering + dev-story implementation)

### Debug Log References

- RED: 10 targeted failures (5 resolver + 3 writer + 2 contract-key/order updates) before implementation
- GREEN: 87/87; ruff check/format clean
- CLI E2E: BOM'd `ai_tool: cursor` config → `{ai_tool: "cursor", ai_tool_declared: true, ai_tool_implemented: false}`; writer `--ai-tool cursor` → manifest carries `ai_tool: "cursor"` after `source_of_truth`

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created
- `resolve.py` now resolves `ai_tool` from the same `.story-config.yaml` (single config-reading path): unset → `claude-code` with `ai_tool_declared: false` (AC 3); declared values validated against `^[a-z][a-z0-9-]*$` since the value becomes the `ai.<tool>.*` event-namespace segment (AD-1a); unimplemented-but-valid tools (e.g. `cursor`) resolve honestly with `ai_tool_implemented: false` (AD-10) — never rejected, never swapped. Main() refactored to resolve both keys then emit one ack.
- Writer gained `--ai-tool` (default `claude-code`, same regex validated, exit 2 + nothing written on violation); manifest key order now `story_id, source_of_truth, ai_tool, points, goal, sprint, description, created` — the field Story 2.3's capture producers read (AC 2).
- SKILL.md threads the resolved `ai_tool` into every writer invocation, explains the reduced-confidence message for unimplemented tools (non-blocking), and documents that per-story override is only for genuinely tool-mixing teams (AC 1). Never asks which tool — declare-once, like source_of_truth.
- AC→test traceability: AC 1 → declared/cursor resolver tests + writer flag-recorded test; AC 2 → manifest key-order test + namespace-format validation tests (resolver + writer); AC 3 → unset-default tests (resolver + writer default).
- **Epic 1 complete** — this was the epic's final story (5/5).

### Change Log

- 2026-07-09: Story 1.5 implemented — ai_tool resolution (resolver), --ai-tool manifest field (writer), skill wiring. 10 new tests (87 total). Status → review. Epic 1's final story.
- 2026-07-09: Gemini review of PR #9 returned zero findings — first clean §9 pass of the project. No fixes, no declines. Logged on the PR.
- 2026-07-09: PR #9 squash-merged to `develop` (e786ef6). Status → done. **Epic 1 complete (5/5).**

### File List

- tools/adapters/resolve.py (modified — ai_tool resolution, docstring, main() refactor)
- tools/adapters/docs-only/main.py (modified — --ai-tool flag + validation + manifest field)
- .claude/skills/story-kickoff/SKILL.md (modified — ai_tool threading + reduced-confidence note)
- tests/adapters/test_resolve.py (modified — 5 new tests + ack contract keys)
- tests/adapters/test_docs_only.py (modified — 3 new tests + key order)
- _bmad-output/implementation-artifacts/1-5-kickoff-manifest-declares-which-ai-tool-is-in-use.md (modified — this story file)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — status transitions)
- _bmad-output/planning-artifacts/epics.md (modified — §12 annotation, inside PR)
