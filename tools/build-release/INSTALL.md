# AI Metrics Capture — Install

Automatic PM/engineering/time/token metrics as a byproduct of your normal dev flow.
This package adds capture tooling to **your own repository** — no server, no background
service, fully offline (only a per-story snapshot ever leaves your machine, and only when
you publish it).

## Prerequisites

Check these **in order**:

| # | Requirement | Why | Check |
| --- | --- | --- | --- |
| 1 | Git | Capture hooks are git hooks; branch-per-story is assumed for time attribution | `git --version` |
| 2 | uv | **uv** is a fast Python package/project manager — every script here runs via `uv run`, and uv **provisions its own Python automatically**, no separate Python install needed | `uv --version` — if empty/not found, see the install command below |
| 3 | Python 3.8+ | Informational only if step 2 succeeded — uv manages its own Python. A bare `python --version` failing (e.g. Windows' Microsoft Store stub) is **not a blocker** as long as `uv --version` works | `python --version` (optional check) |
| 4 | Claude Code | AI-session capture (the default `ai_tool: claude-code` adapter) | the VS Code extension or CLI |
| 5 | JIRA via MCP *(only if your project uses JIRA)* | Kickoff auto-fills points/goal/sprint through a JIRA MCP server — OAuth, **no personal API token** | see "JIRA setup" below |

No third-party Python packages are needed at runtime — every script is standard-library only.

If `uv --version` is empty/not found, install it (Windows PowerShell):
```
powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
See [docs.astral.sh/uv/getting-started/installation](https://docs.astral.sh/uv/getting-started/installation/) for other platforms, then restart your terminal.

## Package install (`uvx`) — not yet published

The most convenient path, once this package is actually published:
```
uvx ai-metrics-capture install
```
Run once at your repository root — no URL, branch name, or manual download to
remember, same on-disk result as the other two paths below. **Not live yet**:
Story 4.5 built the packaging (`pypi-package/`), but real PyPI publishing still
needs a human to wire a publish secret and run it — that step, not a branch
promotion cadence, is now the only thing gating it (Story 4.2's original
`develop`→`main` premise was dropped 2026-07-15 in favor of `main` as the only
trunk; see `project-context.md` §10). Use one of the two paths below until this
section is updated to say otherwise.

## Quick install (recommended for now)

One command, run once at your repository root — fetches the latest release and
extracts it for you (equivalent to Install step 1 below, without the manual zip
download):

**macOS/Linux:**
```
curl -fsSL https://raw.githubusercontent.com/jayanthchincholi26/ai-project-metrics-bmad/main/tools/build-release/install.sh | sh
```

**Windows (PowerShell):**
```
irm https://raw.githubusercontent.com/jayanthchincholi26/ai-project-metrics-bmad/main/tools/build-release/install.ps1 | iex
```

Then continue at Install step 2 below. Prefer the manual zip download instead
(e.g. air-gapped machine, or you want to inspect the contents first)? Step 1
below is the manual alternative to this command.

## Install (per repository, once)

1. Extract this zip **at your repository root** (it adds `tools/`,
   `.claude/skills/story-kickoff/`, and `.story-config.yaml.example`; nothing is
   overwritten) — or use "Quick install" above to skip the manual download.
2. From the repo root, run:
   ```
   uv run tools/setup-hooks.py --repo-root .
   ```
   Installs git hooks into `.git/hooks/`, wires the Claude Code hook entries into
   `.claude/settings.json` (merged additively — existing settings preserved), and
   auto-appends the local-capture-state entries to `.gitignore` (see below). Each
   developer runs this once per clone.
3. Declare your project's PM tool **once**: copy `.story-config.yaml.example` to
   `.story-config.yaml` at the repo root, then uncomment and edit what applies
   (this file is never created or copied for you automatically — its absence
   defaults to docs-only, so declaring it stays your explicit choice):
   ```yaml
   source_of_truth: jira   # or: confluence | docs-only (default when absent)
   ai_tool: claude-code    # default when absent

   # Optional — real cost figures per story snapshot. All three are optional and
   # absent by default; without them, token_cost.cost_usd and estimated_cost.usd
   # stay null (never a fabricated number computed from a missing rate):
   # hourly_rate: 10        # USD/hr, used for estimated_cost
   # ai_input_rate: 1.25    # USD per 1,000,000 input tokens
   # ai_output_rate: 5.00   # USD per 1,000,000 output tokens

   # Optional — automatic compile/test defect capture. Comma-separated command
   # patterns; a matching Bash command gets a harmless exit-code marker
   # silently appended (Claude Code doesn't expose a command's exit code to
   # hooks on its own) so a failure can be detected and logged as a defect
   # automatically. Absent by default (no capture, no command rewriting,
   # without this opt-in). Only the matched pattern name is ever recorded,
   # never the command/output:
   # test_commands: pytest, npm test
   # build_commands: tsc --noEmit, ruff check
   ```
4. Commit `tools/`, `.claude/skills/`, and `.story-config.yaml` so every teammate gets the
   same setup from a plain clone (they still each run step 2 once).

**Important — do step 2 before opening a Claude Code session in this repo.** Hooks (and
MCP server connections, and custom slash commands) are only discovered at a session's
*start* — they never retroactively apply to a session already open. If a Claude Code
panel was already open in this window before you ran step 2, **reload the window**
(Ctrl+Shift+P → "Developer: Reload Window") or start a brand-new session; don't reuse the
old one. Also open the repo folder itself as your editor's workspace root (not a parent
folder), or Claude Code won't see the kickoff skill.

## JIRA setup (only for `source_of_truth: jira`)

1. Connect the Atlassian Remote MCP Server — once per machine **and per project path**
   (this is local-scope, it does not carry over to a different folder):
   ```
   claude mcp add --transport http atlassian https://mcp.atlassian.com/v1/mcp/authv2
   ```
2. Run `/mcp` inside the Claude Code session you'll use for kickoff, and authenticate —
   a browser OAuth flow under your own JIRA account. No API token is created or stored
   anywhere.
3. If your JIRA site uses non-default custom fields for story points or sprint, override
   them in `.story-config.yaml`:
   ```yaml
   jira_points_field: customfield_10016   # default
   jira_sprint_field: customfield_10020   # default
   ```

## Daily use — docs-only flow (`source_of_truth: docs-only`, or absent)

1. `git checkout -b story/<branch-name>`.
2. *(only if your project uses openspec SDD, and you want a real Phase-1 point
   estimate)* `/opsx:propose <change-name>` — a name you choose, kebab-case; never the
   story ID. Do this **before** kickoff for docs-only, so the Phase-1 estimator has a
   real `tasks.md` to read.
3. In chat: *"kick off this story"* — confirm the prompts (story name, points, goal,
   milestone — say "none" if you don't track sprints/milestones). Writes `.story.yaml`;
   capture runs silently from here.
4. *(openspec only)* `/opsx:apply` — implements against the proposal.
5. Work normally. Commits, checkouts, merges, AI sessions, and active time are captured
   automatically. Nothing to start, stop, or report.
6. Commit and push.
7. Close the story — **one command**, archives the openspec change and produces the
   snapshot:
   ```
   uv run tools/opsx-wrapper/main.py archive <change-name>
   ```
   Without openspec, just:
   ```
   uv run tools/snapshot-assembler/main.py --repo-root .
   ```
8. Check `snapshots/<story-id>.v1.rev1.json`.
9. *(optional)* Generate a human-readable report from all accumulated snapshots:
   ```
   uv run tools/metrics-report/main.py --repo-root .
   ```
   Writes/overwrites `metrics-reports/metrics-<MMDDYYYY>.md` (grouped by the day each
   story closed) — safe to re-run any time, always fully regenerated from the
   (immutable) JSON snapshots, never appended to.
10. *(optional)* Generate a single shareable leadership dashboard across every story:
    ```
    uv run tools/dashboard/main.py --repo-root .
    ```
    Writes/overwrites `metrics-reports/dashboard.html` — a self-contained file (no
    server, no network calls) you can open by double-clicking or share directly.
    Same regeneration contract as the report above.

**Don't confuse `/opsx:archive` (the Claude Code slash command) with the wrapper command
above.** The slash command only calls the underlying `openspec archive` — it produces no
snapshot. `tools/opsx-wrapper/main.py archive <name>` wraps the same CLI call and
*additionally* runs the snapshot assembler on success (failing loudly if that step
breaks) — it's the one command to actually close out a story's metrics. If you already
ran `/opsx:archive` and just want the snapshot, `uv run tools/snapshot-assembler/main.py
--repo-root .` alone is fine too.

**The change name (step 2) and the story ID (step 3) are unrelated identifiers** —
nothing links them by name; they coexist because a project normally has one story (and
one openspec change) active per branch at a time.

**Step order (2 vs. 3) only matters for the point estimate, never for correctness** —
kickoff works fine run before `/opsx:propose` too, it just falls back to a plain ask
instead of an auto-computed suggestion (Phase-1 needs a real `tasks.md` to read).

## Daily use — JIRA flow (`source_of_truth: jira`)

1. `git checkout -b story/<branch-name>`.
2. In chat: *"kick off this story \<issue-key\>"* — kickoff fetches points/goal/sprint
   automatically via the connected Atlassian MCP tools; confirm or override the values.
   Writes `.story.yaml`.
3. *(only if your project uses openspec SDD)* `/opsx:propose <change-name>` — do this
   **after** kickoff for JIRA (see note below), describing the work in your own words.
4. *(openspec only)* `/opsx:apply`.
5. Work normally — same silent capture as the docs-only flow.
6. Commit and push.
7. Close the story: `uv run tools/opsx-wrapper/main.py archive <change-name>` (or, without
   openspec, `uv run tools/snapshot-assembler/main.py --repo-root .`).
8. Check the resulting snapshot under `snapshots/`.
9. *(optional)* Generate a human-readable report:
   ```
   uv run tools/metrics-report/main.py --repo-root .
   ```
   Same command as the docs-only flow — writes `metrics-reports/metrics-<MMDDYYYY>.md`.
10. *(optional)* Generate the leadership dashboard: `uv run tools/dashboard/main.py --repo-root .`
    — same command as the docs-only flow, writes `metrics-reports/dashboard.html`.

**Why JIRA's step order differs from docs-only's:** `/opsx:propose` has no JIRA-fetching
capability of its own — it only accepts a kebab-case name or a plain-text description you
type. Give it a JIRA URL before kickoff has run and it will either fail or silently fall
back to unauthenticated `WebFetch`, which can't reach an authenticated Atlassian page.
The real Atlassian MCP fetch only exists inside `story-kickoff` itself. So for JIRA,
kickoff must run first; Phase-1's estimate will still be null at that point (no
`tasks.md` exists yet) — expected, not a bug.

## Team dashboard — one-click, no local install needed (Story 5.9)

Once several developers have merged story branches (each carrying their own committed
`snapshots/*.json`), anyone with repo access can generate a consolidated leadership
dashboard **without running anything locally**: this install ships a GitHub Actions
workflow at `.github/workflows/generate-dashboard.yml`, triggered manually from the
Actions tab (**Actions → generate-dashboard → Run workflow**). It checks out the repo,
runs the same `metrics-report`/`dashboard` tools documented above, and uploads the result
as a downloadable workflow artifact (not committed to the repo — same "you decide whether
and how to share it" boundary as running these tools locally).

**One-time setup, before relying on approval-gating (do this once per repo, in GitHub's
web UI, not via this tooling):** by default, anyone with **Write** access to the repo can
trigger this workflow (a GitHub-enforced baseline — no config needed for that much). If
you want to restrict it further to specific approvers only:

1. Repo **Settings → Environments → New environment**, name it exactly `dashboard-publish`
   (the workflow already references this name).
2. Under that environment, enable **Required reviewers** and add whoever should approve a
   run (e.g. just you, or a small leads list).
3. From then on, anyone can still click "Run workflow," but the job pauses until an
   approved reviewer signs off before it actually executes.

If you skip this setup, the workflow still works — it just runs immediately for anyone
with Write access, ungated.

## Local capture state (`.gitignore`)

`uv run tools/setup-hooks.py --repo-root .` (Install step 2) automatically adds these
lines to your `.gitignore`:

```
.story-events.jsonl
.story-events.pending.jsonl
.active-story
.active-claude-session
```

If any of these was already git-tracked from before this was automatic, the installer
prints a `warning:` to stderr naming the file and the fix (`git rm --cached <file>`) —
don't ignore it: a tracked `.story-events.jsonl` silently forks and discards captured
events every time you switch between story branches, with no error at all.

`snapshots/` and `metrics-reports/` are different — both are meant to be **committed**,
not ignored. They're generated *output* (an immutable JSON snapshot per story close, a
human-readable markdown rendering of it, and the self-contained `dashboard.html`), shared
with your team the same way any other tracked file is, unlike the genuinely-local
`.story-events.jsonl` family above. The dashboard specifically has **no publishing
mechanism of its own** — it's a local file only; you decide whether and how to share it,
same as any other file in your repo (worth a second thought before sharing outside the
team, since it may summarize cost figures).

## Data use and privacy

This tool captures **team/process-level metrics only** — time on a story, AI cost,
points planned vs. used, defect counts. It is not intended for, and should not be used
for, individual performance evaluation. If your team is piloting this tool, confirm this
framing with participants before relying on the data in any review or reporting context.

What is captured, precisely:
- Git activity (commits, checkouts, merges) and timestamps.
- AI-session duration, token counts, and cost — **never prompt or response content**.
  `tools/hooks/claude/user_prompt_submit.py` emits only a prompt's character count, and
  `session_end.py` reads only the transcript's `usage.input_tokens`/`output_tokens`
  fields — the actual conversation text is never read, stored, or transmitted anywhere.
- Story metadata pulled from JIRA/Confluence (ticket title, points, sprint) — see "JIRA
  setup" above for what that connection can read and write.

What the Atlassian connection can write: creating a JIRA sub-task when a bug is logged
against a JIRA-tracked story is the only write this tool performs. The OAuth grant itself
is scoped by your own existing JIRA permissions, not narrowed to a single project by this
tool — if you can already create issues in a project through JIRA's own UI, this
connection can too, for that same project.

## Known limitations

**`token_cost` is accurate per-story only when AI sessions and stories stay 1:1.**
`session_end.py` sums an entire Claude Code session's transcript, start to finish, only
once `SessionEnd` actually fires — it has no concept of which story was active during
which part of that session. This is exactly right for the intended pattern this tool is
built around (one branch per story: kick off, work, close, move on, closing or reloading
the AI session somewhere around when the story closes). It silently degrades once that
assumption breaks:

- **The AI session never closes/reloads at all** (e.g. the developer keeps one long-running
  session open across many unrelated stories for days): `token_cost` stays `null` with an
  honest reason for every story worked during that time, until the session finally does
  end — not lost, just absent until then. Everything else (commits, checkouts, tool uses,
  active-time tracking, defect capture) is captured live regardless and is unaffected.
- **One continuous session spans multiple stories** (work on Story A, `git checkout` to
  Story B, all without closing/reloading the AI session in between, then eventually close):
  the *entire* session's token total gets attributed to whichever story is active at that
  final moment (Story B) — Story A's `token_cost` just shows `null`, never a fair split.

Bottom line: close or reload the AI session at least roughly once per story for `token_cost`
to mean what it looks like it means. This isn't enforced or detected today — a future story
would need to track transcript byte-offsets per story boundary to do better.

**`Duration` and `estimated_cost` reflect active work time, with one remaining edge case
(Story 3.4).** `estimated_cost_of()` prefers real, idle-excluded active time — reduced from
the event log's `time.slice_opened`/`time.slice_paused`/`time.slice_closed` events (gap
threshold 15 minutes by default) — falling back to a raw first/last-event span only when no
completed time slice was ever observed (an older snapshot, an `ai_tool` whose hooks don't
emit `time.slice_*`, or a story closed while its AI session is still open). That fallback
(Story 3.5) only scans genuine activity events (`git.*`, `ai.<tool>.*` other than the
session-boundary events themselves) for its span — a later administrative action (e.g.
re-running `opsx archive`/the assembler well after real work ended) can no longer stretch
a story's reported duration.

The one case this doesn't yet handle: **a mid-session story switch.** If a developer works
Story A, then `git checkout`s to Story B without closing or reloading the AI session in
between, the whole session's active time lands on whichever story was active when the
session finally closes (Story B) — Story A gets none of it from that session. This is the
same session-vs-story blending `token_cost` already has above, just for time instead of
dollars. Close or reload the AI session at least roughly once per story to avoid it — same
guidance as `token_cost`'s bottom line.

Meetings, discovery, manual QA, or deployment work that isn't a git or AI-tool action stays
invisible to this tool either way — captured neither as active time nor as idle time, since
nothing here observes it happening at all.

## Updating

Download the newer release zip, extract it at the repo root (overwriting `tools/` and the
skill), re-run `uv run tools/setup-hooks.py --repo-root .`, and commit the diff. Hook
installs are idempotent — re-running upgrades in place.

## Uninstall

`uninstall.sh`/`uninstall.ps1` remove everything Install added — `tools/`, the skill,
`INSTALL.md`, `.story-config.yaml.example`, the four git hooks, this tooling's own
entries in `.claude/settings.json` (surgically — any other hooks/keys you have are left
untouched), and, if present, anything a kickoff/close cycle created (`.story.yaml`,
`.story-events.jsonl`, `.active-story`, `snapshots/`, `metrics-reports/`, etc.). Like
Install, they're fetched directly from the repo, not shipped inside the release zip:

**macOS/Linux:**
```
curl -fsSL https://raw.githubusercontent.com/jayanthchincholi26/ai-project-metrics-bmad/main/tools/build-release/uninstall.sh | sh
```

**Windows (PowerShell):**
```
irm https://raw.githubusercontent.com/jayanthchincholi26/ai-project-metrics-bmad/main/tools/build-release/uninstall.ps1 | iex
```

This is destructive — it prints exactly what it's about to remove and asks for a `y/N`
confirmation first. To skip the prompt (scripted use): `curl ... | sh -s -- --yes`, or for
PowerShell, set `$env:AI_METRICS_UNINSTALL_YES = "1"` before piping (a switch argument
can't reach a script invoked via `irm | iex`).

## Troubleshooting

- `No pyproject.toml found` / files "missing": you're in the wrong directory — `cd` to the
  repo root and check with `Get-Location` / `pwd` first.
- `setup-hooks.py: error: --repo-root is required`: pass `--repo-root .` explicitly.
- Skill not appearing in Claude Code: the workspace root must be the repo folder itself;
  reopen the correct folder and start a new session.
- A hook append failure prints `METRICS CAPTURE FAILED` to stderr (after 3 retries) — it
  never blocks your commit or session; investigate disk/permissions when you see it.
- `claude mcp list` shows the JIRA MCP server as `Connected`, but a kickoff run says no
  JIRA MCP tools are available: same root cause as the two issues above — the session was
  started before the server finished connecting, and a session's tool list doesn't refresh
  mid-session. Reload the window / start a new Claude Code session, then retry kickoff.
