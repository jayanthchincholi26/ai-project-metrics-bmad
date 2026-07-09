---
baseline_commit: 0642acfe3f239713ae080b9240bd87bf314b3f01
---

# Story 1.1: Create the Story Manifest via Docs-Only Kickoff

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want to kick off a story and have my points/goal/sprint captured into a manifest, even when my project has no PM tool,
so that every downstream capture mechanism has a story identity to attach to.

## Acceptance Criteria

1. **Given** a project with no source-of-truth tool configured, **when** the developer runs the kickoff skill, **then** it prompts for story points confirmation, goal, and sprint, and writes them into `.story.yaml` with a generated `story_id`.
2. `.story.yaml` becomes the sole source other producers read the story ID from (AD-5) — it lives at the repo root, carries `story_id` as a top-level key, and no producer ever infers identity from branch name or ticket key.
3. If the developer submits without providing points, goal, or sprint, the kickoff skill re-prompts for the missing field rather than writing an incomplete manifest. The manifest writer script independently refuses (non-zero exit, nothing written) when any required field is missing or invalid — validation exists at both layers.

## Tasks / Subtasks

- [x] Task 1: Scaffold the docs-only manifest writer `tools/adapters/docs-only/main.py` (AC: 1, 2)
  - [x] PEP 723 header (`# /// script` / `requires-python = ">=3.8"` / `# ///`) + `from __future__ import annotations` — copy the exact top-of-file shape from `_bmad/scripts/memlog.py`
  - [x] `argparse` CLI: `--repo-root DIR` (required), `--points INT` (required), `--goal STR` (required), `--sprint STR` (required), `--description STR` (optional)
  - [x] Module docstring stating the AD-4 adapter contract this script fulfils (docs-only backend of `{points, goal, sprint, description}`)
