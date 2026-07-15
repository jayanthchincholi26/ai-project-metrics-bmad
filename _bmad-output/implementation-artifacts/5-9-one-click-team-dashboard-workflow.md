---
baseline_commit: 65e22d5
---

# Story 5.9: One-Click Team Dashboard via GitHub Actions

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an engineering manager,
I want to generate the consolidated leadership dashboard with one click, no local install needed,
so that I can see a sprint-wide rollup across every developer's merged story branches without depending on someone running a local command.

## Background

Follows directly from a live demonstration (2026-07-15): the user asked to see a real consolidated report across all pilot-test snapshots to date. Built by manually collecting the 7 real snapshots scattered across 5 different local test folders into one `snapshots/` directory and running the existing, unmodified `metrics-report`/`dashboard` tools against them — proving the aggregation mechanism already works with zero new code, since `snapshots/*.json` is already meant to be committed to git.

This story automates that same mechanism via GitHub Actions, discussed and scoped live with the user across a few design questions:
- **Trigger choice**: of the three options discussed (manual local command, CI-triggered on every merge, one-click `workflow_dispatch`), the user chose **one-click only** for now — CI-on-every-merge deferred to a later story once the team's actual merge cadence is understood.
- **Publishing boundary**: Story 5.5 deliberately gave the dashboard no publishing mechanism of its own ("you decide whether and how to share it," since it can summarize cost figures). Automating generation must not silently cross that boundary — the workflow uploads a downloadable artifact (access follows the repo's own Actions read permissions), not a committed file or a public page.
- **Access control**: the user asked whether the button itself could be restricted to specific people/roles. GitHub's own baseline (Write access required to trigger any `workflow_dispatch`) already limits it to collaborators. Finer-grained restriction to a *specific* approver list uses a GitHub Environment with required reviewers — a free, native mechanism (true custom RBAC roles would require GitHub Enterprise Cloud, out of reach on this plan).

## Acceptance Criteria

1. **Given** a target repo has installed this tooling
   **When** the release artifact is extracted at the repo root
   **Then** it includes `.github/workflows/generate-dashboard.yml`, a `workflow_dispatch`-only workflow — no code push or local install needed to trigger it
2. **Given** the workflow runs
   **When** it executes
   **Then** it checks out the repo, runs the same `metrics-report`/`dashboard` tools already documented for local use, and uploads the result (`metrics-reports/`) as a downloadable GitHub Actions artifact — never committed back to the repo, never published to a public URL
3. **Given** a repo wants to restrict who can actually let a run execute (not just who can click the button)
   **When** they define a GitHub Environment named `dashboard-publish` with required reviewers (a one-time manual Settings step, documented, not automatable by this tooling without an admin token)
   **Then** the workflow's `environment: dashboard-publish` reference gates execution behind that approval, while remaining fully functional (ungated, Write-access-only) if the environment isn't configured
4. **Given** this is a new shipped artifact
   **When** `tools/build-release/main.py` builds the release zip
   **Then** the workflow file is included and the build fails loudly (per existing precedent) if the source file goes missing

## Tasks / Subtasks

- [x] Task 1: author the workflow template (AC 1, 2, 3)
  - [x] Subtask 1.1: `tools/build-release/dashboard-workflow.yml` — `workflow_dispatch` trigger, `environment: dashboard-publish`, checkout + setup-uv + run report/dashboard + `upload-artifact`
- [x] Task 2: wire it into the shipped artifact (AC 1, 4)
  - [x] Subtask 2.1: `iter_entries()` yields it at arcname `.github/workflows/generate-dashboard.yml` (lands ready-to-use at install, no manual copy step)
  - [x] Subtask 2.2: added to `build()`'s required-inputs check alongside `INSTALL.md`/`.story-config.yaml.example`
- [x] Task 3: tests (AC 4)
  - [x] Subtask 3.1: `test_artifact_contains_the_deployable_surface` asserts the new arcname is present
- [x] Task 4: document (AC 3)
  - [x] Subtask 4.1: new `INSTALL.md` section — how to run it, and the one-time GitHub Environment + required-reviewers setup for approval-gating
- [x] Task 5: verify
  - [x] Subtask 5.1: full suite green, `ruff check`/`ruff format --check` clean
  - [x] Subtask 5.2: real release build, confirmed the workflow YAML lands at the correct path with correct content
  - [x] Subtask 5.3: ran the exact commands the workflow's own step runs (`metrics-report` then `dashboard`) against a real multi-story `snapshots/` directory (the same 7 real pilot snapshots used for the earlier live demo), confirming they produce exactly what `upload-artifact` would package
  - [ ] Subtask 5.4: **live verification pending** — this workflow has not yet actually been triggered inside a real GitHub Actions run (would require merging this PR first, then a real `workflow_dispatch` click); local command verification (5.3) proves the underlying logic, not the CI wiring itself

## Dev Notes

### Scope

New shipped artifact (a workflow template) plus two small `main.py` wiring changes. No changes to `metrics-report`/`dashboard` themselves — this story is pure distribution/automation, reusing existing tools unchanged, same category as Stories 4.1/4.3/4.5's own "new front door, not a rewrite" precedent.

### Why an artifact upload, not a commit-back or a published page

Committing the generated dashboard into the repo, or publishing it somewhere public, would be a bigger, harder-to-undo sharing decision than this story should make on the team's behalf — Story 5.5 drew this line deliberately. An uploaded workflow artifact keeps access scoped to whoever already has read access to the repo's Actions runs (the same audience who could already run this locally), and is naturally time-limited (`retention-days: 30`) rather than a permanent addition to repo history.

### Why the environment name can't be auto-created

Creating a GitHub Environment with protection rules requires the GitHub API's environments endpoint, which needs repo-admin-scoped credentials this tooling never holds (same reasoning as why `publish-pypi.yml`'s `TEST_PYPI_API_TOKEN` secret is documented as a manual setup step, not something `setup-hooks.py` provisions). Documented as a one-time manual Settings step instead.

### Source tree touched

```text
tools/build-release/dashboard-workflow.yml      NEW    the workflow template (source of truth)
tools/build-release/main.py                     UPDATE iter_entries()/build() wire it in
tests/build_release/test_build.py               UPDATE asserts the new shipped arcname
tools/build-release/INSTALL.md                  UPDATE new "Team dashboard" section
```

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5

### Debug Log References

Full suite: 337 passed. `ruff check`/`ruff format --check` clean. Real release build confirmed the workflow lands at `.github/workflows/generate-dashboard.yml` with correct content. The workflow's own `metrics-report`/`dashboard` commands were run directly against a real 7-snapshot directory (the same real pilot data used for the live demo earlier this session), confirming correct output.

### Completion Notes List

- Not fully closed — Subtask 5.4 (an actual GitHub Actions `workflow_dispatch` run) is the real proof of the CI wiring itself, since local command verification can't exercise the YAML/environment-gating machinery.
- CI-on-every-merge (the "B" option discussed alongside this "C" one-click option) was deliberately deferred, per the user's own call, to a later story once real team merge cadence is understood.

### File List

tools/build-release/dashboard-workflow.yml (new)
tools/build-release/main.py (updated)
tests/build_release/test_build.py (updated)
tools/build-release/INSTALL.md (updated)
