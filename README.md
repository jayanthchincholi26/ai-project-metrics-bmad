# AI Project Metrics

Capturing project-management, engineering, cost, and AI-token metrics automatically as a byproduct of an AI-accelerated engineering flow (openspec/speckit) — no manual double-entry, rolled up into a leadership dashboard.

## The problem

AI-accelerated engineering now moves faster and less predictably than manual project-management tracking can follow. Developers end up manually re-entering what already happened — points, time, review cycles — duplicating work the tools already know. This project designs a way to capture that data as a natural side effect of how developers already work.

## Start here

- **[APPROACH.md](_bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/APPROACH.md)** — one-page summary: the problem, the chosen approach, data-usage policy, known risks, and the delivery path. The best starting point for a leadership or team review.
- **[developer-flow.html](_bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/developer-flow.html)** — a small standalone visual of what a developer actually experiences.
- **[architecture-walkthrough.html](_bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/architecture-walkthrough.html)** (or the [light theme](_bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/architecture-walkthrough-light.html)) — an interactive, click-through deck for live walkthroughs.

## Repository layout

```
docs/problem-statement.txt          Original problem statement that kicked this off
_bmad-output/
  brainstorming/                    Divergent ideation session and its synthesized intent
  planning-artifacts/
    architecture/                   Architecture spine (AD-1..AD-9), presentation decks, APPROACH.md
    epics.md                        Draft epic/story breakdown (in progress)
  specs/                            Canonical machine-readable spec (capabilities/constraints)
prompts/                            Session summary + reusable BMad skill-invocation prompts
```

## Approach in one line

Git hooks, Claude Code hooks, and an openspec/speckit CLI wrapper each append events to a local, append-only log. At story close, those events are reduced into one immutable, versioned snapshot — the only thing that ever leaves the developer's machine — which rolls up into PM, engineering, cost, and token-cost metrics per story, developer, and project.

## Status

Architecture and spec are finalized and reviewed. Epic/story breakdown is drafted and paused pending a leadership review of the approach. See `prompts/conversation-summary.md` for the full session history and current open items.

## Generated with BMad

This project's planning artifacts were produced using the [BMad](https://github.com/bmad-code-org/BMAD-METHOD) skill chain: `bmad-brainstorming` → `bmad-architecture` → `bmad-spec` → `bmad-create-epics-and-stories`. The literal prompts used for each stage are preserved in [prompts/skill-prompts.md](prompts/skill-prompts.md) for reuse or continuation.
