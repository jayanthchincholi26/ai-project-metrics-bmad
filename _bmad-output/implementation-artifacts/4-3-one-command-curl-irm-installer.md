---
baseline_commit: 937e0a1
---

# Story 4.3: One-Command Curl/irm Installer (No Manual Zip Download)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer adopting this capture tooling in my own project,
I want a single copy-pasteable command that installs the tooling into my repo,
so that I don't have to manually find the GitHub Releases page, download a zip, and extract it myself — the same one-command experience `uv`, BMad, and openspec already give me.

## Acceptance Criteria

1. **Given** a developer is standing in their target repo root (a real git repo, this tool's actual install precondition today)
   **When** they run one documented command
   **Then** the same effect as today's "download the zip, extract at repo root" step happens automatically — `tools/`, `.claude/skills/story-kickoff/SKILL.md`, and `INSTALL.md` land at the repo root, fetched from this project's **latest GitHub release**, no manual download/extract step required

2. **Given** this needs to work **before** the target repo has any of this tool's files yet
   **When** the install command is documented
   **Then** it's a `curl -fsSL <raw-script-url> | sh` command for macOS/Linux and an `irm <raw-script-url> | iex` command for Windows PowerShell — fetched directly from this repo's own `main` branch via a stable `raw.githubusercontent.com` URL (the exact pattern `uv`'s own installer uses, already referenced in this project's own `INSTALL.md` Prerequisites table)

3. **Given** the two installer scripts (`tools/build-release/install.sh`, `tools/build-release/install.ps1`)
   **When** either runs
   **Then** it: (a) confirms the current directory is a git repo (`.git` exists) before doing anything, failing with a clear message if not; (b) queries the GitHub API for the **latest release** (`https://api.github.com/repos/jayanthchincholi26/ai-project-metrics-bmad/releases/latest`) to resolve the current zip asset URL — never a hardcoded version; (c) downloads and extracts that zip into the current directory; (d) cleans up the temporary download; (e) prints the exact next step (`uv run tools/setup-hooks.py --repo-root .`), matching `INSTALL.md`'s own Install step 2

4. **Given** these scripts are **not** Python and this project's automated test suite is Python/`pytest`-only
   **When** Definition of Done is evaluated
   **Then** there is no automated test for the scripts themselves — Definition of Done is live manual E2E (both scripts actually run against a real, empty git repo, network calls included) — same precedent as Story 2.7's git-hook shims and Story 1.6's MCP flow (skill/script-level behavior this project's stdlib-only Python test suite structurally cannot exercise)

5. **Given** this doesn't replace the existing zip-download path
   **When** this story is done
   **Then** `tools/build-release/main.py`'s zip artifact and the manual "download from Releases, extract" instructions **both still work exactly as before** — this story adds a second, more convenient path, it does not remove or change the first

## Tasks / Subtasks

- [x] Task 1: write `install.sh` (macOS/Linux) (AC: 1, 2, 3)
  - [x] Subtask 1.1: git-repo precondition check, clear failure message if not
  - [x] Subtask 1.2: resolve latest release's zip download URL via the GitHub API (`curl` + basic JSON field extraction — no `jq` dependency assumed, since this must work on a bare-bones machine with only `curl`/`unzip` as prerequisites)
  - [x] Subtask 1.3: download to a temp file, extract into the current directory, clean up the temp file
  - [x] Subtask 1.4: print the next-step guidance (the `setup-hooks.py` command)

- [x] Task 2: write `install.ps1` (Windows PowerShell) (AC: 1, 2, 3)
  - [x] Subtask 2.1: same git-repo precondition check
  - [x] Subtask 2.2: resolve the latest release's zip URL via `Invoke-RestMethod` against the same GitHub API endpoint
  - [x] Subtask 2.3: download via `Invoke-WebRequest`, extract via `Expand-Archive` into the current directory, clean up the temp file
  - [x] Subtask 2.4: print the same next-step guidance

- [x] Task 3: document the new install path, keep the old one intact (AC: 2, 5)
  - [x] Subtask 3.1: add a new "Quick install" section to `tools/build-release/INSTALL.md`, above the existing "Install (per repository, once)" section, presenting the one-line curl/irm command as the primary path and the manual zip-download steps as the explicit fallback ("prefer no network access to GitHub, or want to inspect the zip first? Extract it manually instead:") — not a replacement, an addition
  - [x] Subtask 3.2: the raw script URLs must point at this repo's `main` branch (the branch a released zip's own `INSTALL.md` snapshot won't drift from, unlike pinning to a specific tag) — confirm this is genuinely how `uv`'s own installer resolves its script (a stable branch reference, not a tag), matching the established precedent this project's own `INSTALL.md` already cites

- [x] Task 4: live E2E, both platforms available in this environment (AC: 1-3)
  - [x] Subtask 4.1: **Windows/PowerShell** — run `install.ps1` for real, from a real terminal, against a fresh empty git repo, with real network access to GitHub; confirm the resulting directory structure matches a manually-extracted zip exactly, and that `uv run tools/setup-hooks.py --repo-root .` works immediately afterward
  - [x] Subtask 4.2: **Bash** (this environment's Bash tool runs Git Bash / POSIX sh, which can execute `.sh` scripts directly) — run `install.sh` for real, same verification
  - [x] Subtask 4.3: confirm a clear, non-cryptic failure message when run outside a git repo (both scripts)

## Dev Notes

### Scope — what this story is and is not

- This is purely a **distribution convenience** — a second way to get the exact same artifact Story 4.1 already produces (the GitHub Releases zip). No change to what's *in* the artifact, no change to `tools/build-release/main.py`, no change to `setup-hooks.py` or any capture logic.
- **Do NOT build in this story:** a PyPI package / `uvx ai-metrics-capture init` entry point (a heavier, alternative distribution mechanism considered and explicitly not chosen here — the curl/irm script is the lower-effort path that still gets a one-command experience); any auto-update/version-pinning mechanism beyond "always fetch latest" (if a developer needs a specific older version, the manual zip-download path from a specific release tag already covers that, untouched by this story).
- **Do NOT remove or alter the existing manual zip-download instructions.** AC 5 is explicit: this is additive.

### Why `main` branch for the script URL, not a pinned tag

The install *script* itself (the shell/PowerShell logic) should track `main` so a bug fix to the installer script itself reaches every future user immediately, without requiring a new release tag just to fix the installer. The *artifact it fetches* is always resolved dynamically via the GitHub "latest release" API at run time — so a user always gets the current release's tooling, regardless of which commit the script itself was fetched from. This mirrors `uv`'s own installer exactly (the script URL is stable/branch-tracked; the thing it installs is always "whatever's current").

### Architecture compliance (binding invariants)

- No AD/architecture invariant is touched — this is a pure distribution/packaging concern, same category as Story 4.1 itself.
- `project-context.md` §1 (stdlib-only) doesn't apply to shell/PowerShell scripts the way it applies to Python — but the same spirit holds: no third-party dependency beyond what's already assumed present (`curl`, `unzip` on Unix; PowerShell's built-in `Invoke-WebRequest`/`Expand-Archive` on Windows — no `jq`, no external JSON library).

### Testing standards (project-context.md §5/§6)

- No pytest surface for the scripts themselves (AC 4) — same precedent as Story 2.7's git-hook shims and Story 1.6's MCP flow. Definition of Done is live E2E, executed for real on both scripts this environment can actually run (PowerShell natively; `.sh` via this environment's Git Bash).

### Source tree touched

```text
tools/build-release/install.sh    NEW    macOS/Linux one-command installer
tools/build-release/install.ps1   NEW    Windows PowerShell one-command installer
tools/build-release/INSTALL.md    UPDATE new "Quick install" section, existing manual steps preserved as the fallback path
```

Neither new script ships *inside* the release zip (`EXCLUDED_DIR_NAMES` in `tools/build-release/main.py` already excludes the whole `build-release/` directory from `tools/` packaging) — they must be fetched directly from the repo via `raw.githubusercontent.com`, since a developer running them has nothing installed yet.

### Project Structure Notes

New files under the existing `tools/build-release/` directory, alongside `main.py` and `INSTALL.md` — consistent with that directory already being "everything related to producing/documenting the release," not itself shipped in the artifact.

### References

- [Source: tools/build-release/main.py] — confirms `EXCLUDED_DIR_NAMES = {"__pycache__", "build-release"}`, i.e. why these new scripts must be fetched from the repo directly, not from inside the zip
- [Source: tools/build-release/INSTALL.md] — the existing Prerequisites table already documents `uv`'s own `irm .../install.ps1 | iex` pattern as precedent to mirror exactly
- [Source: project-context.md] — §8-12 branch/PR/DoD; the manual-E2E-only precedent already established for skill/script-level stories (Story 1.6, Story 2.7 Task 3/4)

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5

### Debug Log References

Live E2E only (no pytest surface, per AC 4): ran `install.sh` and `install.ps1` against real empty git repos with real network access to GitHub, against the actual latest release (v0.3.0). Verified: successful extraction matches a manually-extracted zip; `uv run tools/setup-hooks.py --repo-root .` runs clean immediately after; both scripts fail with a clear one-line message outside a git repo (exit 1 for `install.sh`; a catchable `throw` for `install.ps1`). Separately verified via `Get-Content install.ps1 -Raw | Invoke-Expression` inside a `try/catch` that `throw` (not `exit`) is required in `install.ps1`: an `irm | iex`-style invocation runs the script's code in the caller's own session, so `exit` would terminate the caller's whole PowerShell session rather than just the script — confirmed the session survives the `throw`.

Repo visibility: this project's GitHub repo (`jayanthchincholi26/ai-project-metrics-bmad`) was private, which would make both the release-API call and the raw-script fetch fail unauthenticated. Scanned full git history for secrets (`git log --all --diff-filter=A --name-only` + `git log --all -p` grepped for token/credential patterns) — clean, one doc reference to an env var name, no real values. Flipped the repo to public with the user's explicit confirmation (`gh repo edit --visibility public --accept-visibility-change-consequences`).

### Completion Notes List

- Implemented `install.sh` and `install.ps1` exactly as scoped: git-repo precondition, latest-release resolution via the GitHub API (no `jq`; POSIX `grep`/`sed` field extraction on the Unix side, `Invoke-RestMethod`'s native JSON parsing on Windows), download+extract+cleanup, next-step guidance.
- Added a "Quick install" section to `INSTALL.md` ahead of the existing manual "Install (per repository, once)" section; the manual steps are preserved verbatim as the explicit fallback (AC 5) — only step 1's wording gained a one-line pointer to the new section.
- Neither script ships inside the release zip (`tools/build-release/main.py`'s `EXCLUDED_DIR_NAMES` already excludes `build-release/`) — both are fetched directly via `raw.githubusercontent.com/.../main/...`, per the story's design decision.

### File List

tools/build-release/install.sh (new)
tools/build-release/install.ps1 (new)
tools/build-release/INSTALL.md (updated — new "Quick install" section)
