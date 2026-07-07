# Brainstorm Intent: PM Metrics as a Byproduct of AI-Accelerated Engineering Flow

## Problem Statement

PM activity (tracking, estimation, velocity) lags behind AI-accelerated engineering activity: developers using AI/SDD tooling move faster and less predictably than manual PM tracking can follow, and double-entry (developers re-reporting status/effort) is undesirable. The goal is to capture PM metrics, engineering metrics, and cost data automatically as a byproduct of the existing dev flow rather than through manual tracking or added developer overhead.

## Chosen Approach: A + B + C Capture Architecture

- **A — Story manifest**: a `.story.yaml` file created at story kickoff, carrying PM metadata, read by downstream events/tools throughout the story lifecycle.
- **B — Git hooks**: silently extract PM signals from branch names, commit messages, and PR timestamps, with zero developer prompts.
- **C — Agent self-narration**: the AI/SDD agent emits structured status events (design/coding/testing/done) as it works, acting as a PM proxy.

Since there is no plugin/extension access into the openspec/speckit tooling itself, this is realized without modifying its internals via three constraint-survival mechanisms:
1. **CLI wrapping** — wrap the openspec/speckit CLI invocation to intercept calls.
2. **Custom skill** — a skill that captures the human-provided inputs (developer-facing prompts baked into the skill).
3. **Claude Code hooks** — hook into tool-use/stop events to capture in-session signals without touching openspec/speckit source.

## Lifecycle

1. **Complexity gate** at story kickoff: an LLM classifies story complexity using project-defined rules, plus a ~30% manual-activity buffer accounting for code review, unit testing, and local feature testing. This gate decides whether the full capture pipeline runs (heavy flow for complex stories; skipped/lightweight for small, low-complexity tasks).
2. **Kickoff bookend**: captures goal and sprint context at story start.
3. **Silent A+B+C capture**: runs through the story's engineering phases.
4. **Close/archive trigger**: the openspec/speckit close/archive command (e.g., `opsx archive`) is the moment all metric families are calculated and snapshotted.
5. **Rollup**: snapshots roll up per developer and per project overall.

## Metrics Model

Four metric families, captured per story and rolled up per developer and per project:
1. **PM metrics**
2. **Engineering metrics**
3. **Story-point cost**
4. **Token cost**

**Derived trend metric**: token-cost-per-story-point over time — surfaced on the leadership dashboard to show whether AI investment is improving delivery efficiency.

## Open Questions / Deferred

- **Automatic story-point estimation**: story points should be auto-calculated via defined rules (since code is now LLM-generated, manual entry is no longer meaningful), but the rules themselves are still to be defined.
- **Developer time-on-task attribution**: developers multi-task and multi-prompt across stories concurrently, making it hard to isolate time spent per story. Current working assumption: a developer focuses on one single story at a time. The general multi-tasking case remains unresolved.
