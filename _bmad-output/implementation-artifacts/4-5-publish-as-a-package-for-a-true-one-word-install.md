---
baseline_commit: b6327c7
---

# Story 4.5: Publish as a Package for a True One-Word Install (`uvx ai-metrics-capture install`)

Status: done

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

- [x] Task 0: pre-flight — confirm the package name is actually available on PyPI (AC 1)
  - [x] Subtask 0.1: attempted to check `https://pypi.org/project/ai-metrics-capture/` — pypi.org returns a bot-detection "Client Challenge" page (HTTP 200, no real content) for automated requests from this environment, so availability could not actually be confirmed programmatically. Proceeding with `ai-metrics-capture` (matches the existing release zip's name) but flagging plainly: **real availability must be confirmed by hand before any actual publish** — moot for this story anyway since AC 4/Task 3.2 gate real publishing behind Story 4.2.

- [x] Task 1: package scaffolding (AC 1, 5, 6)
  - [x] Subtask 1.1: added `pyproject.toml` — **not at the repo root** (see Dev Notes deviation below) but in a new `pypi-package/` subdirectory, to avoid colliding with the existing root `pyproject.toml` (this repo's own dev/test config, `[tool.uv] package = false`). `[build-system]` = hatchling, `[project]` metadata, `[project.scripts]` entry point `ai-metrics-capture = "ai_metrics_capture.cli:main"`
  - [x] Subtask 1.2: `pypi-package/src/ai_metrics_capture/cli.py` — thin `install` subcommand; module layout is src-layout, first package this repo has shipped
  - [x] Subtask 1.3: confirmed — `ruff check .` / `ruff format --check .` at the repo root pass clean including `pypi-package/`; no new runtime import appears anywhere under `tools/`

- [x] Task 2: the `install` subcommand (AC 1, 2, 3)
  - [x] Subtask 2.1: **Option A** (see Dev Notes) — the package bundles the capture tooling directly inside its own wheel; `install` makes no GitHub API call at all, just copies from the installed package's own `_bundled/` directory into cwd
  - [x] Subtask 2.2: same git-repo precondition check (`.git` exists — file or dir, matching Story 4.3's `-e` fix), same "Installed. Next: uv run tools/setup-hooks.py --repo-root ." message, verbatim-matching Story 4.3's UX

- [x] Task 3: publish automation (AC 4)
  - [x] Subtask 3.1: `.github/workflows/publish-pypi.yml` — builds via `uv build`, publishes via `uv publish`
  - [x] Subtask 3.2: gated exactly as required — `workflow_dispatch` only (no tag trigger), targets TestPyPI (`--publish-url https://test.pypi.org/legacy/`) via a `TEST_PYPI_API_TOKEN` secret that does not yet exist in this repo. Cannot publish anything, anywhere, until both Story 4.2 lands and a human deliberately wires a real secret and triggers it by hand.

- [x] Task 4: documentation (AC 2, 3)
  - [x] Subtask 4.1: added a new "Package install (`uvx`) — not yet published" section to `INSTALL.md`, ahead of the existing "Quick install" (curl/irm) section, explicitly marked not-yet-live and explaining why (gated behind Story 4.2) — three tiers now exist in the doc, only two are actually usable today

- [x] Task 5: live E2E (AC 1, 2, 3)
  - [x] Subtask 5.1: `uv build` in `pypi-package/` → real wheel; ran `uvx --from <local wheel path> ai-metrics-capture install` against a real empty scratch git repo; `diff -rq` against a real `tools/build-release/main.py`-built zip extracted into a separate scratch repo came back **empty** — byte-identical file layout. Also verified the git-repo precondition failure path (real non-git scratch dir → `exit 2`, same error message as Story 4.3's scripts).
  - [x] Subtask 5.2: full suite 324 passed, `ruff check`/`ruff format --check` clean at repo root — Story 4.1's zip path and Story 4.3's curl/irm scripts are untouched by this story

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
pypi-package/pyproject.toml                     NEW    build-system + [project.scripts] entry point (own subdirectory - see deviation note)
pypi-package/README.md                          NEW    PyPI project description
pypi-package/sync_bundle.py                      NEW    pre-build step: regenerates _bundled/ from tools/build-release/main.py's iter_entries()
pypi-package/src/ai_metrics_capture/__init__.py  NEW
pypi-package/src/ai_metrics_capture/cli.py       NEW    thin install subcommand, copies from installed package's own _bundled/
.github/workflows/publish-pypi.yml               NEW    workflow_dispatch-only, TestPyPI target, gated behind Story 4.2 (Task 3.2)
tools/build-release/INSTALL.md                   UPDATE new top-tier "Package install (uvx)" section, marked not-yet-published
.gitignore                                       UPDATE ignore pypi-package/src/.../  _bundled/ and pypi-package/dist/
```

### Project Structure Notes

This is the first time this repo ships an importable Python *package* (as opposed to standalone PEP-723 scripts) — expect some genuine new-ground decisions here (src-layout vs flat, how `.claude/skills/` and `INSTALL.md` get included as package data). Flag any structural surprise found during Task 1 in this story's own Completion Notes for future reference, since nothing in this project has done this before.

### Deviations found during implementation (recorded per the note above)

1. **`pyproject.toml` location**: this story's own Source Tree section (below) said `pyproject.toml` NEW at the repo root — but a `pyproject.toml` **already exists** at the repo root, and it's this planning repo's own dev/test config (`[tool.uv] package = false`, pytest/ruff settings every other story's tooling depends on). Renaming its `[project]` name or adding `[build-system]`/`[project.scripts]` to it would change how `uv run pytest`/`uv run ruff` behave repo-wide. Resolved by putting the distributable package in its own `pypi-package/` subdirectory with its own independent `pyproject.toml` — fully isolated, zero risk to the existing dev workflow, `uv build` is simply run from inside that subdirectory.
2. **Build hook reaching outside the package fails from an sdist**: the first implementation used a hatchling custom build hook that reached `../tools/build-release/main.py` at wheel-build time. This works for a direct wheel build but **fails when building the wheel from an sdist** (the normal `uv build`/PyPI path) — hatchling's sdist stage has no access to anything outside `pypi-package/`, so the hook's import of a file at `../tools/...` throws `FileNotFoundError` once running from the unpacked sdist. Fixed by moving the bundling logic to `pypi-package/sync_bundle.py`, an explicit **pre-build** step (not a build hook) that must run before `uv build`; the sdist target's `include` list then ships the resulting `_bundled/` directory explicitly (overriding hatchling's default VCS-tracked-files heuristic, since `_bundled/` is deliberately `.gitignore`'d as a generated artifact).

### References

- [Source: tools/build-release/main.py] — the exact build logic (`iter_entries()`, `build()`) this story's CLI wrapper must call, not duplicate
- [Source: tools/build-release/install.sh, install.ps1] — Story 4.3's precedent this story extends with a third path (Task 4)
- [Source: _bmad-output/implementation-artifacts/4-3-one-command-curl-irm-installer.md] — Dev Notes explicitly named "a PyPI package / `uvx ai-metrics-capture init` entry point" as the heavier alternative deferred from that story; this story is that deferred work
- [Source: project-context.md §1] — stdlib-only-by-default rule; AC 5 is how this story stays compliant while still needing a build backend
- [Source: _bmad-output/planning-artifacts/epics.md — Story 4.2] — the `develop`→`main` promotion cadence this story's real-publish automation is explicitly gated behind (AC 4, Task 3.2)

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5

### Debug Log References

Full suite: 324 passed. `ruff check .` / `ruff format --check .` clean at repo root (includes `pypi-package/`). Real `uv build` produced a working wheel + sdist. Real `uvx --from <wheel> ai-metrics-capture install` against a scratch git repo produced a file layout `diff -rq`-identical to a real `tools/build-release/main.py`-built zip extracted into a separate scratch repo. Confirmed the non-git-repo failure path exits 2 with the same message Story 4.3 uses.

### Completion Notes List

- Two genuine new-ground deviations from the story's original plan — both recorded in Dev Notes above: (1) the package's `pyproject.toml` had to live in its own `pypi-package/` subdirectory rather than the repo root, since a root `pyproject.toml` already exists for this repo's own dev/test tooling; (2) the bundling of capture-tooling files into the package had to be an explicit pre-build script (`sync_bundle.py`), not a hatchling build hook, because a build hook reaching outside the package directory breaks once hatchling builds the wheel from an sdist (no access to `../tools/`).
- Chose Option A from Dev Notes (package bundles tooling directly, no GitHub API call at install time) — confirmed correct via the E2E diff coming back empty.
- PyPI name availability (Task 0) could not be confirmed programmatically — pypi.org blocks automated requests with a bot-detection challenge page. Not a blocker for this story since real publishing doesn't happen here anyway (gated behind Story 4.2), but must be confirmed by hand before Story 4.2 unblocks a real publish.
- No LICENSE file exists in this repo — `pyproject.toml`'s `license` field is intentionally omitted rather than asserting an unchosen license; this needs resolving before any real publish too.
- `.github/workflows/publish-pypi.yml` references a `TEST_PYPI_API_TOKEN` secret that does not exist in this repo yet — the workflow is `workflow_dispatch`-only and cannot run automatically, so this is safe to leave unset until someone deliberately wires it up.

### File List

pypi-package/pyproject.toml (new)
pypi-package/README.md (new)
pypi-package/sync_bundle.py (new)
pypi-package/src/ai_metrics_capture/__init__.py (new)
pypi-package/src/ai_metrics_capture/cli.py (new)
.github/workflows/publish-pypi.yml (new)
tools/build-release/INSTALL.md (updated)
.gitignore (updated)
