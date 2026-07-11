---
baseline_commit: 28b3f5761ac123f41e31abc7178f5bbde5c9f81e
---

# Story 2.7: Hook Commands Are Cwd-Independent (Absolute Paths)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want the capture hooks to keep working no matter which directory I `cd` into during a session,
so that a normal workflow (building/testing a subproject) never permanently breaks metrics capture — or my whole session.

## Acceptance Criteria

1. **Given** a repo where `tools/setup-hooks.py --repo-root <path>` has been run
   **When** `.claude/settings.json` is inspected
   **Then** every one of the six Claude hook commands (`SessionStart`, `SessionEnd`, `PreToolUse`, `PostToolUse`, `Stop`, `UserPromptSubmit`) is an **absolute path** to its script (resolved from `--repo-root` at install time), never a bare relative path

2. **Given** a live Claude Code session with hooks installed this way
   **When** the developer `cd`s into any subdirectory (or a subproject entirely) and continues working
   **Then** every hook continues to spawn and fire correctly — no `Failed to spawn` error, regardless of the session's current working directory at the moment a hook fires

3. **Given** an existing installation from before this fix (relative paths already in `.claude/settings.json`)
   **When** the developer re-runs `uv run tools/setup-hooks.py --repo-root .`
   **Then** the installer detects and upgrades the stale relative-path entries to absolute paths **in place** — not as a duplicate second entry alongside the old one

4. **Given** the git hook shims (`post-commit`, `post-checkout`, `post-merge`, `commit-msg`)
   **When** this story is implemented
   **Then** confirm whether they share this vulnerability or are protected by git's own guarantee that hooks always run with cwd at the repo root — **fix only if actually vulnerable; do not touch what isn't broken**

## Tasks / Subtasks

- [ ] Task 1: Make `command_for()` produce an absolute, repo-root-resolved path (AC: 1)
  - [ ] Subtask 1.1 (RED): extend `tests/test_setup_hooks.py` — after `run(fake_repo)`, every command string in every one of the six `CLAUDE_EVENTS` entries must satisfy `Path(command_substring).is_absolute()` (extract the path portion out of the `"uv run <path>"` command string) **and** resolve to a path actually under `fake_repo / "tools" / "hooks" / "claude"`. This will fail against the current relative-path implementation
  - [ ] Subtask 1.2 (GREEN): change `command_for(script: str) -> str` to `command_for(root: Path, script: str) -> str`, building the command from `(root / "tools" / "hooks" / "claude" / script).resolve()`. **Quote the path** in the command string (e.g. `f'uv run "{abs_path.as_posix()}"'`) — the repo root may contain spaces (e.g. a Windows username with a space in it), and the exact command-string parsing Claude Code performs when spawning the hook process is not something this codebase controls; quoting is the defensive, low-cost choice. Use `.as_posix()` for forward-slash consistency across platforms (matches how the existing test helper `our_commands()` substring-matches `"tools/hooks/claude/"`)
  - [ ] Subtask 1.3: `command_for()`'s only caller is `merge_settings()`, which itself needs `root` threaded through (`merge_settings(root: Path, settings: dict) -> dict`), and `merge_settings()`'s only caller is `main()` — update that call site too (`merge_settings(root, settings)`, where `main()` already has `root = Path(args.repo_root)`; resolve it once there, e.g. `root = Path(args.repo_root).resolve()`, rather than resolving separately inside `command_for()` each time)

- [ ] Task 2: Upgrade stale relative-path entries in place, don't duplicate (AC: 3)
  - [ ] Subtask 2.1 (RED): extend `tests/test_setup_hooks.py` — seed a `fake_repo`'s `.claude/settings.json` by hand with the **old-style relative-path** command for one event (e.g. `PreToolUse: "uv run tools/hooks/claude/pre_tool_use.py"`, no quotes, no absolute path), then run the installer. Assert: exactly **one** command remains wired for that event afterward (not two), and it's now the new absolute-path form. This is the regression this story exists to prevent — a naive "does an identical command already exist" check (the current `present = any(hook.get("command") == wanted ...)` logic) will **append a second entry** instead of upgrading the first, since the old and new command strings never match
  - [ ] Subtask 2.2 (GREEN): rewrite `merge_settings()`'s matching logic — instead of exact string equality against `wanted`, match any existing hook entry that references the script's filename, tolerant of the trailing quote Subtask 1.2 adds: `command.rstrip('"').endswith(script)` (a plain `command.endswith(script)` check **will not** match the new quoted form, since it now ends with `.py"` not `.py` — this is the one gotcha to get right here). When found, **overwrite that entry's `command` in place** with `wanted`. Only append a brand-new entry when no existing entry matches at all. Verify this doesn't disturb entries for *other* hooks a team may have added by hand (only match on `command` values that reference one of *our* six known script filenames)
  - [ ] Subtask 2.3: re-run the existing `test_second_run_is_idempotent` test unmodified — confirm it still passes (a second run against an already-upgraded install should produce byte-identical `settings.json`, not a second round of "upgrades")

