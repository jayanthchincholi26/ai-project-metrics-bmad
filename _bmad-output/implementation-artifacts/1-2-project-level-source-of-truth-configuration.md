---
baseline_commit: 71857039707c4d729fcd18508660be7dc733103e
---

# Story 1.2: Project-Level Source-of-Truth Configuration

Status: review

## Story

As a developer,
I want my project to declare its PM tool once,
so that I'm never asked which tool applies on every single story.

## Acceptance Criteria

1. **Given** a project config declares `source_of_truth: jira | confluence | docs-only`, **when** the kickoff skill runs for any story in that project, **then** it reads the declared value and behaves accordingly, without re-asking which backend applies.
2. An unset config (no config file, or no `source_of_truth` key) defaults to the docs-only behavior from Story 1.1.

## Tasks / Subtasks

- [x] Task 1: Implement the config resolver `tools/adapters/resolve.py` (AC: 1, 2)
  - [x] PEP 723 header + `from __future__ import annotations` + module docstring stating the AD-4 rule it implements (declared once, never re-asked per story) and the config file decision (`.story-config.yaml`, repo root, flat YAML, committed)
  - [x] `argparse` CLI: `--repo-root DIR` (required, must exist — exit 2 otherwise)
  - [x] Read `{repo-root}/.story-config.yaml` if present: flat `key: value` lines; skip blanks/`#` comments/non-`key: value` lines; accept bare or JSON-quoted values
  - [x] Resolution rules: file or key absent → `docs-only` with `declared: false`; value in `{jira, confluence, docs-only}` → that value with `declared: true`; anything else (including empty value) → stderr + exit 2, listing legal values — never guess, never fall back silently
  - [x] Success ack (one JSON line, stdout, exit 0): `{"ok": true, "source_of_truth": <v>, "declared": <bool>, "implemented": <v == "docs-only">, "config": <path-or-null>}` — `implemented` widens to jira/confluence in Stories 1.3/1.4
  - [x] Read-only script: never writes or creates any file
- [x] Task 2: Update `.claude/skills/story-kickoff/SKILL.md` to resolve-then-dispatch (AC: 1, 2)
  - [x] New first step: run `uv run tools/adapters/resolve.py --repo-root <repo>` before anything else; never ask the developer which backend applies (AC 1)
  - [x] Dispatch: `docs-only` → existing Story 1.1 flow unchanged; `jira`/`confluence` → tell the developer the backend is declared but its adapter arrives in Story 1.3/1.4, and stop (no silent docs-only fallback); resolver exit 2 → surface stderr verbatim and stop
  - [x] Preserve all Story 1.1 behaviors: early double-kickoff refusal, three-field elicitation with re-prompt rule, verbatim error surfacing, boundaries section
- [x] Task 3: Tests `tests/adapters/test_resolve.py` (AC: 1, 2)
  - [x] No config file → `docs-only`, `declared: false`, `config: null`, exit 0 (AC 2)
  - [x] Config file without the key → same default (AC 2)
  - [x] Declared `docs-only` / `jira` / `confluence` → resolved with `declared: true`; `implemented` true only for docs-only (AC 1)
  - [x] JSON-quoted value, surrounding whitespace, comment lines, unrelated keys → all tolerated
  - [x] Invalid value (e.g. `gitlab`) and empty value → exit 2, stderr names legal values, no stdout ack
  - [x] Nonexistent `--repo-root` → exit 2
  - [x] Ack is exactly one JSON line with the five contract keys
- [x] Task 4: Regression — full suite green; docs-only kickoff E2E unchanged (AC: 2)

### Review Follow-ups (AI)

