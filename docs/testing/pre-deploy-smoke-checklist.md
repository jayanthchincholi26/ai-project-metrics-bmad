# Pre-Deploy Smoke Checklist — Capture Pipeline

Manual end-to-end run to confirm the full kickoff → capture → time-tracking → archive flow
works on a real machine before rolling out to a pilot team. Full test-case matrix (positive/
negative) lives in [test-cases.xlsx](test-cases.xlsx); this file is the quick smoke-test script
to run per machine/OS before a rollout.

Run `uv run pytest` first — this checklist is a supplement to the automated suite, not a
replacement for it. It exists because several real defects in this project (the Windows BOM
bug, the AD-7 mid-session-checkout precedence bug) were only caught by live E2E testing with a
real git repo and real hook invocations, not mocked unit tests.

## Before you start (findings from the first real run, 2026-07-10/11)

- **`cd` into the cloned folder** — `git clone <url>` creates a subfolder; running `uv` from the
  parent gives `No pyproject.toml found`.
- ~~**`git checkout develop`** — until Story 4.2 promotes `develop` to `main`, a fresh clone's
  default branch (`main`) has no `pyproject.toml`/`tools/`/`tests/` at all~~ — **resolved
  2026-07-15**: the planned `develop`/`main` two-tier promotion (Story 4.2) was dropped in favor
  of `main` as the only trunk (see `project-context.md` §10). A fresh clone's default branch now
  contains everything directly; no `checkout` step is needed for this anymore.
