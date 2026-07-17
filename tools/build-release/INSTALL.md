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
| 5 | JIRA/Confluence via MCP *(only if `source_of_truth` is `jira` or `confluence`)* | Kickoff auto-fills goal (both) and points/sprint (JIRA fully; Confluence partially — see below) through the same Atlassian MCP server — OAuth, **no personal API token** | see "JIRA / Confluence setup" below |

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
   `.claude/skills/story-kickoff/`, `.claude/skills/story-close/` (Story 6.2),
   `.claude/skills/log-review-defect/` (Story 6.3), and `.story-config.yaml.example`;
   nothing is overwritten) — or use "Quick install" above to skip the manual download.
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

**Review defects work differently from compile/test ones (Story 6.3).** The
`test_commands`/`build_commands` capture above is fully automatic — no AI action needed.
Review defects (findings from a pasted code review you've verified against the diff,
confirmed real, and fixed) are captured by a third skill, `log-review-defect`, that
activates implicitly the same way `story-close` does — no command to remember, it
recognizes the moment on its own. For `source_of_truth: jira` stories, it also creates a
real Jira Subtask under the story's parent issue with a story-points value (default 1,
override via `jira_points_field` same as the points-reading config above) — never for a
declined or stale finding, only one confirmed real and actually fixed.

**Important — do step 2 before opening a Claude Code session in this repo.** Hooks (and
MCP server connections, and custom slash commands) are only discovered at a session's
*start* — they never retroactively apply to a session already open. If a Claude Code
panel was already open in this window before you ran step 2, **reload the window**
(Ctrl+Shift+P → "Developer: Reload Window") or start a brand-new session; don't reuse the
old one. Also open the repo folder itself as your editor's workspace root (not a parent
folder), or Claude Code won't see the kickoff skill.

## JIRA / Confluence setup (only for `source_of_truth: jira` or `confluence`)

Both backends connect through the **same** Atlassian Remote MCP Server — if you've already
done this for JIRA, Confluence needs no separate connection (and vice versa):

1. Connect the Atlassian Remote MCP Server — once per machine **and per project path**
   (this is local-scope, it does not carry over to a different folder):
   ```
   claude mcp add --transport http atlassian https://mcp.atlassian.com/v1/mcp/authv2
   ```
2. Run `/mcp` inside the Claude Code session you'll use for kickoff, and authenticate —
   a browser OAuth flow under your own Atlassian account. No API token is created or
   stored anywhere.
3. **JIRA only** — if your site uses non-default custom fields for story points or
   sprint, override them in `.story-config.yaml`:
   ```yaml
   jira_points_field: customfield_10016   # default
   jira_sprint_field: customfield_10020   # default
   ```
   Kickoff also transitions the issue to an active-work state automatically once it
   fetches successfully (Story 6.1) — checked in order: `jira_in_progress_transition`
   below if set, else `"In Progress"`, `"In Development"`, `"Doing"`. Closing a
   JIRA-backed story (Story 6.2) does the same for the Done-equivalent state, checked
   in order: `jira_done_transition` if set, else `"Done"`, `"Closed"`, `"Resolved"`:
   ```yaml
   jira_in_progress_transition: In Progress   # override only if none of the above match your workflow
   jira_done_transition: Done                 # override only if none of the above match your workflow
   ```
