---
name: log-review-defect
description: Log a confirmed-real, fixed code review finding as a defect - for source_of_truth jira, also creates a real Jira Subtask under the story's parent issue with a story-points value. Use whenever a pasted code review's finding has been verified against the diff, confirmed real, and fixed. Never for a declined or stale finding.
---

# Log Review Defect

**Goal:** Turn a confirmed-real, fixed code review finding into a defect record — a side effect of the fix itself, not a separate step the developer has to remember (Story 5.4, generalized and shipped by Story 6.3).

This skill activates implicitly, the same way `story-close` does (Story 6.2) — Claude Code matches it against relevance to this description, not a memorized phrase. It fires right after a pasted review's finding has been verified against the actual diff, confirmed real, and fixed.

**Never log a declined or stale finding this way** — only a finding that was both confirmed real (against the diff) and actually fixed.

**Real limitation, not a design gap:** same as `story-kickoff`/`story-close` — this can only happen during a live Claude Code chat turn. `tools/log-defect/main.py` never calls Jira itself (MCP tools are only reachable from a live assistant turn, never a subprocess), so the Jira subtask must be created first, in the same turn, before this skill's final step runs.

## Flow

### 1. Read the manifest

Read `.story.yaml` for `source_of_truth` and `jira_issue_key`.

### 2. Create the Jira subtask (JIRA-backed stories only)

If `source_of_truth` is `jira` **and** `jira_issue_key` is non-null:

1. Resolve `cloudId` — reuse one already resolved earlier in this conversation if available, otherwise call `getAccessibleAtlassianResources` fresh.
2. Call `createJiraIssue` with `cloudId`, `projectKey` (the parent issue's project), `issueTypeName: "Subtask"`, `parent: <jira_issue_key>`, `summary`/`description` from the finding, and `additional_fields` setting the points field (`.story-config.yaml`'s `jira_points_field`, default `customfield_10016`) to **1** — this is the fix Story 6.3 adds; the original convention this skill replaces never set a points value at all.
3. Keep the resulting subtask key for step 4.

If `source_of_truth` is **not** `jira`, or it is `jira` with a null `jira_issue_key` (an older story, or one predating Story 5.4) — skip this step entirely, no Jira call of any kind.

### 3. Log the local event

Always run, regardless of step 2:

```
uv run tools/log-defect/main.py --repo-root <repo-root> --type review --summary "<finding summary>" --description "<finding description>" [--jira-subtask-key <key from step 2, if one was created>]
```

This appends the local `ai.claude-code.defect_review` event the snapshot assembler reduces into `defect_metrics` at story close. Same script, same arguments, as before this skill existed — nothing about `tools/log-defect/main.py` itself changes.

## Boundaries

- Only a finding confirmed real against the actual diff, and actually fixed, is ever logged this way — a declined or stale finding never is.
- This skill never writes `.story.yaml` or any event/spool file directly — step 3 delegates that to the existing, unmodified `tools/log-defect/main.py`.
- Credentials: MCP-path only, same as `story-kickoff`/`story-close`. No credential of any kind is ever seen by this skill.
- Compile/test defects are unaffected by this skill entirely — those stay hook-captured and local-only (Story 5.4's documented non-goal: hooks can't reach MCP).