- [ ] Task 3: Verify (don't assume) the git hook shims' exposure (AC: 4)
  - [ ] Subtask 3.1: read `tools/hooks/git/*.sh` (already confirmed during story creation: they also use relative paths, e.g. `uv run tools/hooks/git/post-commit.py "$@"`) and cross-check against the documented guarantee in `tools/hooks/_events.py`'s docstring and `ARCHITECTURE-SPINE.md` AD-8/`git_out()` comments: "cwd defaults to the ambient process cwd (correct for git hooks, which git itself invokes with cwd already at the repo — AD-8)"
  - [ ] Subtask 3.2: confirm this guarantee empirically, not just by reading the comment — in a real git repo, `cd` into a subdirectory, then run `git commit` (or trigger `post-checkout`/`post-merge`) and confirm the hook still fires correctly. Git's own documented behavior is that hooks are always invoked with cwd at the repository root regardless of where in the working tree the git command was run from — but this story's whole premise is "don't assume, verify," so prove it rather than citing the comment alone
  - [ ] Subtask 3.3: **if confirmed safe (expected outcome): make no code change to the git hook shims** — document the verification (what was tested, what was observed) in this story's Dev Agent Record so the "why we didn't fix this too" reasoning is preserved, not just assumed. If verification reveals the git shims are *also* vulnerable in some scenario, treat that as a new finding and extend Task 1/2's fix to `tools/hooks/git/*.sh` too — but do not preemptively rewrite them without evidence

- [ ] Task 4: Full regression, live E2E, and documentation parity (AC: 1-4)
  - [ ] Subtask 4.1: run `uv run pytest`, `uv run ruff check .`, and `uv run ruff format --check tools tests`
  - [ ] Subtask 4.2: manual E2E reproducing the exact failure this story fixes — in a real git repo with hooks installed via the fixed installer: start a Claude Code session, `cd` into an unrelated subdirectory (create one if needed, e.g. `mkdir sub && cd sub`), trigger a tool call and a `Stop` boundary, confirm **no** `Failed to spawn` error and that events still land in `.story-events.jsonl`/`.story-events.pending.jsonl` correctly. This is the scenario the user's own testing hit live — reproduce it, then prove the fix
  - [ ] Subtask 4.3: manual E2E for the upgrade path (AC 3) — take a repo with an old-style (relative-path) install already present (simulating a pre-fix pilot machine), re-run `uv run tools/setup-hooks.py --repo-root .`, confirm hooks fire correctly afterward with no duplicate entries
  - [ ] Subtask 4.4: if the repo root path itself contains a space (create a test folder with one, e.g. `test pilot 2/`), confirm hooks still install and fire correctly — this is the scenario Subtask 1.2's quoting decision exists to protect against; don't skip it just because it's inconvenient to set up
  - [ ] Subtask 4.5: no INSTALL.md prerequisite/step changes are expected from this story (it's a transparent bugfix to an already-documented install step) — but if `INSTALL.md`'s troubleshooting section would benefit from a line about this specific failure mode (in case a pilot developer hits it on an *older* release before upgrading), add one; note in the PR either way

## Dev Notes

### Scope — what this story is and is not

- This is a **bugfix to Story 2.1's existing deliverable** (the hook installer), not new capability. No new files, no new hook events, no new manifest fields.
- **Do NOT build in this story:** any change to what the hooks *do* once they fire (their capture logic in `tools/hooks/claude/*.py` and `tools/hooks/_events.py` is untouched); any change to the git hook shims unless Task 3 actually finds them vulnerable (expected: it won't, but verify per AC 4); a general "make Claude Code more resilient to a hook failing to spawn" — that's an Anthropic-side concern (worth a separate `/feedback` report), not something fixable in this codebase.

### Why this matters (severity context)

Found live during v0.2.0 pilot-simulation testing (2026-07-11): kickoff (Story 1.7) worked perfectly, then the developer did realistic follow-on work (`/opsx:apply`, building a proposed feature in a subdirectory) and `cd`'d into it. From that point, **every** subsequent tool call failed:
```
PreToolUse hook error: [uv run tools/hooks/claude/pre_tool_use.py]: error: Failed to spawn: `tools/hooks/claude/pre_tool_use.py`
Caused by: The system cannot find the path specified. (os error 3)
```
`Stop` failed identically on every turn boundary — an unrecoverable loop, session had to be killed and restarted. This is as close to "worst realistic pilot outcome" as this project has produced: a developer doing completely normal work (building a subproject) permanently breaks their own session with no in-session recovery path. Treat this as the highest-priority item in the current backlog.

### Architecture compliance (binding invariants)

- **AD-8** — "Hook scripts live in a git-tracked directory... a single committed setup script installs them... this setup script runs once per clone/checkout." This story doesn't change *what* AD-8 requires, only makes the installer actually deliver on the "keeps working" half of that promise — AD-8 never said hook commands must be relative, that was purely `setup-hooks.py`'s own (buggy) implementation choice.
- **AD-9** — "A producer that fails to append an event retries up to 3 times; if it still fails, it surfaces a visible error... Silence is never an acceptable outcome." This story is arguably an AD-9 violation in its own right: a hook that can't even *spawn* isn't retried 3 times and doesn't surface a clean, single visible error — it fails immediately and repeatedly on every subsequent call. Once this story's fix lands, that specific failure mode (spawn failure from a bad relative path) becomes structurally impossible, which is the cleanest way to satisfy AD-9 here — prevention over better error handling.
- **Existing test infrastructure** (`tests/test_setup_hooks.py`) already exercises `merge_settings()`/`command_for()` behavior with a `fake_repo` fixture and no real git operations — extend this pattern, don't introduce a new one.

### The AC-3 upgrade-in-place trap (read before writing Task 2)

The single most important design detail in this story: `merge_settings()`'s current "is this hook already wired" check is `hook.get("command") == wanted` — **exact string equality**. Once `wanted` changes shape (relative → absolute), that equality check can *never* match an old-style entry, so a naive fix would silently start **duplicating** every hook command on the first post-fix `setup-hooks` run on any already-installed machine — two `PreToolUse` entries firing on every tool call, both invoking the same underlying script twice. This is exactly the kind of subtle regression a green test suite could miss if Task 2's specific duplicate-prevention test (Subtask 2.1) isn't written first.

Match on "does this command reference our script," not "does this command exactly equal what we'd write today" — and be precise about *how*: once Subtask 1.2's quoting is in place, the command ends with `.py"` (trailing quote), so a naive `command.endswith(script)` **will not match**, silently reintroducing the exact duplication bug this task exists to prevent. Strip the trailing quote before comparing (`command.rstrip('"').endswith(script)`), or equivalent.

### Testing standards (project-context.md §5/§6)

- Everything in Tasks 1-2 is fully unit-testable with the existing `fake_repo` fixture pattern — no real git, no real Claude Code process, no real `uv run` execution needed (the installer only *writes* the command strings; it doesn't invoke them).
- Task 3's verification and Task 4's E2E scenarios are inherently unit-untestable (they require a real git repo, a real directory change, and — for Subtask 4.2 — ideally a real Claude Code session to reproduce the exact failure). Manual E2E is the Definition of Done for these, consistent with this project's established pattern for anything that can't be simulated in a fixture.
- One behavior per test, Arrange/Act/Assert, sentence-style names — matches every existing test file in this repo.

### Source tree touched

```text
tools/setup-hooks.py       UPDATE  command_for() takes root, builds absolute quoted path; merge_settings() matches by script filename, not exact string
tests/test_setup_hooks.py  UPDATE  absolute-path assertions; new upgrade-in-place (no duplicate) test
```

`tools/hooks/git/*.sh`, `tools/hooks/claude/*.py`, and `tools/hooks/_events.py` are **not** touched unless Task 3 finds a genuine problem (expected: it won't).

### Project Structure Notes

- No conflicts with the unified project structure. This story touches exactly the two files Story 2.1 created, nothing else.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.7] — the live-testing incident this story fixes, verbatim error and root-cause analysis
- [Source: tools/setup-hooks.py] — `command_for()`, `merge_settings()`, the exact code this story changes
- [Source: tests/test_setup_hooks.py] — existing `fake_repo` fixture, `run()`/`settings_of()`/`our_commands()` helpers to extend
- [Source: tools/hooks/git/post-commit.sh] — confirmed (2026-07-11, during story creation) also uses a relative path; Task 3 must verify whether this matters given git's cwd guarantee, not assume it doesn't
- [Source: ARCHITECTURE-SPINE.md#AD-8, AD-9] — hook installation invariant this story fulfills more completely; failure-visibility invariant this story satisfies via prevention
- [Source: tools/hooks/_events.py] — docstring's documented assumption that git always invokes hooks with cwd at repo root (the reasoning Task 3 must verify empirically, not just cite)
- [Source: project-context.md] — §1 stdlib-only, §2 atomic writes, §5-6 testing standards, §8-12 branch/PR/DoD

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
