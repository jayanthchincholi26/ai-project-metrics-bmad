---
baseline_commit: b6327c7
---

# Story 4.5: Publish as a Package for a True One-Word Install (`uvx ai-metrics-capture install`)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer adopting this capture tooling in my own project,
I want a single short, versionless command — no URL, no branch name, no host to remember,
so that onboarding feels like `npx bmad-method install` or `uvx ruff`, not a fully-qualified `raw.githubusercontent.com` path.

## Acceptance Criteria

1. **Given** this project is published to PyPI as an installable package
   **When** a developer runs `uvx ai-metrics-capture install` (exact command name TBD at implementation time if `ai-metrics-capture` collides on PyPI — confirm availability first)
   **Then** `uv` resolves and runs the package's console-script entry point without the developer needing `git clone`, a URL, or a branch/tag name — `uvx` transparently downloads the latest published version into an ephemeral environment and executes it

2. **Given** the entry point runs
   **When** it executes in the developer's target repo (current working directory)
   **Then** it produces the exact same on-disk result as today's zip-extract path: `tools/`, `.claude/skills/story-kickoff/SKILL.md`, `INSTALL.md`, and `.story-config.yaml.example` land at the repo root — same git-repo precondition check as Story 4.3's scripts, same clear failure message if not a git repo

3. **Given** this doesn't replace either existing distribution path
   **When** this story is done
   **Then** the Story 4.1 manual zip download and the Story 4.3 `curl`/`irm` one-liners **both still work exactly as before** — this is a third, more convenient path, additive only (same precedent Story 4.3 set over 4.1)

4. **Given** publishing to PyPI is a new supply-chain surface this project has never had
   **When** the publish mechanism is built
   **Then** it's automated via a GitHub Actions workflow gated on a tagged release on `main` (consistent with Story 4.2's `develop`→`main` promotion cadence — **this story cannot ship a real publish step until Story 4.2 lands**; until then, implementation and testing use a manual `uv build`/`twine upload` or a test index, never publishing untested code to the real, public PyPI index under whatever real account owns the package name)

5. **Given** `project-context.md` §1 declares this project stdlib-only-by-default with "adding a third-party package requires explicit discussion first"
   **When** this story introduces a build backend (e.g. `hatchling` or `setuptools`) in a new `pyproject.toml`
   **Then** that dependency is a **packaging-time-only** dependency (never imported by any capture-tooling script at runtime) — call this out explicitly in the PR description as the one exception this story needs, not a silent violation of §1

6. **Given** this project's `tools/` directory already has an established per-tool structure (`main.py` + PEP 723 inline metadata, no third-party imports)
   **When** the new CLI wrapper is written
   **Then** it reuses Story 4.1's `tools/build-release/main.py` build logic and Story 4.3's install logic directly (import, don't reimplement) — this story is a new *distribution front door*, not a rewrite of what already works

## Tasks / Subtasks

- [ ] Task 0: pre-flight — confirm the package name is actually available on PyPI (AC 1)
  - [ ] Subtask 0.1: check `https://pypi.org/project/ai-metrics-capture/` (and 1-2 fallback name candidates) before writing any packaging code — a taken name blocks this story entirely until a name is chosen; surface this to the user rather than silently picking an alternate name

- [ ] Task 1: package scaffolding (AC 1, 5, 6)
  - [ ] Subtask 1.1: add `pyproject.toml` at the repo root — `[build-system]` (hatchling recommended: zero-config for a single-package layout, already `uv`'s own default for new projects), `[project]` metadata (name, version — likely synced to the same version string Story 4.1's `--version` flag already bakes into release zips), `[project.scripts]` entry point (e.g. `ai-metrics-capture = "ai_metrics_capture.cli:main"`)
  - [ ] Subtask 1.2: decide and document the package's importable module layout (a new small package, e.g. `src/ai_metrics_capture/cli.py`, that imports and calls Story 4.1's `tools/build-release/main.py` build/extract logic and Story 4.3's install logic as library calls — not a copy-paste duplicate)
  - [ ] Subtask 1.3: confirm packaging-time-only dependency boundary holds — `ruff check`/`ruff format` still pass on `tools/`, no new runtime import appears in any file under `tools/`

- [ ] Task 2: the `install` subcommand (AC 1, 2, 3)
  - [ ] Subtask 2.1: implement `ai-metrics-capture install` reusing the same logic Story 4.3's scripts already prove out (latest-release resolution — or, since this ships as a versioned package itself, consider: does `uvx` running version N of this package just install/extract version N's own bundled tooling directly, skipping the GitHub API call entirely? Resolve this design question explicitly in Dev Notes before implementing — it changes whether this needs network access to GitHub at all)
  - [ ] Subtask 2.2: same git-repo precondition check, same next-step guidance printed at the end, consistent UX with Story 4.3