External LLM review (Gemini, via PR #4) triaged per project-context §9 — 2026-07-09:

- [x] [AI-Review][Med] Inline comments broke bare-value parsing (`source_of_truth: jira # note` → invalid) — fixed via `parse_scalar()`: bare values end at ` #`; paired quotes shield `#`. Test-first repro also exposed an uncaught `JSONDecodeError` crash on `"quoted"  # comment` (worse than reported). 4 regression tests added.
- [x] [AI-Review][Low] Single-quoted values unsupported — fixed in the same `parse_scalar()` (paired single/double quotes; deliberately not a blind `.strip("'\"")`, which would accept mismatched quotes)
- [x] [AI-Review][Low] `read_config() -> dict[str, str]` inaccurate while `json.loads` could return non-str — resolved by construction: `json.loads` removed from parsing; the hint is now exact
- Declined — add `__init__.py`/PYTHONPATH so tests import `tools.adapters.resolve` natively: same theme as Issue #2; `tools/` holds `uv run` script entry points, not a package, and one uniform `importlib` loading pattern across the test suite beats two mechanisms. Pre-documented in this story's Dev Notes (Previous Story Intelligence). Logged as a wontfix issue per the §9 convention.

## Dev Notes

### Scope — what this story is and is not

- This story adds **config reading + dispatch only**. Do NOT build: the JIRA adapter (1.3), the Confluence adapter (1.4), the `ai_tool` field (1.5 — same config file, but its key is out of scope here), any event/hook logic (Epic 2).
- Do NOT modify `tools/adapters/docs-only/main.py`: it *is* the docs-only backend; its hardcoded `source_of_truth: "docs-only"` manifest field stays correct. The resolver decides *which* backend runs; the backend decides what it writes.
- Config file name/location is a this-story decision (spine fixes only "project-level config alongside project-context.md"): **`.story-config.yaml` at repo root, flat YAML, committed** (shared team declaration — unlike `.story-events.jsonl`, it is NOT git-ignored). Story 1.5 will add `ai_tool` to the same file; keep the parser generic flat-key reading, but expose only `source_of_truth` behavior here (no premature abstraction).

### Architecture compliance (binding invariants)

- **AD-4** — declared **once** per project; the kickoff skill reads it and never re-asks per story. The resolver is the single reading path; the skill must not prompt for backend choice under any circumstance.
- **Unimplemented-but-valid backends surface honestly** (AD-9 philosophy): `jira`/`confluence` are legal declarations today whose adapters don't exist yet — kickoff must say so and stop, never silently substitute docs-only, and never treat them as invalid config.
- **Exit codes load-bearing / ack pattern / explicit addressing** (project-context §3): identical contract to Story 1.1 — one JSON line on success, exit 0/2, `--repo-root` required, no cwd assumptions.
- **Never trust external input** (§3): the config file is user-editable — validate the value against the closed set before acting on it.
- **Stdlib only** (§1): the flat-YAML reading trick mirrors 1.1's writing trick (bare or `json.loads`-parsed quoted scalars). No PyYAML (declined in review — Issue #3).

### Source tree touched

```text
tools/adapters/resolve.py              NEW     config resolver (this story's core)
.claude/skills/story-kickoff/SKILL.md  UPDATE  resolve-then-dispatch flow
tests/adapters/test_resolve.py         NEW     pytest suite
```

**UPDATE-file analysis — `.claude/skills/story-kickoff/SKILL.md` (current state, from Story 1.1):**
- Does today: refuses double kickoff early (checks `.story.yaml` existence); elicits points/goal/sprint with the AC-3 re-prompt rule; invokes `uv run tools/adapters/docs-only/main.py` with explicit `--repo-root`; relays JSON ack; surfaces non-zero-exit stderr verbatim and re-elicits; Boundaries section (skill never writes the manifest; no event files; manifest is committed).
- This story changes: adds the resolver as the new first step and a dispatch table; removes the "docs-only only / Story 1.2 pending" scoping note.
- Must be preserved: every behavior listed above — the docs-only path after dispatch is byte-for-byte the same flow.

### Previous Story Intelligence (Story 1.1)

- **Patterns established (copy, don't reinvent):** `main(argv) -> int` entry testable in-process; `fail(msg) -> 2` helper; one-line JSON ack via `json.dumps`; PEP 723 header block; `from typing import Any` for parameterized dict hints. Model files: `tools/adapters/docs-only/main.py` and `_bmad/scripts/memlog.py` (pattern source only — never import from `_bmad/`).
- **Test loader:** hyphen-free `resolve.py` sits in `tools/adapters/` (no package `__init__.py` exists), so keep the established `importlib.util.spec_from_file_location` loader from `tests/adapters/test_docs_only.py` for consistency — don't introduce a packaging change just to import one module.
- **Review learnings applied forward:** single shared `now` for any correlated timestamps (no timestamps needed in this story — resolver is read-only); f-strings over `.format()`; ruff format runs on everything (`uv run ruff format tools tests` before finishing).
- **Declined-findings convention (§9, adopted after 1.1):** any review finding declined during this story's review gets a `Review-declined:` GitHub issue, `wontfix` label, closed as not-planned.
- **Tooling already bootstrapped:** pyproject.toml, pytest 8.3.5, ruff 0.9.6 all exist — no tooling tasks this story. Run: `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check tools tests`.

### Testing the resolver

- Mirror path: `tests/adapters/test_resolve.py`; load via `importlib` (same pattern as `test_docs_only.py`).
- Call `main(argv)` in-process with `tmp_path`; write config fixtures with plain `Path.write_text`.
- One behavior per test, sentence names, Arrange/Act/Assert (§6). AC 1 → declared-value tests + the skill's no-re-ask instruction (conversational half documented, script half tested). AC 2 → the two default tests.
- The dispatch behavior for jira/confluence (skill layer) is conversational — the `implemented: false` ack field is its testable proxy; state this mapping in the PR.

### Process requirements

- Branch: `story/1.2-source-of-truth-config` off `develop`. PR title: `Story 1.2: Project-Level Source-of-Truth Configuration`. PR links FR4 (CAP-4), AD-4; squash-merge this time (§10 — 1.1 was merge-commit by accident, logged).
- Every AC maps to at least one test; LLM review (§9, external LLM) + human sign-off (§7) before merge; annotate `epics.md` inside the PR this time (§12).

### Project Structure Notes

- `tools/adapters/resolve.py` is a small addition beyond the spine's Structural Seed listing (seed shows only backend dirs under `adapters/`); rationale: backend *selection* is adapter-family logic and belongs beside the backends. Flagged here per the variance-with-rationale rule; no spine change needed (the seed is a seed, not an exhaustive manifest).
- `.story-config.yaml` joins `.story.yaml` as a committed root-level file; the git-ignored trio (`.story-events.jsonl`, `.active-story`) is untouched.

### References

- [epics.md § Story 1.2](../planning-artifacts/epics.md) — ACs (lines 110–121); Epic 1 context
- [ARCHITECTURE-SPINE.md § AD-4](../planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md) — declare-once rule, adapter families
- [SPEC.md § CAP-4](../specs/spec-pm-metrics-ai-engineering-flow/SPEC.md) — success = never asked per story
- [project-context.md](../../project-context.md) — §1 stdlib-only, §3 ack/exit codes/never-trust-input, §5–6 testing, §8–12 process
- [1-1 story file](1-1-create-the-story-manifest-via-docs-only-kickoff.md) — patterns, review follow-ups, declined findings (Issues #2, #3)

## Dev Agent Record

### Agent Model Used

claude-fable-5 (create-story context engineering + dev-story implementation)

### Debug Log References

- RED: `uv run pytest` → collection error, `tools/adapters/resolve.py` absent (test validity confirmed)
- GREEN: 31/31 (19 prior + 12 new) after implementation
- E2E caught a real defect the unit suite missed: PowerShell 5.1 `Set-Content -Encoding utf8` writes a UTF-8 BOM; the first config key parsed as `﻿source_of_truth` and silently fell back to docs-only — the exact silent misconfiguration AD-4 forbids. Fixed with `utf-8-sig` decoding + regression test `test_utf8_bom_config_is_parsed`. Final: 32/32
- E2E after fix: unset → docs-only/declared:false; BOM'd `jira` → jira/declared:true/implemented:false; BOM'd `gitlab` → exit 2 naming legal values; docs-only kickoff regression → ack + exit 0
- Lint: `uv run ruff check .` + `ruff format --check tools tests` clean

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created
- Implemented `tools/adapters/resolve.py`: reads `.story-config.yaml` (flat YAML, BOM-tolerant, bare or JSON-quoted scalars, comments/unrelated keys ignored), resolves `source_of_truth` per AD-4 — absent file/key → docs-only `declared: false`; legal value → `declared: true` with `implemented` flag (docs-only only, until 1.3/1.4); invalid/empty value → exit 2 naming legal values. Read-only, ack pattern, explicit `--repo-root`.
- Updated `story-kickoff` SKILL.md to resolve-then-dispatch: resolver runs first, never asks the developer for a backend (AC 1); jira/confluence declared-but-unbuilt → honest stop, no silent fallback; invalid config → stderr verbatim + stop. All Story 1.1 behaviors preserved verbatim (double-kickoff refusal, elicitation + re-prompt rule, writer invocation, boundaries).
- AC→test traceability: AC 1 → declared-value tests (docs-only/jira/confluence, quoting, BOM, tolerance) + no-re-ask instruction in SKILL.md (conversational half; `implemented: false` ack field is its testable proxy); AC 2 → no-config-file and no-key default tests + docs-only E2E regression.
- No new dependencies; `tools/adapters/docs-only/main.py` untouched as scoped.

### Change Log

- 2026-07-09: Story 1.2 implemented — config resolver, skill dispatch update, 13 new tests (32 total). BOM-handling defect found via E2E and fixed pre-review. Status → review.
- 2026-07-09: Addressed Gemini review of PR #4 — 3 fixed (inline-comment parsing incl. a latent `JSONDecodeError` crash, single-quote support, exact return hint), 1 declined with logged rationale (test packaging change). 36 tests passing.

### File List

- tools/adapters/resolve.py (new)
- tests/adapters/test_resolve.py (new)
- .claude/skills/story-kickoff/SKILL.md (modified — resolve-then-dispatch)
- _bmad-output/implementation-artifacts/1-2-project-level-source-of-truth-configuration.md (modified — this story file)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — status transitions)
