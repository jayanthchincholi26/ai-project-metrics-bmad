---
baseline_commit: 29cf16bac2ca06c55441199f7849c452c7572b61
---

# Story 4.1: Release Artifact Packages the Capture Tooling for Target Repos

Status: done

> **Backfilled record (2026-07-11).** Designed and implemented directly in a working session
> without the create-story/dev-story workflow; this file was written to keep the
> implementation-artifacts trail complete. Decision history (mechanism choice, rejected
> alternatives) lives in `epics.md` (Epic 4 / Story 4.1).
>
> ✅ **Complete** — 2026-07-11 · [PR #20](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/20) (squash-merged to `enhancements`, 7b621ff). Gemini review: first fully clean, correctly-attributed pass in 5 PRs — zero defects, one harmless mischaracterization (called packaging exclusions "ignoring" `tests/`/`_bmad`/`prompts` when they're simply never walked).

## Story

As a developer on a target project,
I want a documented, repeatable way to bring only the capture tooling into my project,
So that adopting metrics capture doesn't require cloning this planning repo's specs, prompts, and BMad artifacts.

## Acceptance Criteria

1. **Given** a target project that wants to adopt the capture pipeline
   **When** a developer follows the documented install path
   **Then** only the deployable surface lands in their repo — `tools/`, the story-kickoff skill, `INSTALL.md`; never `_bmad-output/`, `prompts/`, `openspec/`, specs, or tests
   **And** `tools/setup-hooks.py` works unmodified against the extracted copy
   **And** install is extract-at-root + one command, not a manual file-by-file copy
   **And** updating later has a defined path (download newer tag, re-extract, re-run setup-hooks — idempotent)
   **And** every prerequisite is stated up front in the shipped `INSTALL.md`

## What Was Done

- `tools/build-release/main.py` — stdlib-only packager producing
  `dist/ai-metrics-capture-<version>.zip`: `tools/` (excluding the packager itself and
  bytecode), `.claude/skills/story-kickoff/SKILL.md`, `INSTALL.md` at archive root. Sorted
  entries for reproducibility; missing inputs fail visibly (exit 2).
- `tools/build-release/INSTALL.md` — ships in the zip; prerequisites table (git, Python 3.8+,
  uv, Claude Code, JIRA-via-MCP OAuth), install steps, `.story-config.yaml` declaration,
  capture-state gitignore lines, update path, and a troubleshooting section built from the
  real smoke-test failures (wrong-cwd, `--repo-root` required, workspace-root,
  hooks-before-session).
- `.github/workflows/release.yml` — on `v*` tag: tests → build with the tag as version →
  `gh release create` with the zip attached. The Releases page doubles as the public
  download URL.
- `dist/` gitignored; 6 new tests in `tests/build_release/test_build.py`.

## Dev Notes

- **Mechanism decision (2026-07-10/11)**: release artifact, over git subtree/submodule
  (imposes this repo's history/friction on target teams) and a template repo (permanent
  two-repo sync burden; useless for existing projects). Fits the codebase because everything
  under `tools/` is stdlib-only single-file scripts — no build step exists to complicate
  packaging.
- **Live E2E verification (beyond unit tests)**: built the artifact, extracted into a virgin
  git repo, ran `uv run tools/setup-hooks.py --repo-root .` → 4 git hooks + 6 Claude events
  wired; a real commit immediately captured `git.commit_msg`/`git.commit` into
  `.story-events.pending.jsonl` with `story_id: null` — AD-1b working in the distributed
  package with zero planning-repo files present.
- **Two smoke-test bugs become structurally impossible for target teams**: the Windows
  long-path clone failure (deep `_bmad-output/` paths aren't in the artifact) and the
  wrong-workspace-root confusion (no parent-wrapper layout to open by mistake).
- Origin: the epic exists because the first real deployment attempt (2026-07-10) cloned the
  whole planning repo and hit four onboarding failures in the first hour. AD-8 assumed
  `tools/` already lives in the target repo; nobody had designed how it gets there.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 4 / Story 4.1] — mechanism decision, prerequisites table
- [Source: docs/testing/pre-deploy-smoke-checklist.md] — the findings the INSTALL.md encodes
- [Source: tools/setup-hooks.py] — the installer the artifact reuses unmodified (AD-8)
- [PR #20](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/pull/20) — in review
