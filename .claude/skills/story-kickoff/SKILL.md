---
name: story-kickoff
description: Kick off a story - confirm story points, goal, and sprint, then write the .story.yaml manifest that gives every capture producer its story identity. Use when the developer says "kick off this story", "start story kickoff", or "start a new story".
---

# Story Kickoff

**Goal:** The human bookend at story start. Resolve the project's declared source of truth, confirm the PM fields with the developer, and write them into `.story.yaml` — the sole source of story identity every capture producer reads (AD-5).

## Flow

### 1. Resolve the source of truth (never ask)

Run first, before anything else (pass the repo root explicitly — never assume cwd):

```
uv run tools/adapters/resolve.py --repo-root <repo-root>
```

The project declares its PM tool **once** in `.story-config.yaml` (`source_of_truth: jira | confluence | docs-only`); an absent file or key defaults to `docs-only`. **Never ask the developer which backend applies** — that is exactly what AD-4 forbids (see project-context §3: the config is the contract).

Dispatch on the JSON ack:

- `"source_of_truth": "docs-only"` → continue with steps 2–5 below.
- `"source_of_truth": "jira"` → continue with steps 2–5, using the **JIRA variant of step 4** (step 4a).
- `"source_of_truth": "confluence"` → continue with steps 2–5, using the **Confluence variant of step 4** (step 4b).
- Any backend with `"implemented": false` → tell the developer it isn't built yet and stop. Do **not** silently fall back to docs-only.
- Non-zero exit (e.g. an invalid `source_of_truth` or `ai_tool` value) → surface the script's stderr to the developer **verbatim** and stop; the config file needs fixing before any kickoff can proceed.

The ack also carries the project's **AI tool** (`ai_tool`, default `claude-code` when undeclared — never ask). Remember it: step 5 passes it to the writer. If `ai_tool_implemented` is `false`, tell the developer that capture for that tool isn't built yet (AD-10 — metrics will be reduced-confidence until its adapter exists), but do **not** block the kickoff. Only override the resolved value per story if the team genuinely mixes tools and the developer says so.

### 2. Refuse a double kickoff early — unless the existing manifest is provably closed

If `.story.yaml` already exists at the repo root, read its `story_id`, then check whether `snapshots/` contains any file matching `{story_id}.*.json`.

- **No matching snapshot** (still open): behavior is unchanged — stop, tell the developer this story is already kicked off (show its `story_id` and `goal`). Re-running kickoff would change story identity mid-story. Do not delete or overwrite the manifest.
- **A matching snapshot exists** (Story 2.10 — AD-3 guarantees a snapshot revision is the authoritative signal a story closed): this manifest almost certainly lingered via a merge or branching off a sibling story branch, not a story still in progress. Tell the developer plainly, naming the closed story's `story_id`/`goal` and the snapshot revision found (e.g. "The `.story.yaml` here is from `story-<old-id>` ('<old-goal>'), which was already closed (snapshot found: `snapshots/story-<old-id>.v1.rev<N>.json`). This looks like an inherited manifest from a previous story on this branch lineage, not a story still in progress. OK to clear it and continue kicking off this new story?"). Only on explicit confirmation, delete `.story.yaml` (a real file delete — kickoff does not auto-commit this; that's the developer's own next commit, same as any other kickoff-adjacent change) and fall through to steps 3-5 as if no manifest had existed. On decline, stop exactly like the still-open case — do not proceed, do not delete anything.

This check is backend-agnostic: it only depends on whether a snapshot file exists for the stale manifest's `story_id`, never on whether the project uses openspec/the opsx wrapper.

### 3. Estimate story points (Phase-1, informational only)

Run the AD-6 Phase-1 estimator before asking for points:

```
uv run tools/estimate-phase1/main.py --repo-root <repo-root> --source-of-truth <resolved source_of_truth>
```

- If `phase1_points` is **not null**: present it to the developer as a **suggested** value ("Phase-1 estimate: N points — accept this or tell me a different number?"). It is never written silently — whatever the developer confirms (accepted or overridden) is what step 5's `--points` uses. **Remember the raw `phase1_points` number itself** (regardless of what the developer confirms) — step 5 passes it separately as `--points-estimated`, per AD-6a: the confirmed value and the raw estimate are always distinct, never substituted for each other, so Story 2.6's close-time reconciliation has a real Phase-1 number to compare against.
- If `phase1_points` is **null**: tell the developer why (`phase1_points_reason`, e.g. no openspec change found) and fall back to a plain ask — exactly the step-4 elicitation below, unassisted. If the reason specifically indicates no openspec change was found, add a one-line, non-blocking nudge: something like "if this project uses openspec SDD, running `/opsx:propose <change-name>` before kickoff next time gives this estimator a real number to work from" (`<change-name>` is a developer-chosen kebab-case name, never the `story_id` — these are unrelated identifiers). Informational only — never gates or delays this kickoff (FR5).
- If `must_split` is `true`: mention it as a heads-up (the scope looks large), but this **never blocks kickoff or changes any other behavior**.
- **Hard rule (FR5):** nothing from this estimator — a null result, `must_split`, an error, any field — may ever skip, shorten, gate, or disable capture for this story. If the script fails to run at all, proceed straight to step 4's plain ask as if it had returned null.

