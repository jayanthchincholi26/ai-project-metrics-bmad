# Session Summary — PM Metrics as a Byproduct of AI-Accelerated Engineering

## Flow

1. **Brainstorm** (`bmad-brainstorming`, Creative Partner mode) on `docs/problem-statement.txt` — PM tracking lags AI-accelerated engineering; converged on an **A+B+C capture architecture**: story manifest + git hooks + Claude Code hook/agent self-narration, feeding a leadership dashboard without developer double-entry.
   - Output: `_bmad-output/brainstorming/brainstorm-pm-metrics-ai-engineering-flow-2026-07-01/` (`brainstorm.html`, `brainstorm-intent.md`)

2. **Architecture** (`bmad-architecture`, Coaching path) turned the intent into a formal spine: event-sourced pipes-and-filters paradigm, 8+ invariants (AD-1 through AD-8) covering event integrity, the snapshot contract, source-of-truth adapters, story identity, two-phase story-point rules, time attribution, and git-versioned hook install. Reviewed by 3 parallel reviewer passes (rubric, currency, adversarial) and hardened.
   - Output: `_bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/` (`ARCHITECTURE-SPINE.md`, `architecture-walkthrough.html` + `-light.html` presentation decks)

3. **Spec** (`bmad-spec`) distilled the spine + intent doc into the canonical machine contract: 6 capabilities (CAP-1–6), 5 constraints, 3 non-goals, a concrete success signal.
   - Output: `_bmad-output/specs/spec-pm-metrics-ai-engineering-flow/SPEC.md` (adopts `ARCHITECTURE-SPINE.md` as companion)

4. **Epics & Stories** (`bmad-create-epics-and-stories`, **complete**) — resumed after the leadership discussion. Redesigned the initial 5-epic technical-layer draft into a proper user-value-first **3-epic structure**: Epic 1 (Start a Story With Zero Manual PM Setup, 5 stories after fixes), Epic 2 (Metrics Appear Automatically When You Close a Story, 6 stories — the core capture/snapshot/points loop), Epic 3 (Time Tracked Without Logging Hours, 3 stories). 14 stories total, all FR1–FR7/NFR1–5/AD-1–10 traced and validated (no forward dependencies, no epic independence violations).
   - Output: `_bmad-output/planning-artifacts/epics.md`

