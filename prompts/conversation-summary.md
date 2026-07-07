# Session Summary — PM Metrics as a Byproduct of AI-Accelerated Engineering

## Flow

1. **Brainstorm** (`bmad-brainstorming`, Creative Partner mode) on `docs/problem-statement.txt` — PM tracking lags AI-accelerated engineering; converged on an **A+B+C capture architecture**: story manifest + git hooks + Claude Code hook/agent self-narration, feeding a leadership dashboard without developer double-entry.
   - Output: `_bmad-output/brainstorming/brainstorm-pm-metrics-ai-engineering-flow-2026-07-01/` (`brainstorm.html`, `brainstorm-intent.md`)

2. **Architecture** (`bmad-architecture`, Coaching path) turned the intent into a formal spine: event-sourced pipes-and-filters paradigm, 8+ invariants (AD-1 through AD-8) covering event integrity, the snapshot contract, source-of-truth adapters, story identity, two-phase story-point rules, time attribution, and git-versioned hook install. Reviewed by 3 parallel reviewer passes (rubric, currency, adversarial) and hardened.
   - Output: `_bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/` (`ARCHITECTURE-SPINE.md`, `architecture-walkthrough.html` + `-light.html` presentation decks)

3. **Spec** (`bmad-spec`) distilled the spine + intent doc into the canonical machine contract: 6 capabilities (CAP-1–6), 5 constraints, 3 non-goals, a concrete success signal.
   - Output: `_bmad-output/specs/spec-pm-metrics-ai-engineering-flow/SPEC.md` (adopts `ARCHITECTURE-SPINE.md` as companion)

4. **Epics & Stories** (`bmad-create-epics-and-stories`, **paused by user request**) — extracted FR1–FR6 (from CAP-1–6), NFR1–NFR5 (from Constraints), and 9 additional architecture requirements (from AD-1–AD-8) into a proposed 5-epic split. User chose to hold off confirming this until after the leadership discussion ("let's wait").
   - Output: `_bmad-output/planning-artifacts/epics.md`

5. **Presentation polish + leadership prep** — reworked both `architecture-walkthrough.html` (dark) and `-light.html`: clearer title, per-slide plain-language "Takeaway" footers, a simple 6-step flow strip on the title slide, plainer wording for AD-1 ("one writer per line, every time"), worked examples added for the adapter pattern, time-on-task, and git-versioned hooks, and a new "Delivering to Developers" slide (repo starter kit → scaffolding CLI → VS Code extension, in that order).
   - Created `APPROACH.md` — a one-page leadership-ready summary (problem, chosen approach, deferred items, delivery path), then added two more sections after discussing risk with the user:
     - **"How This Data Will and Won't Be Used"** (proposed, needs leadership sign-off) — used for project/portfolio visibility only, explicitly not for individual performance judgment, early numbers flagged as unvalidated, developers to be told upfront.
     - **"Known Risks"** — metric-gaming (people optimizing the number instead of the work — deliberately described without the term "Goodhart's Law" per user preference), silent data loss from unmonitored hook failures, over-trusting unvalidated story-point weights, a soft loophole in the complexity gate, coverage gaps outside git/Claude Code/openspec, and adoption/surveillance-perception risk.
   - Both new sections were iterated twice: first to plain-language paragraphs, then converted to bulleted lists with key phrases bolded, per user request.
   - User's plan: bring `APPROACH.md` (as the leave-behind doc) + the HTML deck (for live walkthrough) to leadership, then resume `bmad-create-epics-and-stories` afterward.
   - Output: `_bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/APPROACH.md`

6. **Developer Experience Flow diagram** — added a plain-language "confirm at start, work normally, close at end" line diagram to both `APPROACH.md` (ASCII, new section right after "Chosen Approach") and as a standalone self-contained artifact `developer-flow.html` (theme-aware, drop-in for a slide/email, separate from the full walkthrough deck).

7. **Answered own review questions from earlier (risk pass) — real decisions, not just discussion:**
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
- AI-tool coverage beyond Claude Code (Copilot/Cursor/Codex) — real named gap; whether kickoff should ask which tool is unresolved.
- Multi-repo scaling / schema-versioning ownership — deliberately deferred until after the pilot.
- `epics.md` requirements extraction — **on hold**, awaiting user confirmation → Step 2 (epic design) of `bmad-create-epics-and-stories`, to resume after the leadership conversation.
- Leadership sign-off on the "How This Data Will and Won't Be Used" policy in `APPROACH.md` — currently proposed, not yet ratified.

## Where we left off

User is taking `APPROACH.md` + the HTML walkthrough decks to a leadership discussion. Next session should pick up with: (1) how that discussion went / any feedback or new constraints from leadership, then (2) resuming `bmad-create-epics-and-stories` Step 2 if the approach is confirmed.
