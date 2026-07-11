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
| 2 | uv | **uv** is a fast Python package/project manager — every script here runs via `uv run`, and uv **provisions its own Python automatically**, no separate Python install needed | `uv --version` — if empty/not found, install from [docs.astral.sh/uv/getting-started/installation](https://docs.astral.sh/uv/getting-started/installation/) (Windows: `powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 \| iex"`), then restart your terminal |
| 3 | Python 3.8+ | Informational only if step 2 succeeded — uv manages its own Python. A bare `python --version` failing (e.g. Windows' Microsoft Store stub) is **not a blocker** as long as `uv --version` works | `python --version` (optional check) |
| 4 | Claude Code | AI-session capture (the default `ai_tool: claude-code` adapter) | the VS Code extension or CLI |
| 5 | JIRA via MCP *(only if your project uses JIRA)* | Kickoff auto-fills points/goal/sprint through a JIRA MCP server — OAuth, **no personal API token** | see "JIRA setup" below |

No third-party Python packages are needed at runtime — every script is standard-library only.

## Install (per repository, once)

1. Extract this zip **at your repository root** (it adds `tools/` and
   `.claude/skills/story-kickoff/`; nothing is overwritten).
2. From the repo root, run:
   ```
   uv run tools/setup-hooks.py --repo-root .
   ```
   This installs the git hooks into `.git/hooks/` and wires the Claude Code hook entries
   into `.claude/settings.json` (merged additively — your existing settings are preserved).
   Each developer runs this once per clone.
3. Declare your project's PM tool **once**, in `.story-config.yaml` at the repo root:
   ```yaml
   source_of_truth: jira   # or: confluence | docs-only (default when absent)
   ai_tool: claude-code    # default when absent
   ```
4. Commit `tools/`, `.claude/skills/`, and `.story-config.yaml` so every teammate gets the
   same setup from a plain clone (they still each run step 2 once).

**Important:** run step 2 *before* opening a Claude Code session in the repo — hooks wire
up at session start. If a session was already open, start a new one. And open the repo
folder itself as your editor's workspace root (not a parent folder), or Claude Code won't
see the kickoff skill.

## JIRA setup (only for `source_of_truth: jira`)

Connect the Atlassian Remote MCP Server once per machine:

```
claude mcp add --transport http atlassian https://mcp.atlassian.com/v1/mcp/authv2
```

Then run `/mcp` inside a Claude Code CLI session and authenticate — a browser OAuth flow
under your own JIRA account. No API token is created or stored anywhere.

If your JIRA site uses non-default custom fields for story points or sprint, override them
in `.story-config.yaml`:

```yaml
jira_points_field: customfield_10016   # default
jira_sprint_field: customfield_10020   # default
```

## Daily use

- **Start a story:** check out its branch, tell Claude Code *"kick off this story"*, and
  confirm points/goal/sprint (JIRA projects: just give the issue key). This writes
  `.story.yaml` — capture runs silently from here.
- **Work normally.** Commits, checkouts, merges, AI sessions, and active time are captured
  automatically to a local, append-only event log. Nothing to start, stop, or report.
- **Close a story:** `opsx archive` (or run
  `uv run tools/snapshot-assembler/main.py --repo-root .`) produces the immutable,
  versioned metrics snapshot under `snapshots/`.

Add these to your `.gitignore` (local capture state, never committed):

```
.story-events.jsonl
.story-events.pending.jsonl
.active-story
.active-claude-session
```

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
