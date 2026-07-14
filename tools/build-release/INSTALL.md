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

## Install (per repository, once)

1. Extract this zip **at your repository root** (it adds `tools/` and
   `.claude/skills/story-kickoff/`; nothing is overwritten).
2. From the repo root, run:
   ```
   uv run tools/setup-hooks.py --repo-root .
   ```
   Installs git hooks into `.git/hooks/`, wires the Claude Code hook entries into
   `.claude/settings.json` (merged additively — existing settings preserved), and
   auto-appends the local-capture-state entries to `.gitignore` (see below). Each
   developer runs this once per clone.
3. Declare your project's PM tool **once**, in `.story-config.yaml` at the repo root:
   ```yaml
   source_of_truth: jira   # or: confluence | docs-only (default when absent)
   ai_tool: claude-code    # default when absent
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

**Why JIRA's step order differs from docs-only's:** `/opsx:propose` has no JIRA-fetching
capability of its own — it only accepts a kebab-case name or a plain-text description you
type. Give it a JIRA URL before kickoff has run and it will either fail or silently fall
back to unauthenticated `WebFetch`, which can't reach an authenticated Atlassian page.
The real Atlassian MCP fetch only exists inside `story-kickoff` itself. So for JIRA,
kickoff must run first; Phase-1's estimate will still be null at that point (no
`tasks.md` exists yet) — expected, not a bug.

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

## Updating

Download the newer release zip, extract it at the repo root (overwriting `tools/` and the
skill), re-run `uv run tools/setup-hooks.py --repo-root .`, and commit the diff. Hook
installs are idempotent — re-running upgrades in place.

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