### 4. Elicit the docs-only fields

This step is docs-only-specific (Story 1.7). The JIRA/Confluence variants (4a/4b) are unaffected — no story name, no document read, and their `sprint` stays required exactly as before.

**4.0 — Story Name (first, free text):** ask "What should we call this story? (a short name, e.g. 'Auth Module Implementation')." One short phrase, not a sentence. This becomes the manifest's `name` field — distinct from `goal`, which describes what done looks like rather than naming the story. Not required to re-prompt aggressively if skipped, but ask for it before moving on.

**4.1 — Requirements document (optional):** ask "Do you have a requirements document (PRD) for this story? If so, give me its path." A "no" or no path given skips straight to 4.2, unmodified from today's behavior.

If a path is given, read it with the Read tool. Supported: `.md`, `.txt`, `.pdf`, `.docx`. A legacy binary `.doc`, a missing file, or an unreadable file is **not fatal** — say so plainly ("couldn't read that file — want to paste the text instead, or skip?") and fall back to 4.2 unassisted; never block kickoff on a bad path (FR5, same principle as step 3's estimator-failure fallback).

If read successfully, summarize the relevant content (scope/objective, any complexity hints) — never paste the raw document text into chat or into `.story.yaml`. From the summary, derive a candidate one-line goal and a candidate points value. These are **suggestions only**, clearly labeled as document-derived and kept distinct from any Phase-1 estimate (step 3) — if both exist, show both and let the developer pick or override. Neither is ever written without confirmation (CAP-1).

**4.2 — Points:** use the `AskUserQuestion` tool. Options: any Phase-1 estimate (step 3) and/or document-derived suggestion (step 4.1) first, then common story-point values (1, 2, 3, 5, 8) as additional options — the tool's built-in "Other" always covers a value outside the preset list.

**4.3 — Goal:** plain free-text chat, not `AskUserQuestion` (a one-line objective doesn't decompose into a small option set). Ask "What does done look like for this story?" — never the bare word "Goal." Pre-fill with the document-derived candidate from 4.1 when one exists, otherwise an open ask.

**4.4 — Milestone/sprint:** use `AskUserQuestion`, reworded away from "Sprint" to backend-neutral phrasing: "Milestone, release, or time period this belongs to." Options must include an explicit "None — this project doesn't track sprints/milestones" choice alongside 1-2 generic examples; "Other" covers anything else. Selecting "None" (or answering "none"/"n/a" via "Other") means step 5 **omits** `--sprint` entirely — never pass the literal string "none," omit the flag so the writer produces a true `null` (Story 1.7).

An optional **description** may also be offered, but never block on it.

**Re-prompt rule (Story 1.1 AC 3):** if **points** or **goal** is missing, blank, or invalid (e.g. points not a positive whole number), re-ask specifically — do not proceed, do not substitute defaults, never invoke the writer with incomplete input. **Sprint is the one exception (Story 1.7, docs-only only):** "none" is itself a valid, complete answer — do not re-prompt when the developer has genuinely said they don't track this.

### 4a. JIRA variant: fetch via MCP, then confirm

The JIRA fetch goes through **whichever JIRA MCP server this session has configured** (Story 1.6; the official Atlassian Remote MCP Server is the recommended default — OAuth under the developer's own JIRA access, no personal API token anywhere). The Story 1.3 subprocess adapter remains only as a fallback (step 4 below).

1. Ask the developer for the **JIRA issue key** (e.g. `PROJ-123`).
2. Fetch via the MCP tools (a two-call sequence; load them via tool search if deferred):
   1. `getAccessibleAtlassianResources` → take the `cloudId`. Resolve it **once per kickoff** and reuse it; don't re-resolve per call. If multiple sites come back, ask the developer which site applies (once — this is a site choice, not the AD-4 backend question, which stays forbidden).
   2. `getJiraIssue` with `cloudId`, `issueIdOrKey: <KEY>`, and `fields: ["summary", "description", <points field>, <sprint field>]` — where the points/sprint field IDs come from `.story-config.yaml` (`jira_points_field` / `jira_sprint_field`) when set, else the Jira Cloud defaults `customfield_10016` / `customfield_10020` (same override contract as Story 1.3).
3. Normalize the response (`issues.nodes[0].fields`) to the AD-4 shape — same rules Story 1.3's adapter implements:
   - **points** ← the points field: a number, or `null` when unset. Never invent a value.
   - **goal** ← `summary`.
   - **sprint** ← the sprint field: it's a list of sprint objects — the one with `state: "active"` wins; otherwise the **last** entry; take its `name`. `null` when absent.
   - **description** ← `description`, or `null`.
   Then confirm with the developer exactly as before: **points confirmation stays human** (CAP-1) even when JIRA supplied a number — if step 3 also produced a Phase-1 suggestion, mention both and let the developer pick. Any `null` field → elicit via the step-4 re-prompt rule.
4. **Degradation chain — kickoff is never blocked** (FR5):
   - Issue key not found / permission denied → tell the developer what the tool returned and re-ask the key.
   - **No JIRA MCP tools available in this session** → say so plainly ("no JIRA MCP server is connected — see prerequisites"). Then, only if `JIRA_BASE_URL`, `JIRA_EMAIL`, and `JIRA_API_TOKEN` are all set in the environment, fall back to the Story 1.3 script (`uv run tools/adapters/jira/main.py --repo-root <repo-root> --issue <KEY>`, same normalized ack, surface stderr verbatim on failure). Otherwise fall back to the plain step-4 ask, unassisted.
5. Proceed to step 5 with the confirmed values and `--source-of-truth jira` (the manifest records the backend, not the transport — MCP vs fallback script makes no difference downstream).

### 4b. Confluence variant: fetch, then confirm

Same flow as 4a with two differences — the reference is a **Confluence content id** (the number in the page URL), and the fetch command is:

```
uv run tools/adapters/confluence/main.py --repo-root <repo-root> --page <ID>
```

Credentials: `CONFLUENCE_BASE_URL` (including `/wiki` for Cloud sites), `CONFLUENCE_EMAIL`, `CONFLUENCE_API_TOKEN` — same rules as JIRA (env only, never in chat).

Confluence pages have no native points/sprint fields; the adapter reads **page labels** by convention: `points-<number>` (e.g. `points-5`) and `sprint-<name>` (e.g. `sprint-13`). Tell teams about this convention when fields come back `null` — labeled pages auto-fill, unlabeled pages just mean the developer confirms the values here (with the step-3 Phase-1 suggestion still available as a second data point). Points confirmation stays human either way (CAP-1), and nulls are elicited via the step-4 re-prompt rule. Proceed to step 5 with `--source-of-truth confluence`.

### 5. Write the manifest

Run from the repo root:

```
uv run tools/adapters/docs-only/main.py --repo-root <repo-root> [--name "<name>"] --points <N> --goal "<goal>" [--sprint "<sprint>"] [--description "<text>"] [--source-of-truth jira|confluence|docs-only] --ai-tool <resolved ai_tool> [--points-estimated <raw Phase-1 estimate>]
```

(`--source-of-truth` defaults to `docs-only`; the JIRA/Confluence flows pass their backend so the manifest records which one supplied the values. `--ai-tool` carries the step-1 resolved value — the manifest field AI-session capture producers read to pick their `ai.<tool>.*` event namespace. `--points-estimated` carries step 3's raw `phase1_points`, if any was produced — omit it entirely when step 3 returned null; never pass the developer's confirmed `--points` value here, the two must stay distinct per AD-6a. `--name` carries step 4.0's answer — **docs-only only** (Story 1.7); the JIRA/Confluence variants never pass it, and the writer defaults it to `null`. `--sprint` is omitted entirely when step 4.4 resolved to "none" — **docs-only only**; the JIRA/Confluence variants always pass a confirmed non-empty value, exactly as before Story 1.7.)

- **Exit 0:** the script prints a one-line JSON ack `{"ok": true, "story_yaml": ..., "story_id": ...}`. Relay to the developer, in order: **Story ID**, then **Name** (if one was given), then **Points**, **Goal**, **Sprint** ("Not applicable" when null), **Source of truth** — kickoff complete. Leading with Name (when present) rather than the opaque generated `story_id` alone makes the summary human-legible.
- **Non-zero exit:** surface the script's stderr to the developer **verbatim**, then return to step 4 and re-elicit. Never retry silently with altered values.

## Boundaries

- Only the writer script writes `.story.yaml` (atomically); this skill never writes or edits the manifest itself, and the resolver, fetch adapters, and Phase-1 estimator never write anything.
- Credentials never appear in `.story.yaml`, `.story-config.yaml`, chat, or any output (NFR4). On the MCP path this is structural — auth lives entirely in the MCP server's own OAuth session and this skill never sees a credential of any kind. On the fallback-script path, credentials live in environment variables read by the adapter at call time. **Never ask the developer to paste a token into chat** in either mode.
- Do not create `.story-events.jsonl`, `.active-story`, or any event/spool file — those belong to later capture stories (Epic 2/3).
- `.story.yaml` and `.story-config.yaml` are meant to be committed; neither ever contains credentials.
- The Phase-1 estimate is advisory only — it never gates, skips, or shortens capture, and the developer's confirmed points value always wins (FR5).
- A requirements document read at step 4.1 is summarized only — its raw content is never written into `.story.yaml`, `.story-config.yaml`, chat history it persists to, or any other tracked file. A summary informs the developer's own point/goal decision; it is never itself a manifest field.
