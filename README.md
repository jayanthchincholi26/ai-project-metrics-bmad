# AI Project Metrics

Capturing project-management, engineering, cost, and AI-token metrics automatically as a byproduct of an AI-accelerated engineering flow (openspec/speckit) — no manual double-entry, rolled up into a leadership dashboard.

## The problem

AI-accelerated engineering now moves faster and less predictably than manual project-management tracking can follow. Developers end up manually re-entering what already happened — points, time, review cycles — duplicating work the tools already know. This project designs a way to capture that data as a natural side effect of how developers already work.

## Start here

- **Adopting this tool in your own project?** See **[tools/build-release/INSTALL.md](tools/build-release/INSTALL.md)** — install steps, daily-use flow per source-of-truth backend, the one-click team dashboard, known limitations, and data-use policy. This is the real entry point for using the tool.
- **[APPROACH.md](_bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/APPROACH.md)** — the original one-page pitch: the problem, the chosen approach, data-usage policy, known risks, and the delivery path. Written during planning; still a good leadership-facing summary of the *why*, though the *what's built* has moved past it — see Status below for current state.
- **[developer-flow.html](_bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/developer-flow.html)** — a small standalone visual of what a developer actually experiences.
- **[architecture-walkthrough.html](_bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/architecture-walkthrough.html)** (or the [light theme](_bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/architecture-walkthrough-light.html)) — an interactive, click-through deck for live walkthroughs.

## Repository layout

```
tools/                               The shipped product — every capture producer + CLI tool
  hooks/                             Git hooks + Claude Code hooks (the event producers)
  adapters/                          JIRA / Confluence / docs-only source-of-truth adapters
  snapshot-assembler/                The pipeline's only reducer (event log -> versioned snapshot)
  estimate-phase1/                   AD-6 Phase-1 story-point estimator
  opsx-wrapper/                      openspec/speckit CLI wrapper
  metrics-report/, dashboard/        Human-readable report + leadership HTML dashboard generators
  setup-hooks.py                     One-time per-repo hook installer
  build-release/                     Packages tools/ + the story-kickoff skill into a distributable
                                      zip (INSTALL.md, install.sh/.ps1, uninstall.sh/.ps1 live here)
tests/                               Mirrors tools/ 1:1 (pytest, stdlib-only mocking)
.claude/skills/story-kickoff/        The kickoff skill a developer invokes at story start
.github/workflows/                   ci.yml (lint+test), release.yml (tag -> built zip + GH release),
                                      publish-pypi.yml
docs/                                Bug tracking conventions, flow diagrams, smoke-test checklists
_bmad-output/
  planning-artifacts/
    architecture/                    Architecture spine (AD-1..AD-10), presentation decks, APPROACH.md
    epics.md                        Authoritative epic/story record — every story's actual status,
                                      updated as work lands. Source of truth for "what's built."
  implementation-artifacts/          One file per story (full dev context) + sprint-status.yaml
  specs/                            Canonical machine-readable spec (capabilities/constraints)
prompts/                            Session summaries + reusable BMad skill-invocation prompts
project-context.md                  Engineering standards: branching, PR/review, testing, DoD
```

## Approach in one line

Git hooks, Claude Code hooks, and an openspec/speckit CLI wrapper each append events to a local, append-only log. At story close, those events are reduced into one immutable, versioned snapshot — the only thing that ever leaves the developer's machine — which rolls up into PM, engineering, real cost/token, and defect metrics per story, developer, and project.

## Status

All 5 planned epics are built and merged to `main` (the project's only trunk since 2026-07-15 —
see `project-context.md` §10): docs-only/JIRA/Confluence kickoff with real MCP-based auto-fill,
silent git + AI-session capture, idle-aware active-time tracking, a one-command installer and
release-artifact distribution, and real cost/token/defect metrics rolling up into a shareable HTML
dashboard — including a one-click GitHub Actions version (Story 5.9) needing no local install.
`_bmad-output/planning-artifacts/epics.md` is the authoritative, continuously-updated record of
exactly what's done, in review, or still open — check there for current state, not this file.

## Generated with BMad

This project's planning artifacts were produced using the [BMad](https://github.com/bmad-code-org/BMAD-METHOD) skill chain: `bmad-brainstorming` → `bmad-architecture` → `bmad-spec` → `bmad-create-epics-and-stories`. The literal prompts used for each stage are preserved in [prompts/skill-prompts.md](prompts/skill-prompts.md) for reuse or continuation.
