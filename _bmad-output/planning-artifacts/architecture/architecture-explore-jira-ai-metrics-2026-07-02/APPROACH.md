# Approach: PM Metrics as a Byproduct of the AI-Accelerated Engineering Flow

## Problem

AI-accelerated engineering (openspec/speckit, SDD-driven development) now moves faster and less predictably than manual project-management tracking can follow. Developers are asked to manually re-enter what already happened — points, time, review cycles — duplicating work the tools already know. Leadership needs reliable per-story, per-developer, and per-project PM/engineering/cost/token metrics without adding developer overhead.

## How This Data Will and Won't Be Used (proposed — needs leadership sign-off)

This system captures some sensitive-feeling signals — active time, AI token cost, review rounds. That's not a problem on its own, but it can become one if we're not upfront about what it's for. A few ground rules, to confirm with leadership and share with developers before wide rollout:

- **Used for billing justification and process improvement** — sprint trends, estimate accuracy over time, and whether the AI tooling is paying off in cost terms. Confirmed as the two sanctioned uses; not staffing decisions, not individual judgment.
- **Not used to compare or evaluate individual developers.** Signals like "time on task" or "review cycles" reflect how complicated a story turned out to be, not how good or fast a person is. They should never show up in a performance conversation.
- **Metrics should never become targets.** The moment someone feels a number is judging them personally, they'll start managing the number instead of doing the work — and the number stops meaning anything.
- **Early numbers come with a trust caveat.** The story-point weights we're starting with are a **best guess**, not validated against real data. Dashboards should say so plainly, and trend lines are expected to shift once we've calibrated against real usage.
- **Developers should be told upfront**, before it starts running on their machine — not discovered after the fact. How this gets introduced matters as much as how well it's built.

## Chosen Approach

**Event-sourced, local-first capture.** Three independent sources only ever *append* events — nothing writes shared state directly:

- **Git hooks** (`post-commit`, `post-checkout`, `post-merge`, `commit-msg`) capture commit cadence and branch activity.
- **Claude Code hooks** (`SessionStart`, `SessionEnd`, `PreToolUse`, `PostToolUse`, `Stop`, `UserPromptSubmit`) capture AI-session activity, token usage, and phase narration.
- **A CLI wrapper** around openspec/speckit captures lifecycle events (e.g. `opsx archive`) without modifying its internals.

All three append to a local `.story-events.jsonl` (namespaced event types: `git.*`, `claude.*`, `opsx.*`; early events buffered, never dropped). At story close, a **snapshot assembler** reduces the log into one immutable, versioned snapshot — the *only* thing that ever crosses the boundary to a future central presentation layer. The raw event log never leaves the developer's machine.

**Story identity** lives solely in `.story.yaml`, written once at kickoff by a **source-of-truth adapter** (JIRA / Confluence / docs-only — declared once per project, never re-asked per story).

**Story points are two-phase and rule-driven**, not manually entered: a Phase-1 estimate at kickoff (from openspec task count, requirement volatility, and pattern-novelty), reconciled against a Phase-2 actual at close (from review cycles, decision points, and testing complexity). The variance is logged, never silently overwritten.

**Time-on-task** is tracked via an explicit `.active-story` pointer, auto-updated on `git checkout` and Claude Code `SessionStart` — not a manual timer — relying on a confirmed branch-per-story team convention.

**Hook installation is git-versioned**: a single committed setup script (`tools/setup-hooks`) installs everything, so no developer machine silently drifts out of sync.

**A failed hook never fails silently**: if a hook can't append an event, it retries up to 3 times, then shows the developer a visible error — closing the "quiet data loss" gap rather than leaving it as an open risk.

## Developer Experience Flow

What a developer actually sees is much simpler than the architecture behind it — confirm at the start, work normally, close at the end:

```
 Developer                                                        Leadership
 ─────────                                                        ──────────

 [1] Start a story
      |  kickoff skill confirms
      |  points + goal/sprint
      |  (auto-filled if JIRA/Confluence)
      v
 [2] Code normally with AI
      |  (git commits, Claude Code sessions -
      |   nothing extra to do or type)
      |  ................................
      |  (silent capture happens here,        <- invisible to developer
      |   background hooks only)
      v
 [3] Close the story
      |  opsx archive
      |  + a one-line "actual vs blockers" note
      v
 [4] Snapshot created automatically  ------------------------->  [5] Dashboard updates
                                                                     (velocity, cost,
                                                                      token trends)
```

## What's Deliberately Deferred

- The central presentation layer's technology, hosting, and topology — only its input contract (the versioned snapshot) is fixed.
- Story-point weight calibration — the current tables are a confirmed best guess, not yet validated against real usage data.
- Acting on estimate-vs-actual variance (a recalibration feedback loop) — captured today, not yet used.
- A manual-override path if branch-per-story is ever violated.
- Adapter credential provisioning mechanics.
- Support for AI tools other than Claude Code (Copilot, Cursor, Codex, etc.) — a real, named coverage gap, not yet designed.
- Multi-repo scaling and schema-versioning ownership — deliberately pushed past the pilot stage.

## Known Risks

- **Behavior over technology.** The biggest risk here isn't technical. Once people know a number like token cost or review-cycle count is being tracked, some will start **optimizing for the number** instead of just doing good work. The usage policy above is meant to head this off, but only if we actually stick to it.
- ~~**Quiet data loss.**~~ **Resolved:** a failed hook now retries 3 times and then surfaces a visible error, so a failure is never silent.
- **Numbers trusted too early.** The story-point weights we're using are a best guess, not calibrated against real data — an early dashboard could give people **more confidence than the numbers deserve**.
- **A soft loophole in the complexity gate.** Since small or low-complexity stories skip the full tracking pipeline, there's a mild incentive to **under-classify** a story just to avoid the extra overhead.
- **Coverage gaps — still open.** Anything that happens outside git, Claude Code, and openspec/speckit simply **won't show up**. This is a real, named gap: developers on GitHub Copilot, Cursor, Codex, or other AI tools produce no capturable signal today. A likely fix is having the kickoff flow ask which tool a developer is using, but that's not designed yet.
- **Adoption risk.** Automatically capturing active time and AI usage can feel like **surveillance** if it isn't introduced carefully, with a clear explanation of what it is and isn't used for. How well this lands with the team depends as much on that conversation as on how well it's built.

## Delivery Path

Ship in sequence, not in parallel — each step is a strict upgrade of the last, and the architecture doesn't change based on which step you're on:

1. **Repo starter kit** (buildable today) — hooks, setup script, and kickoff/close skills live in the project repo; a developer clones and runs `tools/setup-hooks` once.
2. **Scaffolding CLI / template repo** — reusable across many projects once Step 1 is proven and worth automating.
3. **VS Code extension** — a polished UI layer (status-bar timer, native kickoff prompt) on the same underlying files, built once adoption is wide enough to justify it.

**Rollout plan:** run Step 1 as a **pilot with a small group of developers first**. Use real pilot data — not guesswork — to tweak the story-point formula (the current weights are a best-guess starting point, consistent with the common practice of estimating from a reference document). Only after the pilot proves out should scaling to more repos, or the harder multi-repo/schema-versioning ownership questions, be tackled.

## Full Reference

- Architecture spine (all AD invariants): `ARCHITECTURE-SPINE.md` (this folder)
- Canonical spec (capabilities/constraints): `_bmad-output/specs/spec-pm-metrics-ai-engineering-flow/SPEC.md`
- Epic/story breakdown: `_bmad-output/planning-artifacts/epics.md`
- Presentation decks: `architecture-walkthrough.html` / `architecture-walkthrough-light.html` (this folder)
