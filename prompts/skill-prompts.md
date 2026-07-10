# Skill Invocation Prompts

The literal prompts/args used to invoke each BMad skill in this session, in order. Re-running a skill with the same args on the same output folders will resume/update in place (memlog-driven), not start over.

## 1. `/bmad-brainstorming`

```
problem-statement.txt
```
(Resolved to `docs/problem-statement.txt`. Stance chosen interactively: Creative Partner. Technique batch chosen: How Might We → Job to Be Done → Role Playing → Constraint Roulette, then Affinity Clustering to converge.)

## 2. `bmad-architecture`

```
create architecture for the AI-accelerated engineering metrics capture pipeline, based on the brainstorm intent doc at _bmad-output/brainstorming/brainstorm-pm-metrics-ai-engineering-flow-2026-07-01/brainstorm-intent.md and the synthesized pipeline (complexity gate -> kickoff bookend -> silent capture via story manifest + git hooks + Claude Code hooks -> close/archive trigger -> 4-family metrics snapshot -> rollup per developer/project, plus token-cost-per-point trend)
```
(Working mode chosen interactively: Coaching path. Purpose: alignment doc + spine.)

## 3. `bmad-spec`

```
adopt/create a spec from the finalized architecture spine at _bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md and its memlog, plus the brainstorm intent doc at _bmad-output/brainstorming/brainstorm-pm-metrics-ai-engineering-flow-2026-07-01/brainstorm-intent.md, keeping AD IDs stable
```

## 4. `bmad-create-epics-and-stories`

```
break down the SPEC at _bmad-output/specs/spec-pm-metrics-ai-engineering-flow/SPEC.md (companion: ARCHITECTURE-SPINE.md at _bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md) into epics and stories, citing CAP-N and AD-N ids
```
(Completed — 3 epics / 14 stories, `_bmad-output/planning-artifacts/epics.md`.)

## 5. `bmad-check-implementation-readiness`

Run with no extra args (validates SPEC.md + ARCHITECTURE-SPINE.md + epics.md together). Found and the user fixed 1 high-priority gap (missing `ai_tool` manifest field/story) + 3 minor AC/sequencing issues. Output: `_bmad-output/planning-artifacts/implementation-readiness-report-2026-07-09.md`, final status READY.

## 6. `bmad-sprint-planning`

Run with no extra args once ready. Produced `_bmad-output/implementation-artifacts/sprint-status.yaml` (epic/story status tracking) — the input every later `bmad-create-story`/`bmad-dev-story`/`bmad-sprint-status` call auto-discovers from.

## 7. `bmad-sprint-status`

Run with no args at any point to get a status summary + next-recommendation. Used repeatedly across the implementation phase to pick up the next story.

## 8. `bmad-create-story` (× 14, one per story)

Invoked either with no args (auto-discovers the first `backlog` story from `sprint-status.yaml`) or with an explicit epic-story key, e.g.:

```
create story 3.1
create story 3.2
create story 3.3
```

Each run reads `epics.md`'s AC for that story, the previous story in the same epic (if any) for cross-story intelligence, and `project-context.md`, then writes a comprehensive story file to `_bmad-output/implementation-artifacts/{epic}-{story}-{slug}.md` and flips its `sprint-status.yaml` entry to `ready-for-dev`.

## 9. `bmad-dev-story` (× 14, one per story)

Invoked with no args after each `create-story` (auto-discovers the first `ready-for-dev` story):

```
dev-story
```

Follows RED (failing test first) → GREEN (minimal implementation) → full regression → live E2E in a real temp git repo/real hook invocation via `uv run --script` (this repeatedly caught defects mocked unit tests alone missed — see `prompts/conversation-summary.md`'s epic retros) → story status `review` → commit/push/PR (no pause for go-ahead — see project-context.md §8/§9/§10 for the branch/PR/review conventions this follows). After the user pastes back Gemini's PR review and confirms the merge, the story (and epic, if it was the last one) gets closed out: status → `done`, `epics.md` annotated with the PR link, `develop` synced.