- [ ] Task 3: publish automation (AC 4)
  - [ ] Subtask 3.1: GitHub Actions workflow, triggered on a tagged release (mirrors Story 4.1's tag-driven release cadence), running `uv build` + `uv publish` (or `twine upload`) against PyPI using a repo secret token
  - [ ] Subtask 3.2: explicitly gate real publishing behind Story 4.2 — until `develop`→`main` promotion is a defined, working cadence, this workflow either targets TestPyPI only or stays unwired (manual trigger, never automatic) — do not let this story accidentally publish an unfinished capture tool to the real public index

- [ ] Task 4: documentation (AC 2, 3)
  - [ ] Subtask 4.1: add a new "Quick install" variant to `INSTALL.md` presenting `uvx ai-metrics-capture install` as the primary path once published; Story 4.3's `curl`/`irm` commands stay documented as the fallback for machines without `uv` (or before this package is actually published) — three tiers now: package install (primary) → curl/irm (fallback 1) → manual zip (fallback 2)

- [ ] Task 5: live E2E (AC 1, 2, 3)
  - [ ] Subtask 5.1: build the package locally (`uv build`), install it into a scratch venv or run directly via `uvx --from <local wheel path> ai-metrics-capture install` against a real empty git repo, confirm the resulting file layout matches a manual zip extract exactly
  - [ ] Subtask 5.2: confirm Story 4.1's zip path and Story 4.3's curl/irm scripts are both untouched and still pass their own existing tests/E2E

## Dev Notes

### Scope — what this story is and is not

- This is a **third distribution front door** onto the exact same underlying artifact-build logic Story 4.1 already owns — no change to what capture tooling *does*, no change to `setup-hooks.py`, no change to any adapter or hook.
- **Do NOT duplicate build logic.** The CLI entry point must call into `tools/build-release/main.py`'s existing functions, not reimplement zip assembly a third time (Story 4.3's scripts already reuse the *artifact*, not the *build code*, since they're shell/PowerShell — this story, being Python, has no excuse not to import directly).
- **Do NOT wire real PyPI publishing before Story 4.2 lands.** Story 4.2 (`develop`→`main` promotion cadence) is the thing that defines *when* a release is official; publishing this package automatically on every tag before that cadence exists risks shipping broken/unfinished work to a public package index that (unlike a GitHub Releases zip) can't easily be un-published or corrected after the fact.

### The design question this story must resolve before writing code

Story 4.3's `curl`/`irm` scripts fetch the **latest GitHub release** dynamically — the script itself is versionless, only the thing it downloads is versioned. A PyPI package inverts this: `uvx ai-metrics-capture install` runs a **specific published version** of this very package, which could itself simply *contain* the capture tooling directly (no second network call to GitHub needed at all — `uvx` already fetched the right version). Decide which model this story implements:
- **Option A (recommended, simpler):** the package's own contents (its wheel) directly bundle `tools/`, `INSTALL.md`, the skill, etc. — `install` just copies from the installed package's own directory into cwd, no GitHub API call, no network dependency beyond what `uvx` itself already did.
- **Option B:** the package is just a thin CLI shim that still calls out to the GitHub releases API at runtime, same as Story 4.3 — more moving parts, no real benefit over Option A given `uvx` already solves the versioning problem.

Recommendation: Option A. Confirm with the user only if a real blocker surfaces (e.g. packaging non-Python files like `SKILL.md` inside a wheel needs `package_data`/`include` config — worth a quick spike before committing to the full task list above).

### Architecture compliance (binding invariants)

- No AD/architecture invariant is touched — pure distribution/packaging, same category as Stories 4.1/4.3/4.4.
- `project-context.md` §1 stdlib-only: the **published capture tooling itself** stays stdlib-only, unchanged. The **build backend** (hatchling/setuptools) is a new, explicit, one-time exception — packaging-time only, never imported by anything under `tools/`. State this plainly in the PR description per AC 5; don't let it read as a silent violation.

### Testing standards (project-context.md §5/§6)

- Packaging/publish-workflow correctness has no meaningful `pytest` surface (similar to Story 4.3's shell scripts) — Definition of Done is a real local build + real `uvx`-style install against a scratch git repo (Task 5), not unit tests of `pyproject.toml` contents.
- Existing `tests/build_release/test_build.py` must stay green untouched — this story adds a new front door, it does not touch Story 4.1's tested build path.

### Source tree touched

```text
pyproject.toml                          NEW    build-system + [project.scripts] entry point
src/ai_metrics_capture/__init__.py      NEW    (or similar layout — confirm during Task 1.2)
src/ai_metrics_capture/cli.py           NEW    thin wrapper calling tools/build-release/main.py's existing logic
.github/workflows/publish.yml           NEW    tag-triggered build+publish, gated behind Story 4.2 (Task 3.2)
tools/build-release/INSTALL.md          UPDATE new top-tier "Quick install (uvx)" section; curl/irm and manual zip stay as documented fallbacks
```

### Project Structure Notes

This is the first time this repo ships an importable Python *package* (as opposed to standalone PEP-723 scripts) — expect some genuine new-ground decisions here (src-layout vs flat, how `.claude/skills/` and `INSTALL.md` get included as package data). Flag any structural surprise found during Task 1 in this story's own Completion Notes for future reference, since nothing in this project has done this before.

### References

- [Source: tools/build-release/main.py] — the exact build logic (`iter_entries()`, `build()`) this story's CLI wrapper must call, not duplicate
- [Source: tools/build-release/install.sh, install.ps1] — Story 4.3's precedent this story extends with a third path (Task 4)
- [Source: _bmad-output/implementation-artifacts/4-3-one-command-curl-irm-installer.md] — Dev Notes explicitly named "a PyPI package / `uvx ai-metrics-capture init` entry point" as the heavier alternative deferred from that story; this story is that deferred work
- [Source: project-context.md §1] — stdlib-only-by-default rule; AC 5 is how this story stays compliant while still needing a build backend
- [Source: _bmad-output/planning-artifacts/epics.md — Story 4.2] — the `develop`→`main` promotion cadence this story's real-publish automation is explicitly gated behind (AC 4, Task 3.2)

## Dev Agent Record

### Agent Model Used

_to be filled by dev-story_

### Debug Log References

_to be filled by dev-story_

### Completion Notes List

_to be filled by dev-story_

### File List

_to be filled by dev-story_
