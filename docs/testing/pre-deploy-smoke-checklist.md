# Pre-Deploy Smoke Checklist — Capture Pipeline

Manual end-to-end run to confirm the full kickoff → capture → time-tracking → archive flow
works on a real machine before rolling out to a pilot team. Full test-case matrix (positive/
negative) lives in [test-cases.xlsx](test-cases.xlsx); this file is the quick smoke-test script
to run per machine/OS before a rollout.

Run `uv run pytest` first — this checklist is a supplement to the automated suite, not a
replacement for it. It exists because several real defects in this project (the Windows BOM
bug, the AD-7 mid-session-checkout precedence bug) were only caught by live E2E testing with a
real git repo and real hook invocations, not mocked unit tests.

## Before you start (findings from the first real run, 2026-07-10)

- **`cd` into the cloned folder** — `git clone <url>` creates a subfolder; running `uv` from the
  parent gives `No pyproject.toml found`.
- **`git checkout develop`** — until Story 4.2 promotes `develop` to `main`, a fresh clone's
  default branch (`main`) has no `pyproject.toml`/`tools/`/`tests/` at all; `uv run pytest` fails
  with `Failed to spawn: pytest — program not found`.
- **Windows: `git config core.longpaths true` before cloning** (or clone to a short path like
  `C:\w\`) — this repo's `_bmad-output/` paths exceed the 260-char limit from deep destinations
  and the clone fails with `Filename too long`.

## Checklist

- [ ] `uv run pytest` passes clean on this machine/OS before manual testing starts
- [ ] Fresh scratch repo: `python tools/setup-hooks.py` installs hooks into `.git/hooks/` and
      merges Claude entries into `.claude/settings.json`; re-running it is a no-op (idempotent)
- [ ] Run story-kickoff (docs-only): `.story.yaml` written with `story_id`, points, goal,
      sprint, `ai_tool`
- [ ] Commit a change: a `git.*` event is appended to `.story-events.jsonl`
- [ ] Create a second story branch, `git checkout` into it (no live AI session): `.active-story`
      switches, and a `time.slice_closed` / `time.slice_opened` pair is appended
- [ ] Start a Claude Code session: `.active-claude-session` marker appears, `ai.claude-code.*`
      events log
- [ ] **While that session is live**, `git checkout` to a third story branch: `.active-story`
      re-points `story_id` only — confirm **no** `time.slice_*` event fires (Story 3.3 / AD-7
      precedence — the highest-risk regression in this pipeline)
- [ ] End the session: `time.slice_closed` fires, `.active-claude-session` is removed
- [ ] Simulate 15+ minutes idle, then trigger one tool-use event: `time.slice_paused` is
      recorded, story stays active
- [ ] Run `opsx archive`: snapshot produced with the fixed envelope shape (`schema_version,
      story_id, revision, pm_metrics, engineering_metrics, story_point_cost, token_cost`),
      including both the Phase-1 estimate and Phase-2 actual with a variance
- [ ] Run `opsx archive` again on the same story: a new `revision` is appended, the prior
      revision is untouched

## OS-specific re-runs

- [ ] Repeat the checkout/commit steps above on **Windows** specifically — piped stdin BOM
      handling has broken 3 times in this project already (Stories 2.2, 2.3, and a related fix);
      don't assume a Linux/WSL pass covers it
- [ ] If the team has any non-`uv`-managed Python on PATH, confirm hooks still resolve correctly
      via `uv run --script`

## Sign-off

| Machine / OS | Tester | Date | Result |
|---|---|---|---|
| | | | |
