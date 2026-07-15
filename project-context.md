---
project: explore-jira-ai-metrics
purpose: AI-accelerated engineering metrics capture pipeline (see SPEC.md / ARCHITECTURE-SPINE.md for the what/how)
updated: 2026-07-09
---

# Project Context — Engineering Standards

**How AI assistants should use this file:** load this before any task, bug, story, or change request in this repo. It governs *how we work* (language/framework rules, code quality, testing, review, deployment, process, done-criteria). It deliberately does not duplicate *what we're building* — that lives in:

- `_bmad-output/specs/spec-pm-metrics-ai-engineering-flow/SPEC.md` — capabilities, constraints, non-goals
- `_bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md` — invariants (AD-1 through AD-10), tech stack, structural seed
- `_bmad-output/planning-artifacts/epics.md` — epics, stories, acceptance criteria

If a rule below conflicts with something in those documents, the documents win for *what*; this file wins for *how*.

## 1. Language & Framework Standards

- **Language/runtime:** Python 3.8+, run via `uv run` (single-file scripts, no venv management, no separate install step). No other language in this repo's implementation.
- **Lint + format tool: [ruff](https://docs.astral.sh/ruff/).** One tool for both, zero-config-friendly, fast, and fits this repo's minimalist/stdlib-only ethos better than a black+flake8+isort combo. No config exists yet — add a `ruff.toml` (or `[tool.ruff]` in a future `pyproject.toml`) in the first implementation story that needs it (Story 2.1), rather than upfront.
- **Style baseline:** PEP 8, enforced by ruff rather than manually reviewed for.
- **Type checking:** type hints are mandatory (see §2); a dedicated `mypy` CI gate is a nice-to-have, not required for this project's size — revisit if the codebase grows past the current 3-epic scope.
- **Compatibility:** every module starts with `from __future__ import annotations` so type-hint syntax stays lazy and 3.8-compatible, matching `_bmad/scripts/*.py`.
- **Dependencies:** stdlib-only by default. This repo's existing scripts (`argparse`, `json`, `os`, `sys`, `datetime`, `pathlib`) prove the pattern works for this class of tool. Adding a third-party package requires explicit discussion first, and an exact pinned version if approved — no floating version ranges.

## 2. Code Standards

- **PEP 723 inline script metadata** at the top of every standalone script (`# /// script` / `requires-python = ">=3.8"` / `# ///`), matching `_bmad/scripts/*.py`.
- **Type hints on every function signature** — no untyped public function.
- **Docstrings only where they carry non-obvious WHY** (matches this repo's broader convention: no comments unless removing them would confuse a future reader). A module docstring may run longer if it explains real invariants (see `memlog.py`'s header as the model); function docstrings stay one line unless truly warranted.
- **Small, single-purpose functions** — `memlog.py`'s `now()`, `resolve()`, `split()`, `render()` are the model: each does one thing, named for what it returns.
- **Atomic writes, always**, for anything touching `.story.yaml`, `.story-events.jsonl`, or a snapshot: temp file → flush → `os.fsync` → `os.replace`. Never an in-place write — this is what AD-1/AD-2's "no corruption, ever" guarantee actually depends on. Reference implementation: `_bmad/scripts/memlog.py`'s `write_atomic()`.
- **No premature abstraction.** Three similar lines beat a speculative helper. Don't design for hypothetical future adapters/tools beyond what AD-4/AD-10 already specify.

## 3. API Standards (Internal Interfaces)

This project has no REST/HTTP API today — the central presentation layer is explicitly deferred (see `ARCHITECTURE-SPINE.md` § Deferred). "API" here means the internal contracts between modules: hooks, the CLI wrapper, the snapshot assembler, and adapters.

- **One JSON object per line** (JSONL) is the only IPC mechanism — every producer appends to `.story-events.jsonl`, nothing else.
- **Event shape is fixed:** `{story_id, source, type, timestamp, payload}`. `type` is always namespaced (`git.*`, `ai.<tool>.*`, `opsx.*` per AD-1a) — never a bare event name.
- **Adapters return a fixed normalized shape.** Source-of-truth adapters (AD-4) return `{points, goal, sprint, description}`; AI-tool adapters (AD-10) emit the normalized AI-activity shape. A new adapter implementation must match the shape exactly — no adapter-specific fields leak into `.story.yaml` or the event log.
- **CLI scripts follow the `_bmad/scripts/*.py` pattern:** explicit `--workspace`/`--path`-style addressing (no ambient global state, no implicit cwd assumptions), and exactly one JSON object printed to stdout on success (the "ack" pattern) — so a caller never has to re-read a file to know what happened.
- **Exit codes are load-bearing, not decorative.** 0 = success; non-zero = failure, and a hook's non-zero exit is what triggers AD-9's retry-then-surface behavior. Never swallow an exception and exit 0.
- **Never trust external input.** JIRA/Confluence API responses are untrusted — validate shape before writing anything into `.story.yaml`.

## 4. Security Standards

- Adapter credentials (JIRA/Confluence tokens) are read from environment variables or the OS credential store **at call time only** — never written into `.story.yaml`, the event log, or any snapshot (AD-4, NFR4). This is a hard rule, not a best-effort one.
- **No secrets, tokens, or API keys committed, ever.** Scan before every commit — this repo's initial commit was scanned for exactly this before it went to GitHub; keep doing that for every PR.
- **`subprocess` calls use argument lists, never `shell=True` with string interpolation** — the CLI wrapper invoking `git`/`opsx` is exactly the kind of call where shell injection would otherwise be possible.
- Dependency additions require explicit justification (see §1) — pin exact versions if ever approved.

## 5. Testing Framework

- **Framework: [pytest](https://docs.pytest.org/).** Add as a dev-only dependency (`--group dev` or a `requirements-dev.txt`) in the first story that needs it — not installed yet.
- **Directory layout mirrors `tools/`:** `tests/hooks/test_git_post_commit.py`, `tests/adapters/test_jira.py`, `tests/snapshot_assembler/test_reduce.py`, etc. — a reader should find a module's test file by guessing the mirrored path.
- **Fixtures over setup/teardown boilerplate:** use pytest fixtures (e.g. a `tmp_path`-based fake `.story-events.jsonl`) rather than manual file creation/cleanup in every test.
- **Mocking:** `unittest.mock` (stdlib) for JIRA/Confluence API calls and subprocess invocations — never hit a real external API or a real git repo in a unit test.
- **Run command:** `uv run pytest` (once pytest is added as a dependency) — no separate test-runner config needed beyond that.

## 6. Unit Testing Standards

- **One behavior per test.** A test name should read as a sentence describing the behavior (`test_retry_exhausted_surfaces_visible_error`, not `test_hook_1`).
- **Given/When/Then maps directly to Arrange/Act/Assert** — write the test in that order, and comment-free, since the AC in `epics.md` already states the "why."
- **Every acceptance criterion in `epics.md` maps to at least one test.** Traceability matters as much in testing as it did in planning — if you can't point to which AC a test proves, the test (or the AC) is missing something.
- **Boundary-test numeric thresholds**, not just the happy path: AD-7's 15-minute idle timeout at 14/15/16 minutes; AD-9's 3 retries at 2/3/4 attempts.
- **Don't test the standard library or third-party code** — test this project's logic only. Don't write a test that just re-asserts `os.replace` works.
- **Coverage bar:** every public function in `tools/` has at least one test; 100% line coverage is not a goal in itself, but an untested public function is a gap, not an exception.

## 7. Code Review (Human)

Separate from, and in addition to, the mandatory LLM pass (§9):

- Every PR gets one human reviewer before merge, even after the LLM review passes — the LLM review is a gate, not a replacement (see §9).
- Reviewer checks: does the code match the story's AC exactly, not just "something reasonable"? Does it follow §1–§4 above? Does a new adapter/hook actually match the fixed shapes in §3, or does it quietly drift?
- Review turnaround: same-day for a single-story PR, given this project's story sizing (single dev agent, single story) — nothing here should sit in review for days.
- Disagreements get resolved in the PR thread, not silently overridden either direction.

## 8. Feature Branch & PR

- **Branch naming:** `story/{epic}.{story}-{short-slug}` — e.g. `story/2.1-hook-installation`. This mirrors AD-7's branch-per-story convention, the very thing this tool enforces on *its own future users* — we dogfood it on ourselves.
- **One branch per story**, never per epic — keeps PRs reviewable, matches the single-dev-agent story sizing already validated in the implementation readiness check.
- **PR title:** `Story {N.M}: {story title}`, matching `epics.md`'s heading exactly, for traceability.
- **PR description** must link the FR/AD IDs the story covers (copy straight from the story's AC).
- **Target branch is `main`** (revised 2026-07-15, see §10) — a story branch opens its PR directly against `main`, not an intermediate integration branch.

## 9. LLM PR Review (Mandatory Before Merge)

- Every PR runs `bmad-code-review` (or `/code-review`) before merge — no exceptions.
- **Findings are triaged:** Critical/High must be fixed before merge. Medium/Low may be deferred to a follow-up story, but must be explicitly logged (PR description or a new `epics.md` note) — never dropped silently. This mirrors AD-9's own philosophy: nothing fails silently.
- **Declined (won't-fix) findings are also logged as GitHub Issues**, labeled `wontfix` and closed as "not planned", titled `Review-declined: {short description}`, with the rationale and a link to the PR triage. This keeps declined findings searchable in one place (Issues) rather than buried in PR threads. (Adopted 2026-07-09, applied retroactively to PR #1.)
- The LLM review is a mandatory gate, **not a replacement** for human sign-off (§7) — a human reviewer still approves the PR.
- **Every finding is verified against the actual diff before being trusted** (`git diff <base>..<branch> --name-only`, or the file's own last-touching commit) — a review finding not present in this PR's own changes is stale/misattributed and must be flagged as such, never silently fixed or silently dropped.
- **Story 5.4 — logging a real, verified-real review finding as a defect:** once a finding is confirmed real (against the diff) and fixed, log it as part of that same step — this is a side-effect of the fix, not a separate task for the developer to remember:
  1. If this story's `.story.yaml` has `source_of_truth: jira` and a non-null `jira_issue_key`, create a real Jira subtask first via the connected Atlassian MCP server's `createJiraIssue` tool (parent = `jira_issue_key`, summary/description from the finding).
  2. Then run `uv run tools/log-defect/main.py --repo-root . --type review --summary "<finding summary>" --description "<finding description>" [--jira-subtask-key <key from step 1>]` — this appends the local `ai.claude-code.defect_review` event the snapshot assembler reduces into `defect_metrics` at story close. This script never calls Jira itself (MCP tools are only reachable from a live assistant turn, never a subprocess) — step 1 must happen first, in the same turn, if applicable.
  A declined/stale finding is never logged this way — only a finding that was both confirmed real and actually fixed.

## 10. PR Merge to `main` (revised 2026-07-15)

- **`main` is the trunk** — every story branch merges straight to `main` via a reviewed PR. There is no `develop`/integration branch; the earlier two-tier plan (§11 as originally written, Story 4.2 in `epics.md`) is superseded by this simpler flow now that the tooling is far enough along to self-host on `main` directly.
- **Squash-merge to `main`** — one commit per story keeps history readable.
- Merge commit message references the story ID and epic.
- Delete the feature branch after merge.
- Flow: `story/{epic}.{story}-{slug}` → PR against `main` → human + LLM review (§7, §9) → squash-merge → optionally tag a release (`v0.M.0`) once a meaningful slice is done → the one-click dashboard workflow (Story 5.9) can be run from `main` any time after.

## 11. Deployment

Two different things share the word "deployment" here — keep them separate:

- **This repo's own release process:** `main` accumulates squash-merged stories directly (§10). A release is tagged with semantic versioning (`v0.1.0`, etc.) once an epic (or a meaningful slice of one) is complete and tested. A `CHANGELOG.md` entry accompanies each tag, referencing the epics/stories included.
- **Deploying the *built tool* into other projects** is a separate concern, already decided in `APPROACH.md` § Delivery Path: Step 1 (repo starter kit copied into a target project, `tools/setup-hooks` run once) → Step 2 (scaffolding CLI) → Step 3 (VS Code extension), built and adopted in that order. This repo produces the artifacts; it doesn't run them.
- No CI/CD pipeline exists yet for this repo. Add one (GitHub Actions running `ruff` + `pytest` on every PR) at the point Epic 2 implementation starts — not before, to avoid building automation before there's anything to automate against.

## 12. Story Definition of Done (Mandatory)

A story is not done until **all** of:

- [ ] Every acceptance criterion in `epics.md` passes, verified by an automated test (§5, §6)
- [ ] Code follows §1 (Language/Framework), §2 (Code Standards), and §3 (API Standards)
- [ ] No secrets or credentials committed (§4)
- [ ] Human code review completed (§7) and LLM PR Review completed (§9), with all Critical/High findings resolved
- [ ] The relevant AD/CAP/FR ID(s) are referenced in the commit message and PR description
- [ ] `epics.md`'s story entry is annotated as complete (date + PR link)
- [ ] If the story surfaced a gap in `SPEC.md` or `ARCHITECTURE-SPINE.md`, that document is updated in the same PR — or a follow-up is explicitly logged. Never let code and planning docs silently diverge (this project has kept them in lockstep all through planning; don't break that discipline once implementation starts).

## 13. Story Archival Checklist

Mirrors the "story close" concept this tool itself is designed to capture for its future users:

- [ ] Story merged to `main` (§10)
- [ ] `epics.md` updated to mark the story complete
- [ ] Any deferred LLM-review or human-review findings logged as new tracked items
- [ ] If the story was the epic's last, add a short epic-level retro note (what worked, what to adjust) — informal; a full `bmad-retrospective` is only for a large epic

## 14. Bug Tracking

- Bugs are tracked as **GitHub Issues** on `jayanthchincholi26/ai-project-metrics-bmad`.
- Issue title: `Bug: {short description}`; label `bug`.
- Every bug issue references the story/AD/CAP it relates to, if known.
- A small bug found during a story's implementation is fixed in the same PR. A bug requiring its own story-sized fix gets a new story added to the relevant epic in `epics.md` — never a silent out-of-band patch.

## Note on scope

This standards file governs **story implementation** going forward (Phase 4). It does not retroactively apply to the planning-phase commits already on `main` (brainstorm/spec/architecture/epics docs) — those were direct commits by design, since they're planning artifacts, not stories being implemented.
