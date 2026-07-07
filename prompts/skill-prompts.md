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
(In progress — Step 1 requirements extraction done, awaiting confirmation to proceed to Step 2: epic design.)
