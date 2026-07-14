---
baseline_commit: 43bf4a9
---

# Story 4.6: One-Command Uninstall (`uninstall.sh` / `uninstall.ps1`)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer who installed this capture tooling into a test/scratch repo,
I want a single command that removes everything the install added,
so that I can reset a repo to a clean, pre-install state without hand-tracking every file/hook the installer and `setup-hooks.py` touched.

## Acceptance Criteria

1. **Given** a repo where the tooling was installed via Story 4.3's `install.sh`/`install.ps1` and `setup-hooks.py` has been run
   **When** the developer runs one documented `uninstall.sh` (macOS/Linux) or `uninstall.ps1` (Windows) command
   **Then** it removes exactly what those two steps added: the extracted `tools/` directory, `.claude/skills/story-kickoff/`, `INSTALL.md`, `.story-config.yaml.example` at the repo root; the four git hooks `setup-hooks.py` installs (`post-commit`, `post-checkout`, `post-merge`, `commit-msg` under `.git/hooks/`); and the Claude Code hook wiring in `.claude/settings.json`

2. **Given** a story may be mid-flight or already closed in that repo
   **When** uninstall runs
   **Then** it also removes, if present: `.story-config.yaml`, `.story.yaml`, `.story-events.jsonl`, `.story-events.pending.jsonl`, `.active-story`, `.active-claude-session`, and the `snapshots/` and `metrics-reports/` directories — i.e. every artifact any part of this tooling could have created, not just the install step's own files

3. **Given** this is a destructive operation (deletes real files, including committed output like `snapshots/`)
   **When** the script runs
   **Then** it prints exactly what it's about to remove and asks for a single y/N confirmation before deleting anything (no silent deletion, no `-Force`-by-default) — an explicit `--yes`/`-y` flag skips the prompt for scripted/CI use, but interactive use always confirms first

