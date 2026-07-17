---
name: story-close
description: Close/archive a story - for source_of_truth jira, transitions open defect sub-tasks and the parent ticket to Done (one confirmation gate) before running the existing close command. Use whenever the developer wants to close, finish, or archive a story, or right before running tools/opsx-wrapper/main.py archive or tools/snapshot-assembler/main.py to close one.
---

# Story Close

**Goal:** The human bookend at story end, for JIRA-backed stories. Sync the ticket's own workflow state to reality (its defect sub-tasks and the parent issue both move to Done) before the existing close command runs — without the developer needing to learn or invoke anything new (Story 6.2).

This skill activates implicitly (Claude Code matches it against relevance to this description), not via a memorized phrase — it fires whenever the developer asks to close/finish/archive a story, or right before `tools/opsx-wrapper/main.py archive <name>` or `tools/snapshot-assembler/main.py --repo-root .` is about to run for that story.

**Real limitation, not a design gap:** this can only happen during a live Claude Code chat turn. Running either close command directly in an external terminal (outside any Claude Code conversation) skips everything below entirely — there's no assistant turn to intercept it, and MCP tools are categorically unreachable outside one. Same category of platform gap as the already-documented `SessionEnd`/VS-Code-panel-"x"-button limitation.

## Flow

### 1. Resolve the source of truth and read the manifest

Run first (pass the repo root explicitly — never assume cwd), reusing the same resolver `story-kickoff` uses:

```
uv run tools/adapters/resolve.py --repo-root <repo-root>
```

Also read `.story.yaml` for `jira_issue_key` and `story_id`.

### 2. Passthrough branch — no JIRA involvement at all

If `source_of_truth` is **not** `jira`, **or** it is `jira` but `.story.yaml`'s `jira_issue_key` is null/absent (e.g. an older story, or one created before Story 5.4 added this field) — skip straight to step 6 below. No confirmation prompt, no MCP calls of any kind, byte-for-byte the same experience as before this skill existed.

### 3. JIRA-backed branch — discover what would happen (no writes yet)

1. Resolve `cloudId` — reuse one already resolved earlier in this same conversation (e.g. from a kickoff or a defect subtask creation) if available; otherwise call `getAccessibleAtlassianResources` fresh. If multiple sites come back, ask the developer which applies (same site-choice handling as `story-kickoff`'s step 4a.2.1 — not the AD-4 backend question).
2. Discover every sub-task under the parent: `searchJiraIssuesUsingJql` with `jql: "parent = <jira_issue_key>"`, requesting `status` and the points field (`.story-config.yaml`'s `jira_points_field`, default `customfield_10016`) in `fields`.
3. For each sub-task **not already in a Done-equivalent status** (see the allow-list in step 3.5 below — a sub-task already there is left alone, not re-transitioned):
   - If its points field is null, note that it needs `editJiraIssue` to set it to **1** before transitioning. **This is the primary mechanism for defect sub-tasks to carry a points value at all today** (Story 6.3, which sets it at creation time, hasn't shipped yet) — not a rarely-used safety net.
4. Resolve the parent's own available transitions: `getTransitionsForJiraIssue` with `cloudId` and the parent's issue key.
5. For both each open sub-task and the parent, match a transition name against, in order (first match wins, case-insensitive):
   1. `.story-config.yaml`'s `jira_done_transition` override, if set.
   2. The allow-list: `"Done"`, `"Closed"`, `"Resolved"`.

   (Mirrors Story 6.1's `jira_in_progress_transition` precedence exactly, just for the opposite end of the lifecycle.)
6. **Do not write anything to JIRA yet** — everything above is discovery only, feeding the confirmation in step 4.

### 4. One confirmation, framed around the parent

Ask a single `AskUserQuestion` — not one per sub-task:

> "This will close {N} sub-task(s) and transition the parent JIRA issue `{KEY}` to Done — proceed?"

- **Confirmed** → proceed to step 5.
- **Declined** → skip straight to step 6 (the existing close command still runs — declining the JIRA sync never blocks the real local close, FR5).

### 5. Apply the writes, sub-tasks first, parent last

1. For each open sub-task (in the order discovered): if it needs a points edit (step 3.3), call `editJiraIssue` first, then `transitionJiraIssue` with its matched transition id (step 3.5).
2. Only after every sub-task has been attempted, transition the parent the same way.
3. **Any individual failure (points edit, a sub-task transition, or the parent transition) is never fatal to this skill or to closing the story.** Report plainly which writes succeeded and which didn't (e.g. "closed 2 of 3 sub-tasks; AI-146 failed — <reason>; parent AI-143 → Done succeeded"), then continue unconditionally to step 6. Never re-attempt silently, never block on a retry.

### 6. Run the existing close command — always, last, unconditionally

Run whichever close command already applies to this project (already known from this conversation's own context — openspec project vs. not, exactly as a developer already knows today):

```
uv run tools/opsx-wrapper/main.py archive <change-name>
```

or, without openspec:

```
uv run tools/snapshot-assembler/main.py --repo-root <repo-root>
```

This step runs **regardless of everything above** — a JIRA-side failure, a declined confirmation, or a fully successful sync all land here the same way. A failed archive run must never be preceded by a false "Done" on the ticket, which is exactly why steps 3-5 always happen *before* this step, never after.

## Boundaries

- This skill never writes `.story.yaml`, `.story-events.jsonl`, or any spool/event file itself — those stay exactly as produced by the existing close command in step 6. This skill's only writes are the JIRA-side ones in step 5.
- Credentials: MCP-path only, same as `story-kickoff`. This skill has no fallback-script path and sees no credential of any kind — auth lives entirely in the MCP server's own OAuth session.
- Do not attempt to detect *which* close command applies (openspec vs. not) — that's already known from the live conversation, not this skill's job to figure out.
- Do not re-transition a sub-task or parent that's already in a Done-equivalent status — leave it alone, it's not this skill's job to second-guess an already-correct state.