- **Windows: `git config core.longpaths true` before cloning** (or clone to a short path like
  `C:\w\`) — this repo's `_bmad-output/` paths exceed the 260-char limit from deep destinations
  and the clone fails with `Filename too long`.
- **Open the repo folder itself as the VS Code workspace root** (File → Open Folder →
  `ai-project-metrics-bmad`, not its parent). With the parent as root, Claude Code sees only
  global skills — `.claude/skills/` (including `story-kickoff`) is silently invisible, and the
  failure looks confusingly like a skills/hooks bug. Cost ~1 hour of misdiagnosis on the first
  run. Terminal `Get-Content` checks against `.active-story`/`.story-events.jsonl` fail the same
  way — run `Get-Location` first, always.
- **Hooks require the setup script to run before the session starts** — `SessionStart` fires
  once, at session start; installing hooks into a live session does nothing until the next one.
- **Check any Get-Content path failure against your cwd before suspecting the pipeline** — every
  "missing file" during the first run (3 separate times) was the parent-folder cwd, not a bug.

## Checklist

- [x] `uv run pytest` passes clean on this machine/OS before manual testing starts
      *(2026-07-10: 215/215 passed in 2.08s, Win11 + Python 3.14.6)*
- [x] Fresh scratch repo: `uv run tools/setup-hooks.py --repo-root .` installs hooks into
      `.git/hooks/` and merges Claude entries into `.claude/settings.json`
      *(2026-07-10: JSON ack, 4 git hooks + 6 Claude events wired. Note: `--repo-root` is
      required — the bare command errors)*
- [x] Run story-kickoff (docs-only): `.story.yaml` written with `story_id`, points, goal,
      sprint, `ai_tool` *(2026-07-10: `story-20260710-a145ba`; AD-4 no-ask, Phase-1 null
      fallback, and re-prompt behavior all correct. Transient `AskUserQuestion`
      InputValidationError on first attempt, self-recovered on retry)*
- [x] Commit a change: a `git.*` event is appended to `.story-events.jsonl`
      *(2026-07-10: `git.commit_msg` + `git.commit` with correct hash/branch/story_id)*
- [x] Start a Claude Code session: `.active-claude-session` marker appears, `ai.claude-code.*`
      events log *(2026-07-10: session_start/prompt/stop/session_end all captured across 5
      sessions; `token_cost` null-with-reason per AD-10)*
- [x] **While that session is live**, `git checkout` to another story branch: `.active-story`
      re-points `story_id` only — **no** `time.slice_*` event fires (Story 3.3 / AD-7)
      *(2026-07-11: verified both directions; `opened_at` preserved untouched)*
- [x] End the session: `time.slice_closed` fires, `.active-claude-session` is removed
      *(2026-07-10: multiple clean close pairs with correct `duration_seconds`)*
- [x] Idle-activity stamping: `last_activity_at` updates on prompt/tool-use activity
      *(2026-07-10 — full 15-min `time.slice_paused` simulation still outstanding)*
- [x] Snapshot: fixed envelope shape produced with honest nulls (`phase1_points: null`,
      `variance: null` + `reduced_confidence_reasons`, `token_cost` null-with-reason)
      *(2026-07-11: `story-20260710-ef967d.v1.rev1.json`, 31 events reduced, 21 pending
      backfilled per AD-1b. Run via the assembler directly — see caveat below)*
- [x] Re-run archive on the same story: a new `revision` is appended, prior untouched
      *(2026-07-11: rev2 alongside rev1, rev1 byte-identical; backfill idempotent, 0 on rerun)*

**Caveats from the first full run:**
- The `opsx archive` **wrapper path** was not fully exercised: the real `openspec` CLI was
  installed and correctly failed ("no changes directory") because the clone had no initialized
  openspec change — the wrapper correctly mirrored the failure with no event/no snapshot. The
  snapshot steps above ran the assembler directly (`uv run tools/snapshot-assembler/main.py
  --repo-root .`, the identical call the wrapper makes). Full wrapper E2E needs a project with a
  real openspec change — plan it as part of the pilot's first real story.
- Root cause of the openspec failure was a packaging bug, now fixed on `enhancements`:
  `openspec/changes|specs|archive` were empty dirs, invisible to git, so fresh clones lost them
  (`.gitkeep` added).
- Stale `.active-claude-session` observed after an abrupt VS Code close (SessionEnd never
  fired) — self-heals at next SessionStart; logged as an assembler reduced-confidence follow-up.

## OS-specific re-runs

- [ ] Repeat the checkout/commit steps above on **Windows** specifically — piped stdin BOM
      handling has broken 3 times in this project already (Stories 2.2, 2.3, and a related fix);
      don't assume a Linux/WSL pass covers it
- [ ] If the team has any non-`uv`-managed Python on PATH, confirm hooks still resolve correctly
      via `uv run --script`

## Sign-off

| Machine / OS | Tester | Date | Result |
|---|---|---|---|
| Windows 11 Pro, Python 3.14.6, uv 0.11.24 | Jayanth | 2026-07-10/11 | **PASS** (all core steps; wrapper E2E + 15-min idle simulation deferred — see caveats) |

## Epic 6 (JIRA lifecycle sync) pilot round — real, not a scripted re-run

Unlike the checklist above (a scripted pre-deploy run against a scratch repo), this round
was the user's own real pilot test of the JIRA daily-use flow (`v0.11.0`, then `v0.11.1`),
against a real JIRA site and a real GitHub-hosted test repo. Findings here are logged as
they were actually found — see the story files under
`_bmad-output/implementation-artifacts/6-*.md` and `epics.md`'s Epic 6 section for full
detail; this is a summary, not the record of truth.

- [x] Kickoff (`AI-143` and others), auto-transition to In Progress (Story 6.1): confirmed
      real, via independent re-fetch after the transition, not just trusting the write call
- [x] Sprint name + start/end dates captured at kickoff (Story 6.5): confirmed against real
      sprint data, including the null-dates case (a sprint that hadn't started yet)
- [x] Defect sub-task creation with a points value at creation time (Story 6.3): confirmed
      real, `AI-148` created with `customfield_10016: 1` set at creation
- [x] Close-time sub-task + parent → Done sync, points sync-back (Stories 6.2/6.4):
      confirmed real against `AI-143` and its sub-tasks
- [x] Dashboard Sprint Rollups table (Story 6.6): confirmed real via the user's own
      generated `dashboard.html` (`AI Sprint 20`, real dates, correct story count/status)
- [ ] ~~Story-close skill reliably triggers on any close-command invocation~~ — **real bug
      found 2026-07-23** ([GitHub #52](https://github.com/jayanthchincholi26/ai-project-metrics-bmad/issues/52)):
      pasting the raw close command as a literal chat message ran it directly via Bash with
      zero JIRA sync — no confirmation, no sub-task discovery, no transition. Root cause:
      the skill's implicit trigger depended on the model recognizing intent, not a
      deterministic interceptor. **Fixed in Story 6.8 / `v0.11.1`** — a `PreToolUse` hook
      now denies the raw command and redirects the assistant to the skill's flow. The
      fix's own gate logic was verified via real subprocess runs; the real Claude Code
      harness behavior (actual denial, actual redirect-message visibility to the assistant)
      is still pending the user's own retest — **update this row once that's confirmed.**
- **Known, unrelated finding** (not a bug — see `INSTALL.md`'s Known Limitations): a story
  showed `token_cost` stuck on `"no AI session_end event observed for this story"` across
  several real test rounds — root cause was ending the AI session via the VS Code panel's
  "x" button, which doesn't reliably fire `SessionEnd`. Resolved by ending sessions with
  `/exit` + Ctrl+D instead.
