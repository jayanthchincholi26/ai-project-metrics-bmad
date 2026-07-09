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

- `"source_of_truth": "docs-only"` → continue with steps 2–4 below.
- `"source_of_truth": "jira"` or `"confluence"` with `"implemented": false` → tell the developer their project declares that backend but its adapter arrives in Story 1.3 (JIRA) / 1.4 (Confluence), and stop. Do **not** silently fall back to docs-only.
- Non-zero exit (e.g. an invalid `source_of_truth` value) → surface the script's stderr to the developer **verbatim** and stop; the config file needs fixing before any kickoff can proceed.

### 2. Refuse a double kickoff early

If `.story.yaml` already exists at the repo root, stop and tell the developer: this story is already kicked off (show its `story_id` and `goal`). Re-running kickoff would change story identity mid-story. Do not delete or overwrite the manifest.

### 3. Elicit the three fields

Ask the developer to confirm, in one exchange if possible:

1. **Story points** — a whole number greater than 0
2. **Goal** — one line describing what done looks like
3. **Sprint** — the sprint this story belongs to (e.g. "Sprint 12")

An optional **description** may also be offered, but never block on it.

**Re-prompt rule (Story 1.1 AC 3):** if any of the three required fields is missing, blank, or invalid (e.g. points not a positive whole number), re-ask for the missing/invalid field(s) specifically — do not proceed, do not substitute defaults, and never invoke the writer with incomplete input.

### 4. Write the manifest

Run from the repo root:

```
uv run tools/adapters/docs-only/main.py --repo-root <repo-root> --points <N> --goal "<goal>" --sprint "<sprint>" [--description "<text>"]
```

- **Exit 0:** the script prints a one-line JSON ack `{"ok": true, "story_yaml": ..., "story_id": ...}`. Relay the `story_id` and the manifest path to the developer — kickoff complete.
- **Non-zero exit:** surface the script's stderr to the developer **verbatim**, then return to step 3 and re-elicit. Never retry silently with altered values.

## Boundaries

- Only the writer script writes `.story.yaml` (atomically); this skill never writes or edits the manifest itself, and the resolver never writes anything.
- Do not create `.story-events.jsonl`, `.active-story`, or any event/spool file — those belong to later capture stories (Epic 2/3).
- `.story.yaml` and `.story-config.yaml` are meant to be committed; neither ever contains credentials.