4. **Given** `.claude/settings.json` may contain hook entries this tooling did **not** add (a developer's own unrelated Claude Code settings)
   **When** uninstall touches that file
   **Then** it removes only the specific hook entries `setup-hooks.py` itself added (matched by the exact `tools/hooks/claude/*.py` command strings it writes), never the whole file wholesale, and never touches any other settings key — mirrors `setup-hooks.py`'s own "merge additively, never clobber" contract in reverse

5. **Given** these are shell/PowerShell scripts, same category as Story 4.3
   **When** Definition of Done is evaluated
   **Then** there is no automated pytest surface — Definition of Done is live E2E: install into a real scratch repo, run uninstall, confirm the repo returns to a bare `git init`-only state (`git status` shows nothing tracked-and-modified beyond what existed before install)

6. **Given** this doesn't touch the install scripts or existing distribution paths
   **When** this story is done
   **Then** `install.sh`/`install.ps1` (Story 4.3) and the zip/manual path (Story 4.1) are completely unchanged — this is a new, separate script pair, purely additive

## Tasks / Subtasks

- [ ] Task 1: write `uninstall.sh` (macOS/Linux) (AC: 1, 2, 3, 4)
  - [ ] Subtask 1.1: git-repo precondition check (same `-e ".git"` pattern as Story 4.3's fixed `install.sh`, worktree/submodule-safe)
  - [ ] Subtask 1.2: build the list of paths that exist and would be removed; print it; prompt `y/N` unless `--yes`/`-y` was passed
  - [ ] Subtask 1.3: remove the install-time files/dirs (`tools/`, `.claude/skills/story-kickoff/`, `INSTALL.md`, `.story-config.yaml.example`) and the four git hooks under `.git/hooks/`
  - [ ] Subtask 1.4: remove the capture-time artifacts (AC 2) if present
  - [ ] Subtask 1.5: surgically remove only this tooling's entries from `.claude/settings.json` (AC 4) — read the JSON, drop hook array entries whose `command` references `tools/hooks/claude/`, write back only if the file still parses as valid JSON afterward; if `.claude/settings.json` doesn't exist, skip silently (nothing to do)

- [ ] Task 2: write `uninstall.ps1` (Windows PowerShell) (AC: 1, 2, 3, 4)
  - [ ] Subtask 2.1: same precondition check, same list-then-confirm UX, same `-Yes` switch to skip the prompt
  - [ ] Subtask 2.2: same removal set as Task 1, PowerShell-native (`Remove-Item`, `ConvertFrom-Json`/`ConvertTo-Json` for the settings.json surgery)
  - [ ] Subtask 2.3: every failure path uses `throw`, never `exit` — same `irm | iex` safety rule Story 4.3 established (an `exit` inside a piped-and-invoked script kills the caller's whole terminal session, not just the script)

- [ ] Task 3: document it (AC: 1-6)
  - [ ] Subtask 3.1: add an "Uninstall" section to `tools/build-release/INSTALL.md`, after "Updating", presenting both commands (local-path invocation, since — like install.sh/ps1 — these aren't inside the release zip; same `raw.githubusercontent.com` fetch pattern as Story 4.3, same temporary-branch-pointer caveat already noted at the top of "Quick install")

- [ ] Task 4: live E2E, both platforms (AC: 1-6)
  - [ ] Subtask 4.1: real scratch repo — install (Story 4.3's script), run `setup-hooks.py`, copy+edit `.story-config.yaml`, run a kickoff/close cycle to produce `snapshots/`/`metrics-reports/` artifacts, then run `uninstall.ps1` and confirm every listed path is gone and `.claude/settings.json` (if other, unrelated keys were present) keeps those keys intact
  - [ ] Subtask 4.2: same for `uninstall.sh` via this environment's Bash tool
  - [ ] Subtask 4.3: confirm the y/N prompt genuinely blocks deletion on "n", and `--yes`/`-Yes` skips it cleanly
  - [ ] Subtask 4.4: confirm a clear failure message outside a git repo, and a graceful no-op (not a crash) when run against a repo where nothing was ever installed (nothing to remove)

## Dev Notes

### Scope — what this story is and is not

- Pure teardown counterpart to Story 4.3's install scripts — no change to what gets installed, no change to `setup-hooks.py`, `build-release/main.py`, or any capture logic itself.
- **Do NOT touch `install.sh`/`install.ps1` or the release zip.** This is a new, separate script pair living alongside them in `tools/build-release/`.
- **Do NOT make this a blind `rm -rf`.** AC 3/4 exist because this repo's own tooling philosophy (see `setup-hooks.py`'s "merged additively — existing settings preserved" contract, and AD-9 "never fail silently") extends naturally to teardown: a developer's own unrelated `.claude/settings.json` keys, or files this tooling never created, must never be touched.

### Reference: exactly what setup-hooks.py installs (must match exactly, don't guess)

Read `tools/setup-hooks.py` before writing either script — it defines the ground truth for what this story must reverse:
- `GIT_HOOKS = ("post-commit", "post-checkout", "post-merge", "commit-msg")` — these are the exact `.git/hooks/` filenames to remove.
- The Claude Code event names it wires (`SessionStart`, `SessionEnd`, `PreToolUse`, `PostToolUse`, `Stop`, `UserPromptSubmit`) and their corresponding `tools/hooks/claude/*.py` scripts — the settings.json surgery in Task 1.5/2.2 must match these exactly, not a guessed subset.
- `GITIGNORE_ENTRIES = (".story-events.jsonl", ".story-events.pending.jsonl", ".active-story", ".active-claude-session")` — these are exactly the capture-time files AC 2 must remove (uninstall does **not** need to touch `.gitignore` itself — leaving a few now-harmless ignore entries behind is not worth the complexity/risk of parsing and rewriting a developer's own `.gitignore`; call this out as an explicit non-goal in the PR).

### Architecture compliance (binding invariants)

- No AD/architecture invariant is touched — pure distribution/teardown tooling, same category as Story 4.3.
- AD-9 ("never fail silently") applies to the settings.json surgery specifically: if the JSON can't be parsed, or the write-back would corrupt it, fail loudly and leave the file untouched — never write a best-effort partial result.

### Testing standards (project-context.md §5/§6)

- No pytest surface (AC 5) — same manual-E2E-only precedent as Story 4.3/2.7/1.6. Definition of Done is real script execution against a real installed-then-populated scratch repo.

### Source tree touched

```text
tools/build-release/uninstall.sh    NEW    macOS/Linux teardown script
tools/build-release/uninstall.ps1   NEW    Windows PowerShell teardown script
tools/build-release/INSTALL.md      UPDATE new "Uninstall" section after "Updating"
```

Neither script ships inside the release zip (`EXCLUDED_DIR_NAMES` already excludes `build-release/`) — fetched directly via `raw.githubusercontent.com`, same as `install.sh`/`install.ps1`.

### References

- [Source: tools/setup-hooks.py] — the ground-truth list of exactly what this story must remove (GIT_HOOKS, the Claude Code event/script map, GITIGNORE_ENTRIES)
- [Source: tools/build-release/install.sh, install.ps1] — the sibling scripts this story mirrors in structure (git-repo precondition, `throw` not `exit` in PowerShell, same fetch pattern)
- [Source: tools/build-release/INSTALL.md] — where the new "Uninstall" section is added, and the existing "Local capture state (`.gitignore`)" section describing exactly which files are local-only vs. committed (informs AC 2's removal list)
- [Source: project-context.md §9] — AD-9 "never fail silently," applied here to the settings.json surgery

## Dev Agent Record

### Agent Model Used

_to be filled by dev-story_

### Debug Log References

_to be filled by dev-story_

### Completion Notes List

_to be filled by dev-story_

### File List

_to be filled by dev-story_