4. **Confluence only** — read this before your first kickoff: the connected MCP server
   can fetch a page's title and body, but **cannot read Confluence page labels today**
   (a confirmed, currently-open platform gap — not something this tooling can work
   around). This project's points/sprint auto-fill has always worked via `points-<number>`/
   `sprint-<name>` page labels, so **whenever MCP tools are available in the session**
   (i.e. you did steps 1-2 above), kickoff fetches your **goal** (the page title)
   automatically but always asks you to enter **points/sprint manually** — this is true
   even if the environment variables below happen to be set, since MCP is preferred
   whenever it's available. The **only** way to get real label-based points/sprint
   auto-fill is to skip the MCP connection for this session entirely and rely purely on
   the Story 1.4 script path instead, which reads labels directly via Confluence's REST
   API using a personal API token (same posture as pre-MCP JIRA):
   ```
   CONFLUENCE_BASE_URL=https://your-site.atlassian.net/wiki
   CONFLUENCE_EMAIL=you@example.com
   CONFLUENCE_API_TOKEN=<a personal API token>
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
8. Check `snapshots/<story-id>.v1.rev1.json`. Confused about what a field means or how it's
   calculated? The snapshot itself, the markdown report, and the dashboard all explain their
   own fields inline now (a `field_guide` section in the JSON, a "Field Guide" appendix in
   the report, hover tooltips in the dashboard) — "Known limitations" below adds deeper
   context on specific gaps, it isn't the only place to look.
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

**Want to preview current metrics without closing the story?** Running the snapshot
assembler for real always closes the story — its existence is this tool's authoritative
"done" signal (see "Known limitations" below). To inspect what your metrics *would* look
like right now (e.g. to confirm a defect-capture hook fired correctly) without triggering
that, add `--dry-run`:
```
uv run tools/snapshot-assembler/main.py --repo-root . --dry-run
```
Prints the full computed snapshot to stdout — no file is written, nothing is consumed,
and the story is left exactly as open as it was before you ran it. Not available on the
`opsx-wrapper archive` path (its `openspec archive` half isn't itself previewable) — use
the bare assembler command above instead.

**Step order (2 vs. 3) only matters for the point estimate, never for correctness** —
kickoff works fine run before `/opsx:propose` too, it just falls back to a plain ask
instead of an auto-computed suggestion (Phase-1 needs a real `tasks.md` to read).

## Daily use — JIRA flow (`source_of_truth: jira`)

1. `git checkout -b story/<branch-name>`.
2. In chat: *"kick off this story \<issue-key\>"* — kickoff fetches points/goal/sprint
   automatically via the connected Atlassian MCP tools; confirm or override the values.
   Writes `.story.yaml`, then automatically transitions the issue to an active-work
   state (Story 6.1) — see "JIRA / Confluence setup" above and "Known limitations"
   below if it doesn't pick the state you expect.
3. *(only if your project uses openspec SDD)* `/opsx:propose <change-name>` — do this
   **after** kickoff for JIRA (see note below), describing the work in your own words.
4. *(openspec only)* `/opsx:apply`.
5. Work normally — same silent capture as the docs-only flow.
6. Commit and push.
7. Close the story: `uv run tools/opsx-wrapper/main.py archive <change-name>` (or, without
   openspec, `uv run tools/snapshot-assembler/main.py --repo-root .`). Before running either
   command in a live Claude Code chat, a new skill (Story 6.2) automatically discovers the
   issue's open defect sub-tasks, ensures each has a story-points value, and asks **one**
   confirmation ("This will close N sub-task(s) and transition the parent JIRA issue `<KEY>`
   to Done — proceed?"). Declining still runs the close command normally — only the JIRA-side
   sync is skipped. See "Known limitations" below for when this doesn't apply.
8. Check the resulting snapshot under `snapshots/` — every field explains itself inline (see
   the docs-only flow's step 8 above).
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

## Daily use — Confluence flow (`source_of_truth: confluence`)

1. `git checkout -b story/<branch-name>`.
2. In chat: *"kick off this story \<full Confluence page URL\>"* — paste the **complete**
   page URL, not a short link (a short link's numeric page ID can't be resolved by the
   MCP tools — open it in a browser first if that's all you have, then paste the
   resulting full URL, which looks like `.../wiki/spaces/<SPACE>/pages/<NUMERIC-ID>/<Title>`).
   Kickoff fetches your **goal** (the page title) automatically via the connected
   Atlassian MCP tools; you'll always be asked to confirm **points** and enter **sprint**
   manually (see "JIRA / Confluence setup" above for why — an MCP platform gap, not a
   bug). Writes `.story.yaml`.
3. *(only if your project uses openspec SDD)* `/opsx:propose <change-name>` — do this
   **after** kickoff, same reasoning as the JIRA flow above (`/opsx:propose` can't fetch
   Confluence content either).
4. *(openspec only)* `/opsx:apply`.
5. Work normally — same silent capture as the other flows.
6. Commit and push.
7. Close the story: `uv run tools/opsx-wrapper/main.py archive <change-name>` (or, without
   openspec, `uv run tools/snapshot-assembler/main.py --repo-root .`).
8. Check the resulting snapshot under `snapshots/` — every field explains itself inline (see
   the docs-only flow's step 8 above).
9. *(optional)* Generate a human-readable report:
   ```
   uv run tools/metrics-report/main.py --repo-root .
   ```
   Same command as the other flows — writes `metrics-reports/metrics-<MMDDYYYY>.md`.
10. *(optional)* Generate the leadership dashboard: `uv run tools/dashboard/main.py --repo-root .`
    — same command as the other flows, writes `metrics-reports/dashboard.html`.

**Same step-order reasoning as JIRA:** `/opsx:propose` has no Confluence-fetching
capability either — the real Atlassian MCP fetch only exists inside `story-kickoff`
itself, so kickoff must run first here too. Phase-1's estimate will still be null at
that point, same as JIRA — expected, not a bug.

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
- Story metadata pulled from JIRA/Confluence (ticket title, points, sprint) — see "JIRA /
  Confluence setup" above for what that connection can read and write.

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

**In VS Code, closing the chat session via the panel's "x" button does not reliably fire
`SessionEnd` at all** — a Claude Code platform gap, not something this tool's `session_end.py`
can work around. `SessionEnd`'s documented trigger reasons (`clear`, `logout`,
`prompt_input_exit`, etc.) are all CLI-oriented, and even there it's known to misfire (doesn't
fire on `/clear` or `/exit` in some versions — only on Ctrl+D). Closing the panel just tears
down the process without guaranteeing the hook runs, so a story can show
`token_cost.reason: "no AI session_end event observed for this story"` even though you did
close the session. To make `SessionEnd` actually fire, end the session with `/exit` followed
by Ctrl+D (or close the whole VS Code window) rather than the chat panel's "x" button.

**`token_cost.reason: "no AI session_end event observed for this story"` specifically means
zero `session_end` events were seen for this story** — distinct from a `token_cost_reason`
surfaced *from* a session_end event (e.g. a transcript read failure). The most common cause is
the VS Code "x"-button gap above, not a bug in the reducer.

**When a story has multiple AI sessions and only some of them close cleanly, `token_cost`
now says so explicitly instead of surfacing an unrelated session's own reason.** `token_cost`
exposes both `sessions_started` (every `session_start` seen) and `sessions_observed` (every
`session_end` seen) — a gap between the two means at least one session never closed. When that
happens, `reason` names the gap (e.g. `"1 of 3 AI session(s) for this story never sent
session_end..."`) rather than showing the first *closed* session's own reason, which can belong
to a short, unrelated reconnect blip and have nothing to do with the session that actually did
the story's real work.