5. **Implementation Readiness Check** (`bmad-check-implementation-readiness`, **complete**) — validated SPEC.md (as PRD-equivalent), ARCHITECTURE-SPINE.md, and epics.md together. Found 1 high-priority gap (Story 2.3 assumed an `ai_tool` manifest field that no story actually created) and 3 minor AC/sequencing concerns. All 4 were fixed immediately: added **Story 1.5** (kickoff declares `ai_tool`, mirroring Story 1.2's `source_of_truth` pattern), tightened Story 1.1's missing-input path and Story 3.2's idle-timeout precision. Final status: **READY** for `bmad-sprint-planning`.
   - Output: `_bmad-output/planning-artifacts/implementation-readiness-report-2026-07-09.md`

6. **Presentation polish + leadership prep** — reworked both `architecture-walkthrough.html` (dark) and `-light.html`: clearer title, per-slide plain-language "Takeaway" footers, a simple 6-step flow strip on the title slide, plainer wording for AD-1 ("one writer per line, every time"), worked examples added for the adapter pattern, time-on-task, and git-versioned hooks, and a new "Delivering to Developers" slide (repo starter kit → scaffolding CLI → VS Code extension, in that order).
   - Created `APPROACH.md` — a one-page leadership-ready summary (problem, chosen approach, deferred items, delivery path), then added two more sections after discussing risk with the user:
     - **"How This Data Will and Won't Be Used"** (proposed, needs leadership sign-off) — used for project/portfolio visibility only, explicitly not for individual performance judgment, early numbers flagged as unvalidated, developers to be told upfront.
     - **"Known Risks"** — metric-gaming (people optimizing the number instead of the work — deliberately described without the term "Goodhart's Law" per user preference), silent data loss from unmonitored hook failures, over-trusting unvalidated story-point weights, a soft loophole in the complexity gate, coverage gaps outside git/Claude Code/openspec, and adoption/surveillance-perception risk.
   - Both new sections were iterated twice: first to plain-language paragraphs, then converted to bulleted lists with key phrases bolded, per user request.
   - User's plan: bring `APPROACH.md` (as the leave-behind doc) + the HTML deck (for live walkthrough) to leadership, then resume `bmad-create-epics-and-stories` afterward.
   - Output: `_bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/APPROACH.md`

7. **Developer Experience Flow diagram** — added a plain-language "confirm at start, work normally, close at end" line diagram to both `APPROACH.md` (ASCII, new section right after "Chosen Approach") and as a standalone self-contained artifact `developer-flow.html` (theme-aware, drop-in for a slide/email, separate from the full walkthrough deck).

8. **Answered own review questions from earlier (risk pass) — real decisions, not just discussion:**
   - **Data use scope confirmed:** billing justification and process improvement only — not staffing or individual performance review. Updated in `APPROACH.md`'s usage-policy section and `SPEC.md`'s Assumptions.
   - **Hook-failure handling decided → new invariant AD-9** in `ARCHITECTURE-SPINE.md`: a failed hook retries up to 3 times, then surfaces a visible error to the developer — never fails silently. This *resolves* the previously-open "quiet data loss" risk (marked resolved in `APPROACH.md`'s Known Risks). Also added to `SPEC.md` Constraints.
   - **Story-point formula validation plan:** pilot with a small group of developers first; tweak the AD-6 weights from real pilot data rather than guessing further. Consistent with the user's note that most orgs estimate off a reference document as a starting point. Added to `APPROACH.md` Delivery Path as a new "Rollout plan" and to the architecture/spec memlogs as a `direction` entry.
   - **New real coverage gap surfaced:** this architecture only captures Claude Code as the AI tool — developers on GitHub Copilot, Cursor, Codex, etc. produce no capturable signal today. Whether the kickoff flow should ask which AI tool a developer is using (to route to tool-specific capture adapters later) is now an explicit open question — added to `ARCHITECTURE-SPINE.md` Deferred, `SPEC.md` Non-goals/Open Questions, and `APPROACH.md`'s Coverage Gaps risk bullet (no longer glossed over).
   - **"20 repos" clarified:** was about future multi-repo/schema-versioning ownership if the pilot succeeds and scales — not an immediate concern. User's answer (solve it after the pilot, not before) was accepted as the right sequencing; added to Deferred in both the spine and `APPROACH.md`.
   - `ARCHITECTURE-SPINE.md` was re-linted clean after these amendments.

## Key decisions locked in

- **Event-sourced, local-first capture**: git hooks, Claude Code hooks, and a CLI wrapper each append events to a local `.story-events.jsonl`; nothing writes shared state directly; works fully offline.
- **Snapshot is the only contract** crossing to a (deliberately deferred) central presentation layer — raw events never leave the developer's machine; every close produces a new immutable revision.
- **Source-of-truth adapter pattern**: JIRA / Confluence / docs-only, declared once per project, normalized to one shape.
- **Story identity** lives solely in `.story.yaml`, never inferred from branch/ticket naming.
- **Two-phase story points** (AD-6): Phase-1 estimate from openspec task-count + volatility + novelty modifier; Phase-2 actual from review cycles + decision points + testing weight + context management; variance logged, never overwritten. Confirmed: the underlying weight tables are an unvalidated best guess (from an internal reference doc), and the variance feedback loop (acting on it) is explicitly deferred.
- **Time-on-task**: an explicit `.active-story` pointer, auto-updated on `git checkout` / Claude Code `SessionStart`; branch-per-story is a confirmed team convention with no override path yet.
- **Hook installation is git-versioned** (`tools/setup-hooks`), not per-machine.
- **Hook failures retry then surface (AD-9)**: 3 retries, then a visible error to the developer — never silent.
- **Sanctioned data use**: billing justification and process improvement only — not staffing or individual performance review.
- **AI-tool capture adapter (AD-10)**: resolves the multi-AI-tool coverage gap by mirroring the source-of-truth adapter (AD-4). One normalized "AI activity" shape (session start/end, activity count, token cost) behind a per-tool adapter; event namespace generalized from `claude.*` to `ai.<tool>.*` (amends AD-1a); kickoff manifest gains an `ai_tool` field; a signal a tool can't report (e.g. Copilot's lack of per-token cost) is null-with-reason, never zero; AD-6 Phase-2 reconciliation marks a story reduced-confidence when the tool can't supply decision-narration/token-cost signals. Only the Claude Code adapter is built — Cursor/Copilot/Gemini adapters are deliberately out of scope for the pilot, but the plug-in boundary now exists. Added as `SPEC.md` CAP-7.

## Delivery path discussed (not yet built)

1. Repo-embedded starter kit (buildable today — hooks + setup script + skills live in-repo).
2. Scaffolding CLI / template repo (reusable across many projects).
3. VS Code extension (nicer UX layer on the same substrate, built last).
Recommendation: ship strictly in that order, only building the next step once the previous one's limits actually hurt.

## Open items carried forward

- Central-service/BI-tool technology choice (no urgency confirmed).
- Adapter credential provisioning mechanics.
- Story-point weight recalibration process — pilot-first plan agreed, but the actual feedback loop (acting on variance) is still undesigned.
- Manual-override path if branch-per-story is ever violated.
- Non-Claude-Code AI-tool adapters (Cursor/Copilot/Gemini) — boundary designed (AD-10), implementations not built; deliberately out of scope for the pilot.
- Multi-repo scaling / schema-versioning ownership — deliberately deferred until after the pilot.
- A fourth source-of-truth adapter (GitLab) — held for later per user; JIRA/Confluence/docs-only remain the only designed adapters (AD-4).
- Leadership sign-off on the "How This Data Will and Won't Be Used" policy in `APPROACH.md` — currently proposed, not yet ratified.

## Clarified: BMad vs. openspec/opsx, and where the tool actually runs

User asked two clarifying questions after the readiness check; answered and worth remembering exactly because it's a subtle distinction:

1. **Implementation framework = BMad, not opsx.** `bmad-sprint-planning` → `bmad-create-story` → `bmad-dev-story` is the right continuation, since `epics.md` was already produced in BMad's own Epic/Story/Given-When-Then format — switching to openspec/opsx now would mean redundantly re-deriving everything into `proposal.md`/`specs/`/`tasks.md`. **Critical distinction:** openspec/speckit (`opsx`) is not a competing build framework for this tool — it's the *target workflow the finished tool observes* (via the CLI wrapper intercepting other developers' `opsx archive` calls, reading their `tasks.md`, etc.) once deployed into someone else's project. BMad and opsx play two entirely different roles: BMad builds this tool; opsx is what this tool watches, in the wild.
2. **Where it runs once built:** this repo (`ai-project-metrics-bmad`) is the design/planning repo only — it never runs the tool. Per the Delivery Path, the runtime pieces (`tools/hooks/`, `tools/setup-hooks`, `.claude/skills/story-kickoff`, etc.) get built here via `bmad-dev-story`, then copied/adopted into whichever *other* target project uses this pipeline. Execution there is editor-agnostic by design — git hooks fire regardless of editor; Claude Code hooks fire wherever Claude Code runs (terminal, VS Code extension, JetBrains, etc.) — there's no hard VS Code dependency anywhere in AD-1 through AD-10.

## Tech stack pinned before sprint planning

User asked what tech stack/project stance was decided and which BMad skill owns it (answer: `bmad-architecture`, the Stack + Design Paradigm sections of `ARCHITECTURE-SPINE.md`). Found a real gap: the Stack table named mechanisms (git hooks, Claude Code hook config, CLI-wrapping) but never pinned an implementation language. Resolved via `AskUserQuestion` (Python+uv vs Node.js vs Bash-only) — **Python 3.8+ via `uv run`** chosen, ratifying the existing `_bmad/scripts/*.py` convention already used in this repo. Git-invoked hooks are thin shell/batch shims calling the Python scripts via `uv run` (git needs a directly executable file). Updated `ARCHITECTURE-SPINE.md` Stack table + Structural Seed tree (file extensions added) and `epics.md` Additional Requirements. Spine re-linted clean; `updated` date bumped to 2026-07-09.

## Engineering standards established (project-context.md)

User asked for a standards document like their other project's `CLAUDE.md` (Angular/.NET), covering: language/framework, code standards, API standards, security standards, testing framework, unit testing, code review (human + LLM), Story DoD, branch/PR, PR merge, deployment, story archival, bug tracking. Key decisions:
- Content went into **`project-context.md`** (committed, tracked), not `CLAUDE.md` — because `project-context.md` is the exact filename every BMad skill in this project auto-loads as a persistent fact (`file:{project-root}/**/project-context.md`), across `bmad-sprint-planning`/`bmad-create-story`/`bmad-dev-story`. That's what makes the standards actually enforced during implementation, not just documented.
- **`CLAUDE.md` at project root is a short pointer file, and IS committed** (clarified after a mix-up: the user actually had a *different* `docs/CLAUDE.md` — their other project's reference standards doc, unrelated to this one — which they've since deleted; the root-level pointer to `project-context.md` was always meant to be committed and now is).
- Stack pick for lint/format: **ruff** (no existing config found; chosen since it's one tool for both, fits the stdlib-only minimalist ethos already established).
- Content grounded in real precedent from `_bmad/scripts/*.py` (PEP 723 headers, `from __future__ import annotations`, atomic temp+fsync+rename writes, argparse `--workspace`/`--path` addressing, single-JSON-ack stdout pattern) rather than invented conventions.
- Created a **`develop` branch** (pushed to origin) since §10 (PR Merge to develop) and §11 (Deployment) depend on it existing.
- 14 sections total: Language & Framework, Code Standards, API Standards (internal interfaces — clarified via `AskUserQuestion`, since this project has no REST API), Security, Testing Framework, Unit Testing, Code Review (Human), Feature Branch & PR, LLM PR Review (Mandatory), PR Merge to `develop`, Deployment, Story DoD (Mandatory), Story Archival Checklist, Bug Tracking.
- Explicit scope note in the file: governs story implementation going forward (Phase 4), not the planning-phase commits already on `main`.

## Where we left off (planning phase, 2026-07-09)

`bmad-create-epics-and-stories` and `bmad-check-implementation-readiness` are both **complete**; `epics.md` is at overall status **READY**. Next natural step in the BMad flow: `bmad-sprint-planning` (required gate into Phase 4/Implementation), followed by `bmad-create-story` and `bmad-dev-story` for actual implementation, run in *this* repo — the resulting tool is then adopted into other target projects per the Delivery Path. No pending user decisions block moving forward — this is a good point to either continue into sprint planning or pause.

---

## Phase 4: Implementation — all 3 epics complete (2026-07-09 → 2026-07-10)

Ran `bmad-sprint-planning` (produced `_bmad-output/implementation-artifacts/sprint-status.yaml`), then cycled `bmad-create-story` → `bmad-dev-story` (TDD: RED failing test → GREEN minimal implementation → full regression → live E2E) → commit/push/PR → paste Gemini's review → triage → user confirms merge → close out story (and epic, when it was the last story) — for all 14 stories across Epic 1, Epic 2, and Epic 3. Every story followed the [[feedback-story-pr-flow]] convention: no manual pause before commit/push/PR.

**Epic 1 — Start a Story With Zero Manual PM Setup** (5 stories, PRs #1/#4/#6/#8/#9, complete 2026-07-09): docs-only kickoff writing `.story.yaml` (Story 1.1), project-level `source_of_truth` config (1.2), JIRA adapter (1.3), Confluence adapter (1.4), `ai_tool` manifest field (1.5, added by the readiness check). Retro: fetch-only adapters + one manifest writer kept NFR4 (no credentials in shared files) trivially provable; TDD + manual E2E caught a UTF-8 BOM bug unit tests alone missed; external LLM review converged to zero findings by 1.5 as earlier lessons got pre-applied; one hallucinated review finding (nonexistent `import math`) — first sighting of a pattern that recurred later.

**Epic 2 — Metrics Appear Automatically When You Close a Story** (6 stories, PRs #10–#15, complete 2026-07-10): hook installation via `tools/setup-hooks` (2.1), git activity capture (2.2), Claude Code session/tool/prompt capture (2.3 — introduced the shared `tools/hooks/_events.py` emitter as a spine amendment, user-approved, resolving a DRY finding from Epic 1), `opsx archive` → snapshot assembler (2.4), Phase-1 story-point estimate at kickoff (2.5), Phase-2 actual-points reconciliation against the event log (2.6). Retro: the shared-emitter spine amendment paid for itself repeatedly (reused by the opsx wrapper in 2.4, by the assembler's `git_out()` in 2.6); live E2E (real git repos, real piped stdin) caught 5 of the epic's defects that mocked unit suites missed outright, including 3 BOM-family bugs and a `git_out()` cwd-addressing bug; Story 2.5 shipped without persisting its own Phase-1 estimate, a gap only found when 2.6 needed to read it back (fixed retroactively via AD-6a) — lesson: check whether a story's own ACs satisfy every invariant *later* stories in the same epic will assume.

**Epic 3 — Time Tracked Without Logging Hours** (3 stories, PRs #16/#17/#18, complete 2026-07-10): `.active-story` pointer auto-updated on `git checkout`/Claude Code `SessionStart`, emitting `time.slice_closed`/`time.slice_opened` (3.1); idle-timeout auto-pause via `record_activity()` and `time.slice_paused`, threshold configurable via `STORY_IDLE_THRESHOLD_SECONDS` env var (3.2); mid-session checkout precedence via a second `.active-claude-session` marker, `repoint_active_story()`, and `close_active_story_slice()` finally wiring `SessionEnd` to actually close a slice — completing an AD-7 rule that had been written into the architecture before Epic 3 even started but was left half-wired by 3.1 (3.3). Retro: the shared-emitter/no-parallel-mechanism discipline from Epic 2 carried straight through — every new mechanic was a sibling function reusing `emit()`/`write_atomic_json()`/`read_active_story()`, never a new I/O path. PR #17 caught a real Critical defect (a malformed `STORY_IDLE_THRESHOLD_SECONDS` crashing module import, which would have blocked every commit) but also failed CI on `ruff format --check` even after local `ruff check` (lint) passed — format and lint are separate CI gates, both now run before every push. The Gemini reviewer produced misattributed findings on *both* PR #16 and PR #18 (content from a different story's actual diff, presented as if about the PR under review) — now a confirmed recurring pattern across 3 separate PRs, not a one-off; every finding gets grep-verified against the actual diff before being acted on or reported.

**Post-epic cleanup (2026-07-10):** two leadership-facing single-page diagrams added (`docs/architecture-diagram-leadership.html`, `docs/new-machine-onboarding.html`, linked from `APPROACH.md`); `epics.md`'s FR Coverage Map fixed (it referenced stale "Epic 4"/"Epic 5" from an early planning draft — FR2/FR3 actually landed in Epics 2/3); everything confirmed committed and pushed to `develop` with a clean working tree, ready for a fresh clone/testing session in another VS Code window.

## Where we left off (2026-07-10, end of Phase 4)

All 3 epics / 14 stories are **done** and merged to `develop`. `sprint-status.yaml` shows epic-1/epic-2/epic-3 all `done`, no backlog stories remain, both retrospectives are `optional` (not yet run — a full `bmad-retrospective` could still be requested, though every epic already got an informal retro note written directly into `epics.md` per project-context.md §13). `develop` is fully pushed and clean. No Epic 4 exists — the project's full planned scope is implemented. Next steps are user-driven: thorough testing in a fresh session/window, deciding on the Delivery Path's Step 2 (scaffolding CLI) or Step 3 (VS Code extension), or running the deferred retrospectives.
