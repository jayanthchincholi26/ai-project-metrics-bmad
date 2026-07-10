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

### 2. Refuse a double kickoff early

If `.story.yaml` already exists at the repo root, stop and tell the developer: this story is already kicked off (show its `story_id` and `goal`). Re-running kickoff would change story identity mid-story. Do not delete or overwrite the manifest.

### 3. Estimate story points (Phase-1, informational only)

Run the AD-6 Phase-1 estimator before asking for points:

```
uv run tools/estimate-phase1/main.py --repo-root <repo-root> --source-of-truth <resolved source_of_truth>
```

- If `phase1_points` is **not null**: present it to the developer as a **suggested** value ("Phase-1 estimate: N points — accept this or tell me a different number?"). It is never written silently — whatever the developer confirms (accepted or overridden) is what step 5 uses.
- If `phase1_points` is **null**: tell the developer why (`phase1_points_reason`, e.g. no openspec change found) and fall back to a plain ask — exactly the step-4 elicitation below, unassisted.
- If `must_split` is `true`: mention it as a heads-up (the scope looks large), but this **never blocks kickoff or changes any other behavior**.
- **Hard rule (FR5):** nothing from this estimator — a null result, `must_split`, an error, any field — may ever skip, shorten, gate, or disable capture for this story. If the script fails to run at all, proceed straight to step 4's plain ask as if it had returned null.

### 4. Elicit the three fields

Ask the developer to confirm, in one exchange if possible:

1. **Story points** — a whole number greater than 0 (pre-filled with the Phase-1 suggestion from step 3, if any)
2. **Goal** — one line describing what done looks like
3. **Sprint** — the sprint this story belongs to (e.g. "Sprint 12")

An optional **description** may also be offered, but never block on it.

**Re-prompt rule (Story 1.1 AC 3):** if any of the three required fields is missing, blank, or invalid (e.g. points not a positive whole number), re-ask for the missing/invalid field(s) specifically — do not proceed, do not substitute defaults, and never invoke the writer with incomplete input.

### 4a. JIRA variant: fetch, then confirm

1. Ask the developer for the **JIRA issue key** (e.g. `PROJ-123`).
2. Fetch the fields (credentials come from the developer's environment — `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`; **never ask the developer to paste a token into chat**):

   ```
   uv run tools/adapters/jira/main.py --repo-root <repo-root> --issue <KEY>
   ```

3. On exit 0, the ack carries `{points, goal, sprint, description}` (any field JIRA doesn't have is `null`). Present the fetched values, then:
   - **Always confirm points with the developer** — even when JIRA supplied a number, points confirmation stays human (CAP-1). If step 3 also produced a Phase-1 suggestion, mention both and let the developer pick.
   - Any `null` field → elicit it via the step-4 re-prompt rule.
4. On non-zero exit → surface stderr **verbatim** (it never contains the token) and either re-ask the issue key (e.g. typo'd key / 404) or stop (missing env vars, credential failure — the developer must fix their environment first).
5. Proceed to step 5 with the confirmed values and `--source-of-truth jira`.

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
uv run tools/adapters/docs-only/main.py --repo-root <repo-root> --points <N> --goal "<goal>" --sprint "<sprint>" [--description "<text>"] [--source-of-truth jira|confluence|docs-only] --ai-tool <resolved ai_tool>
```

(`--source-of-truth` defaults to `docs-only`; the JIRA/Confluence flows pass their backend so the manifest records which one supplied the values. `--ai-tool` carries the step-1 resolved value — the manifest field AI-session capture producers read to pick their `ai.<tool>.*` event namespace.)

- **Exit 0:** the script prints a one-line JSON ack `{"ok": true, "story_yaml": ..., "story_id": ...}`. Relay the `story_id` and the manifest path to the developer — kickoff complete.
- **Non-zero exit:** surface the script's stderr to the developer **verbatim**, then return to step 4 and re-elicit. Never retry silently with altered values.

## Boundaries

- Only the writer script writes `.story.yaml` (atomically); this skill never writes or edits the manifest itself, and the resolver, fetch adapters, and Phase-1 estimator never write anything.
- Credentials live in environment variables, read by the adapter at call time — never in `.story.yaml`, `.story-config.yaml`, chat, or any output (NFR4).
- Do not create `.story-events.jsonl`, `.active-story`, or any event/spool file — those belong to later capture stories (Epic 2/3).
- `.story.yaml` and `.story-config.yaml` are meant to be committed; neither ever contains credentials.
- The Phase-1 estimate is advisory only — it never gates, skips, or shortens capture, and the developer's confirmed points value always wins (FR5).