**Confluence kickoff never auto-fills points/sprint via MCP — only the goal (page title).**
This project's points/sprint auto-fill convention (`points-<number>`/`sprint-<name>` page
labels) predates the Atlassian MCP server's Confluence support, and the MCP server has no
label-read capability at all today (a confirmed, currently-open platform gap). Whenever MCP
tools are available in the kickoff session, you'll always be asked to confirm points and
enter sprint manually for a Confluence-backed story — this is a genuine capability gap in
the MCP server itself, not something a future story in this tooling can silently fix, short
of the platform adding label support or you switching to the script-based fallback (see
"JIRA / Confluence setup" above), which requires a personal API token.

**The automatic "In Progress" transition (Story 6.1) only happens via the MCP fetch
path — not the script fallback, not the plain manual ask.** `tools/adapters/jira/main.py`
(the personal-API-token fallback) has no transition capability at all, so a kickoff that
falls back to it, or all the way to a plain unassisted ask, writes the manifest correctly
but never touches the issue's JIRA status. A transition failure for any reason (no
matching workflow state, permission denied, the issue already active) is never a kickoff
failure either — it's reported as a short note *after* the normal kickoff summary, and
kickoff has already fully succeeded by that point regardless of what happens next.

**The close-time sub-task/parent "Done" sync (Story 6.2) only happens inside a live
Claude Code chat turn — never when the close commands run in an external terminal.**
There's no assistant turn to intercept a directly-run `tools/opsx-wrapper/main.py archive`
or `tools/snapshot-assembler/main.py`, and MCP tools are categorically unreachable outside
one — the same category of platform gap as the `SessionEnd`/VS-Code-"x"-button limitation
above, not something this project's own code can work around. Run these commands by asking
Claude Code to do it (or let it do so as part of a normal close conversation) if you want
the JIRA sync to happen.

**Review defect sub-tasks now get a story-points value at creation time (Story 6.3),
not just as a close-time safety net.** The `log-review-defect` skill sets it when the
subtask is first created; the close-time check in `story-close` (Story 6.2) remains as a
safety net for any older sub-task that predates this fix. Same terminal-run limitation as
above — `log-review-defect` only activates inside a live Claude Code chat turn.

**Running the snapshot assembler always closes the story — its existence is the
authoritative signal every other producer relies on to know a story is done** (a closed
story's `.story.yaml` is what the next `story-kickoff` checks for). There is no "just
show me the current numbers" mode by default — use `--dry-run` (see "Daily use" above) if
you want to inspect in-progress metrics without triggering that.

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

`uninstall.sh`/`uninstall.ps1` remove everything Install added — `tools/`, all three skills
(`story-kickoff`, `story-close`, `log-review-defect`), `INSTALL.md`, `.story-config.yaml.example`, the four git hooks, this tooling's own
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
- `claude mcp list` shows the Atlassian MCP server as `Connected`, but a kickoff run says
  no JIRA/Confluence MCP tools are available: same root cause as the two issues above — the session was
  started before the server finished connecting, and a session's tool list doesn't refresh
  mid-session. Reload the window / start a new Claude Code session, then retry kickoff.