- [x] Task 2: Generate `story_id` and write `.story.yaml` atomically (AC: 1, 2)
  - [x] `story_id` format: `story-{YYYYMMDD}-{uuid4().hex[:6]}` (e.g. `story-20260709-3fa2c1`) — unique, sortable, no PII; format is a this-story decision (spine doesn't fix it), document it in the module docstring
  - [x] Emit flat YAML by hand — **stdlib only, no PyYAML** (see Dev Notes → YAML without a YAML library)
  - [x] Fixed key order: `story_id, source_of_truth, points, goal, sprint, description, created`; `source_of_truth: docs-only`; `description` is `null` when not provided; `created` is ISO-8601 with local offset (`datetime.now().astimezone().isoformat(timespec="seconds")`)
  - [x] Atomic write: temp file → flush → `os.fsync` → `os.replace`, replicating `write_atomic()` from `_bmad/scripts/memlog.py:122-129` (copy the ~7-line pattern; do NOT import from `_bmad/`)
  - [x] Refuse to overwrite an existing `.story.yaml` (exit 2 with a clear stderr message) — re-kickoff would change story identity mid-story (AD-5); no `--force` flag (YAGNI)
- [x] Task 3: Validation and exit codes (AC: 3)
  - [x] Validate BEFORE any write: `points` must parse as int > 0; `goal`/`sprint` non-empty after `.strip()`; collapse internal newlines in free-text values to single spaces (memlog `cmd_append` precedent)
  - [x] Invalid/missing input → message to stderr, exit 2, `.story.yaml` never created (no partial writes, ever)
  - [x] Success → exactly one JSON ack to stdout: `{"ok": true, "story_yaml": "<abs path>", "story_id": "<id>"}`, exit 0 (ack pattern, project-context §3)
- [x] Task 4: Create the kickoff skill `.claude/skills/story-kickoff/SKILL.md` (AC: 1, 3)
  - [x] Human-bookend flow: elicit points confirmation, goal, sprint (description optional); re-prompt conversationally for any missing/blank field before invoking the script (AC 3 first layer)
  - [x] On complete input: run `uv run tools/adapters/docs-only/main.py --repo-root <repo> --points N --goal "..." --sprint "..."` and relay the JSON ack to the developer
  - [x] If the script exits non-zero, surface its stderr verbatim and re-elicit — never retry silently with altered values
  - [x] Keep the skill docs-only-only: config-driven adapter selection is Story 1.2; do not build a config reader here
- [x] Task 5: Bootstrap dev tooling — first implementation story (DoD §1, §5)
  - [x] Add minimal `pyproject.toml`: `[tool.ruff]` config (PEP 8 baseline) + `[dependency-groups] dev = ["pytest"]` — project-context §1 names "Story 2.1" for this, but its stated intent is *the first implementation story that needs it*, and with Epic 1 sequenced first, that story is this one; note the deviation in the PR description
  - [x] Verify `uv run ruff check .` and `uv run pytest` both run clean
- [x] Task 6: Tests `tests/adapters/test_docs_only.py` (AC: 1, 2, 3)
  - [x] Success path: `.story.yaml` created in `tmp_path` with all seven keys in fixed order, `source_of_truth: docs-only`, quoted string values, ack JSON on stdout, exit 0 (AC 1)
  - [x] `story_id` matches `^story-\d{8}-[0-9a-f]{6}$`; two runs in two dirs produce different IDs (AC 1, 2)
  - [x] Boundary: points `0`, `-1`, non-numeric, missing → exit 2 and no `.story.yaml` created (AC 3)
  - [x] Empty/whitespace-only `goal` or `sprint` → exit 2, nothing written (AC 3)
  - [x] Existing `.story.yaml` → exit 2, original file byte-identical after the attempt (AC 2)
  - [x] Multiline goal input → collapsed to a single line in the manifest
  - [x] Load the hyphenated-dir script in tests via `importlib.util.spec_from_file_location` (see Dev Notes → Testing the script)

### Review Follow-ups (AI)

External LLM review (Gemini, via PR #1) triaged per project-context §9 — 2026-07-09:

- [x] [AI-Review][Low] Midnight race: `story_id` date and `created` came from two separate `datetime.now()` calls — fixed with a single aware `now = datetime.now().astimezone()` passed to both; regression test `test_story_id_date_matches_created_date` added (also resolves the naive-vs-aware datetime smell)
- [x] [AI-Review][Low] Replace `.format()` with f-strings; parameterize `render()` hint to `dict[str, Any]` — applied
- Declined — `docs-only` → `docs_only` rename: the hyphenated path is fixed by the ARCHITECTURE-SPINE Structural Seed (consistent with `opsx-wrapper/`, `snapshot-assembler/`); scripts are `uv run` entry points, never package imports in production — the `importlib` loader in tests is the deliberate, documented trade-off. Revisit only via a spine change, not ad hoc in a story.
- Declined — introduce PyYAML/ruamel for unquoted YAML strings: stdlib-only is a hard rule (project-context §1); JSON-quoted scalars are valid YAML and the quoting is deliberate. A dependency addition requires explicit standards discussion, not a lint-level preference.

## Dev Notes

### Scope — what this story is and is not

- This story builds the **docs-only kickoff path only**: elicit three fields → validate → write `.story.yaml` with a generated `story_id`. It is the *default* behavior that Story 1.2's config layer falls back to when `source_of_truth` is unset.
- **Do NOT build in this story:** config file/reading (1.2), JIRA/Confluence adapters (1.3/1.4), the `ai_tool` manifest field (1.5), any event-log/spool/`.story-events.jsonl` handling (Epic 2), `.active-story` (Epic 3), `.gitignore` changes (the manifest is *committed*, not ignored — spine § Deployment).
- Pre-manifest event buffering is explicitly **not** kickoff's job: AD-1b assigns backfilling buffered events to the snapshot assembler (Story 2.4). The adversarial review's earlier draft (AD-5a) had kickoff flushing a spool — the final spine overrode that. Do not add spool logic here.
- No shared "adapter base class" or manifest-writer abstraction: §2 no-premature-abstraction. When 1.3/1.4 create real duplication, *that* story extracts the helper.

### Architecture compliance (binding invariants)

- **AD-5** — `.story.yaml` (repo root) is the sole source of story identity. This story creates that file; its `story_id` key is the contract every later producer reads. Never derive identity from branch/ticket.
- **AD-4** — the adapter contract is a normalized `{points, goal, sprint, description}` regardless of backend. Docs-only "fetches" by prompting the developer instead of calling an API, but must internally produce that exact four-field shape (plus manifest bookkeeping fields) so 1.3/1.4 slot in identically. No adapter-specific fields leak into `.story.yaml`.
- **AD-6a context (adversarial review):** PM-tool-native points and the future Phase-1 AD-6 estimate are *different numbers* and must never share a field. For docs-only the `points` field holds the developer-confirmed value; Story 2.5 will add the computed estimate as its own field. Don't name anything ambiguously (e.g. avoid `estimated_points` here).
- **Atomic writes always** (project-context §2): temp → flush → fsync → `os.replace`. Reference: [memlog.py write_atomic()](../../_bmad/scripts/memlog.py). In-place or incremental writes of `.story.yaml` are non-compliant.
- **Exit codes are load-bearing** (project-context §3): 0 = success + one-line JSON ack on stdout; 2 = validation/refusal with stderr message. Never swallow an exception and exit 0.
- **Explicit addressing** (project-context §3): `--repo-root` required; no cwd assumptions.

### YAML without a YAML library (critical guardrail)

Stdlib-only is a hard rule (project-context §1) — **PyYAML/ruamel are not available and must not be added.** The manifest is a flat key→scalar map, so emit it by hand:

- Strings: serialize with `json.dumps(value)` — a JSON string is valid YAML, which safely handles `:`, quotes, and unicode in free-text goal/sprint values.
- Ints: bare (`points: 5`). Absent description: `description: null`.
- One `key: value` per line, fixed order, trailing newline. Collapse newlines inside values *before* quoting (memlog `render()` precedent at [memlog.py:110-113](../../_bmad/scripts/memlog.py)).
- Example output:

```yaml
story_id: "story-20260709-3fa2c1"
source_of_truth: "docs-only"
points: 5
goal: "Ship docs-only kickoff manifest"
sprint: "Sprint 12"
description: null
created: "2026-07-09T14:30:00+05:30"
```

### Source tree touched (all NEW — no existing code is modified)

```text
tools/adapters/docs-only/main.py       NEW  manifest writer (this story's core)
.claude/skills/story-kickoff/SKILL.md  NEW  human-bookend elicitation skill
tests/adapters/test_docs_only.py       NEW  pytest suite
pyproject.toml                         NEW  ruff config + pytest dev group
```

No UPDATE files exist — this is the repo's first implementation story; the working tree currently contains only planning artifacts and BMad tooling (`_bmad/`, `_bmad-output/`, `docs/`, `openspec/`, `prompts/`). Nothing can regress, but do not touch `_bmad/**` (managed by the BMad installer) or `openspec/**` (wrapped, never modified — NFR1).

### Testing the script

- Framework: pytest via `uv run pytest` (project-context §5); tests mirror `tools/` → `tests/adapters/test_docs_only.py`.
- The seed fixes hyphenated dirs (`docs-only`), which can't be imported as packages. In tests, load the script with `importlib.util.spec_from_file_location("docs_only_main", path)` — a tiny local helper or fixture in the test file is enough (don't create a conftest abstraction for one consumer).
- Prefer invoking `main(argv)`-style entry (give the script a `main(argv: list[str] | None = None) -> int` like memlog's) so tests call it in-process with `tmp_path` — no subprocess, no real git repo, fast and deterministic.
- One behavior per test, Arrange/Act/Assert order, sentence-style names (`test_missing_sprint_exits_2_and_writes_nothing`) — project-context §6.
- The conversational re-prompt (AC 3, skill layer) isn't unit-testable; the script-level refusal is the automated proof for AC 3. State this mapping in the PR.

### Code style anchors

- Model file: [_bmad/scripts/memlog.py](../../_bmad/scripts/memlog.py) — small single-purpose functions named for what they return (`now()`, `resolve()`, `render()`), one-line docstrings only where they carry non-obvious WHY, comment-free bodies otherwise.
- Copy the memlog patterns (PEP 723 header, `write_atomic`, `ack`, `main(argv)`); do **not** import `_bmad/scripts/*` — that directory is installer-managed tooling, not part of the shipped product.

### Latest tech notes (no external research required)

- The stack is deliberately stdlib-only Python 3.8+ via `uv run`; uv supports PEP 723 inline metadata natively — the `# /// script` header is all a runner needs.
- `uv run pytest` resolves pytest from the `dev` dependency group once `pyproject.toml` declares it (`uv run --group dev pytest` if needed explicitly).
- `os.replace` is atomic on both POSIX and Windows (dev machines here are Windows) when source and target are on the same filesystem — which the temp-file-next-to-target pattern guarantees.

### Process requirements (Definition of Done, project-context §12)

- Branch: `story/1.1-docs-only-kickoff` off `develop`-flow conventions (§8); PR title: `Story 1.1: Create the Story Manifest via Docs-Only Kickoff`.
- PR description links FR4 (CAP-4), AD-4, AD-5, NFR4-trivially (no credentials exist in docs-only), and notes the §1 tooling-bootstrap deviation (Task 5).
- Every AC above maps to at least one test (§6 traceability). LLM code review (§9) + human review (§7) before squash-merge to `develop` (§10). Annotate `epics.md` Story 1.1 as complete (date + PR link) in the same PR.

### Project Structure Notes

- Paths follow the spine's Structural Seed exactly (`tools/adapters/docs-only/`, `.claude/skills/story-kickoff/`) — the seed's `main.py` convention matches `opsx-wrapper/main.py` and `snapshot-assembler/main.py`.
- Variance to flag: project-context §1/§11 name Story 2.1 as the tooling-bootstrap story, assuming Epic-2-first sequencing; sprint order makes 1.1 the first code story, so the bootstrap lands here (Task 5). CI (GitHub Actions running ruff+pytest, §11) stays deferred until Epic 2 per the standards' letter — do not add CI in this story.

### References

- [epics.md § Story 1.1](../planning-artifacts/epics.md) — story statement + ACs (lines 96–108); Epic 1 context (lines 74–78, 92–94)
- [SPEC.md § CAP-4](../specs/spec-pm-metrics-ai-engineering-flow/SPEC.md) — kickoff adapts to the project's PM tool; success = `source_of_truth` declared once
- [ARCHITECTURE-SPINE.md § AD-4, AD-5](../planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md) — adapter contract, manifest-as-identity; § Structural Seed (lines 140–167); § Deployment (`.story.yaml` is committed, line 173)
- [review-adversarial.md Findings 4, 6](../planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/reviews/review-adversarial.md) — pre-manifest buffering ownership; points-field separation (AD-6a)
- [project-context.md](../../project-context.md) — §1 stdlib-only/ruff, §2 atomic writes/no-premature-abstraction, §3 ack pattern/exit codes, §5–6 testing, §8–§12 branch/PR/DoD
- [_bmad/scripts/memlog.py](../../_bmad/scripts/memlog.py) — reference implementation: PEP 723 header, `write_atomic()`, `ack()`, `main(argv)` structure

## Dev Agent Record

### Agent Model Used

claude-fable-5 (create-story context engineering + dev-story implementation)

### Debug Log References

- RED: `uv run pytest` → collection error, `tools/adapters/docs-only/main.py` absent (test validity confirmed)
- GREEN: 18/18 tests pass in 0.26s after implementation
- E2E: `uv run tools/adapters/docs-only/main.py --repo-root <scratch> ...` → JSON ack + exit 0; second run on same root → AD-5 refusal + exit 2
- Lint: `uv run ruff check .` and `uv run ruff format --check tools tests` both clean (after excluding installer-managed `_bmad`/`.claude` from ruff scope and applying `ruff format` to the two new Python files)

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created
- Implemented `tools/adapters/docs-only/main.py` per the story contract: argparse CLI (`--repo-root/--points/--goal/--sprint/--description`), `story-{YYYYMMDD}-{6hex}` ID, hand-rolled flat YAML (stdlib only — `json.dumps` scalars), atomic write (temp→flush→fsync→`os.replace`), refuse-to-overwrite (exit 2), one-line JSON ack on success. `main(argv)` entry mirrors `_bmad/scripts/memlog.py`; nothing imported from `_bmad/`.
- Created `.claude/skills/story-kickoff/SKILL.md`: elicits points/goal/sprint with the AC-3 re-prompt rule, invokes the writer via `uv run`, surfaces script stderr verbatim on failure, refuses double kickoff early. Docs-only scope only — config selection deferred to Story 1.2 as fenced.
- Bootstrapped dev tooling in `pyproject.toml` (§1/§5 deviation noted in story: this is the first implementation story, not 2.1): `pytest==8.3.5` + `ruff==0.9.6` pinned in the dev dependency group, `[tool.ruff]` config (line-length 100, target py38), `[tool.uv] package = false`. Added `.venv/` to `.gitignore`; `uv.lock` generated for reproducible dev env.
- AC→test traceability: AC 1 → success-path tests (manifest keys/values/ack/story_id format); AC 2 → fixed repo-root location + key order, distinct-ID, refuse-overwrite tests; AC 3 → six invalid/missing-input tests proving exit 2 with nothing written (script layer; the conversational re-prompt lives in SKILL.md and is not unit-testable, as mapped in Dev Notes).
- Branch: `story/1.1-docs-only-kickoff` cut from `develop` after fast-forwarding `develop` to `main` (it was 4 planning commits behind; ff was purely additive).

### Change Log

- 2026-07-09: Story 1.1 implemented — docs-only kickoff adapter, story-kickoff skill, dev tooling bootstrap, 18 tests. All ACs verified; ruff + pytest clean. Status → review.
- 2026-07-09: Addressed external LLM (Gemini) review findings — 2 fixed (single-`now` timestamp consistency + f-strings/type hint), 2 declined with logged rationale (dir rename vs. spine seed; PyYAML vs. stdlib-only rule). 19 tests passing.

### File List

- tools/adapters/docs-only/main.py (new)
- .claude/skills/story-kickoff/SKILL.md (new)
- tests/adapters/test_docs_only.py (new)
- pyproject.toml (new)
- uv.lock (new, generated by uv from the pinned dev group)
- .gitignore (modified — added `.venv/`)
- _bmad-output/implementation-artifacts/1-1-create-the-story-manifest-via-docs-only-kickoff.md (modified — this story file: frontmatter, checkboxes, record, status)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — story status transitions)
