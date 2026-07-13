---
baseline_commit: 18edb0b
---

# Story 2.10: A Closed Story's Manifest Doesn't Block the Next Story's Kickoff

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want kicking off a new story to work normally even though the previous story's `.story.yaml` was merged into my base branch,
so that ordinary branch-per-story git hygiene (branching the next story off `develop`, or off a sibling story branch) never gets blocked by a stale manifest.

## Acceptance Criteria

1. **Given** `.story.yaml` already exists at the repo root when kickoff starts (SKILL.md step 2)
   **When** kickoff checks `snapshots/` for a file matching `{story_id}.*.json` (`story_id` read from the existing manifest)
   **Then** if a matching snapshot file exists, the story named by that manifest is **provably already closed** (AD-3: a snapshot revision is the authoritative signal a story closed) — kickoff tells the developer plainly (showing the stale manifest's `story_id`/`goal`, and which snapshot revision(s) exist) and asks for confirmation to clear `.story.yaml` before proceeding with the new kickoff

2. **Given** the developer confirms clearing the stale manifest (AC 1)
   **When** kickoff proceeds
   **Then** it deletes `.story.yaml` (a real file delete, same as the developer doing `git rm .story.yaml` themselves — kickoff does not silently overwrite it in place) and continues the normal kickoff flow (steps 3-5) from there, writing a fresh manifest with a new `story_id`

3. **Given** `.story.yaml` exists but **no** matching snapshot exists under `snapshots/` for its `story_id`
   **When** kickoff runs step 2's check
   **Then** behavior is **unchanged from today**: kickoff refuses and tells the developer this story is still open (today's existing hard block) — this is the genuinely-still-working-the-same-story case, which must never be weakened

4. **Given** this fix
   **When** `story-2` is kicked off on a branch that inherited `story-1`'s manifest (via merge into `develop`, or via branching off `story-1`'s own branch) **after `story-1` has been archived/snapshotted**
   **Then** kickoff proceeds normally (per AC 1-2) with no manual `git rm` needed from the developer — this must work identically regardless of whether the project uses openspec/opsx or plain JIRA/Confluence/docs-only close-out (backend-agnostic, since the check is purely "does a snapshot exist for this story_id," never dependent on the opsx wrapper)

## Tasks / Subtasks

- [ ] Task 1: teach `story-kickoff` to distinguish a closed story's stale manifest from a genuinely in-progress one (AC: 1, 3)
  - [ ] Subtask 1.1: update `.claude/skills/story-kickoff/SKILL.md` step 2 ("Refuse a double kickoff early") — when `.story.yaml` exists, read its `story_id`, then check whether any file matching `snapshots/{story_id}.*.json` exists (a directory listing/glob is sufficient; no new script needed — this is a plain existence check, not a value the manifest writer or resolver needs to compute)
  - [ ] Subtask 1.2: if no matching snapshot exists, keep today's exact behavior — stop, tell the developer the story's `story_id`/`goal`, do not delete or overwrite the manifest
  - [ ] Subtask 1.3: if a matching snapshot exists, tell the developer plainly that this branch inherited an already-closed story's manifest (name the closed story's `story_id`/`goal` and the snapshot revision found), and ask for explicit confirmation before clearing it — never delete without asking

- [ ] Task 2: clear-and-proceed flow (AC: 2, 4)
  - [ ] Subtask 2.1: on confirmation, delete `.story.yaml` (a real file delete — this mirrors what a developer would do manually with `git rm .story.yaml`, except kickoff performs the file delete directly; committing that deletion is the developer's own next `git commit`, exactly like any other kickoff-adjacent file change today — kickoff has never auto-committed anything and shouldn't start here)
  - [ ] Subtask 2.2: after clearing, fall through to the normal step 3-5 kickoff flow (Phase-1 estimate, field elicitation, manifest write) exactly as if `.story.yaml` had never existed — no special-cased shortened flow
  - [ ] Subtask 2.3: on decline (developer says no), stop exactly like today's hard block — do not proceed with kickoff, do not delete anything

- [ ] Task 3: manual E2E verification and doc parity (AC: 1-4)
  - [ ] Subtask 3.1: this is a skill-instruction change (SKILL.md), not a Python code change — there is no automated test surface for it, matching this project's established pattern for skill-level behavior (e.g. Story 1.6's MCP two-call sequence is verified via live E2E, not pytest)
  - [ ] Subtask 3.2: reproduce the exact scenario found in testing — kick off a story, archive it (produces a snapshot), branch a second story off the same lineage (inheriting the closed story's `.story.yaml`), attempt kickoff for the second story, confirm it now offers to clear the stale manifest instead of hard-blocking, confirm accepting proceeds to a normal kickoff with a new `story_id`
  - [ ] Subtask 3.3: separately verify AC 3 is not weakened — attempt kickoff for a second story on a branch where `.story.yaml` exists **and no snapshot exists yet** for its `story_id` (the still-in-progress case); confirm today's hard block still fires unchanged
  - [ ] Subtask 3.4: verify AC 4's backend-agnostic claim — this scenario must not reference or depend on `tools/opsx-wrapper/main.py` at all; the check is purely "does `snapshots/{story_id}.*.json` exist," which is produced by the snapshot assembler regardless of which source-of-truth backend or close-out path (wrapper vs plain `uv run tools/snapshot-assembler/main.py`) was used

## Dev Notes

### Scope — what this story is and is not

- This is a **skill-instruction change only** (`.claude/skills/story-kickoff/SKILL.md`) — no Python code in `tools/` changes. No new script, no new manifest field, no new event type.
- **Do NOT build in this story:** any wrapper-side automatic teardown of `.story.yaml` on archive (considered and explicitly rejected — see the design decision below); any general "clean up stale files" scanning beyond this one specific check; any change to `tools/opsx-wrapper/main.py` or `tools/snapshot-assembler/main.py` — both stay untouched, since the fix is entirely about what kickoff does when it *finds* an existing manifest, not about what archiving does.

### Why this matters, and why this specific design (read before editing SKILL.md)

Found live during pilot testing (2026-07-13): `story/AI-53` was branched after `story/add-user-basic-auth` had been fully archived, snapshotted, committed, and pushed — yet still carried the old story's `.story.yaml` (inherited via the branch lineage), and kickoff's existing guard (SKILL.md step 2) blocked it with "this story is already kicked off," requiring a manual `git rm .story.yaml && git commit` before proceeding. The guard itself is *correct* for its original purpose (never silently overwrite an in-progress story's identity) — the gap is that it has no way to tell "still in progress" apart from "already closed, manifest just lingered."

**Design decision (resolved during story creation, not left open for the dev agent to decide):** two alternatives were considered and rejected in favor of the snapshot-existence check specified in the ACs above:
- *Wrapper-side automatic teardown* (`tools/opsx-wrapper/main.py` deletes `.story.yaml` on successful archive) — rejected because it only covers projects using openspec/the opsx wrapper; a plain JIRA/Confluence/docs-only project that closes out via `uv run tools/snapshot-assembler/main.py --repo-root .` directly (no wrapper involved) would still hit this bug. It would also mean archiving has a git-mutating side effect beyond producing a snapshot, which is more surprising behavior to add to that command than strictly necessary.
- *A documented manual step* (Story Archival Checklist gains a "delete `.story.yaml`" bullet) — rejected because it's the same class of problem Story 2.11 just fixed: a manual step a developer can forget, with no enforcement.

The snapshot-existence check is backend-agnostic (AD-3 already guarantees every close produces a snapshot, regardless of source-of-truth or close-out mechanism) and needs no new state, script, or wrapper change — it only teaches the skill's existing step 2 to look at one more piece of already-available information (`snapshots/`) before deciding whether to block.

### Architecture compliance (binding invariants)

- **AD-5** — "`.story.yaml` is the sole source of story identity every capture producer reads." This story doesn't change that invariant; it changes *when kickoff is willing to replace* the manifest, always with an explicit confirmation, never silently.
- **AD-3** — "every close produces a new immutable revision; nothing is overwritten in place." This story leans directly on that guarantee: a snapshot's mere existence for a given `story_id` is sufficient, reliable proof that story closed, regardless of which adapter/backend produced it.
- **CAP-1 (points confirmation stays human)** and the broader "never silently write/delete" pattern already established throughout `story-kickoff/SKILL.md` (e.g. step 4.1's document-summary-never-auto-written rule) — clearing a stale manifest must follow the same never-silent principle: confirm, then act, never act unprompted.

### What "confirmation" looks like (for the dev agent writing the SKILL.md prose)

Match the tone and structure of the rest of `SKILL.md`'s step 2 and step 4 — plain conversational language, not a scripted dialog. Something like: "The `.story.yaml` here is from `story-<old-id>` ("<old-goal>"), which was already closed (snapshot found: `snapshots/story-<old-id>.v1.rev<N>.json`). This looks like an inherited manifest from a previous story on this branch lineage, not a story still in progress. OK to clear it and continue kicking off this new story?" — then proceed only on a clear yes.

### Testing standards (project-context.md §5/§6)

- This story has **no pytest surface** — it is purely a change to skill instructions (natural-language guidance Claude follows at kickoff time), not to any file under `tools/`. This matches the existing precedent for skill-level-only changes in this project (Story 1.6's MCP fetch sequence, Story 1.7's `AskUserQuestion`-based elicitation) — Definition of Done for this story is live manual E2E (Task 3), not an automated test suite.
- Do not invent a Python test for this story just to have one — there is no code to unit test. If a future refactor moves this check into a script (e.g. a small `tools/adapters/resolve.py`-style helper), test it then; don't build that abstraction speculatively here (project-context.md §2: no premature abstraction).

### Source tree touched

```text
.claude/skills/story-kickoff/SKILL.md  UPDATE  step 2 ("Refuse a double kickoff early") gains the snapshot-existence check and confirm-then-clear flow
```

No files under `tools/` or `tests/` are touched by this story.

### Project Structure Notes

No conflicts — this story only extends the existing kickoff skill's step 2, the same section Story 1.7 last modified.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.10] — the live-testing incident this story fixes, and the resolved design decision (rejecting wrapper-side teardown and a manual checklist step in favor of the snapshot-existence check)
- [Source: .claude/skills/story-kickoff/SKILL.md#2. Refuse a double kickoff early] — the exact guard this story extends
- [Source: tools/snapshot-assembler/main.py] — confirms the snapshot filename pattern (`{story}.v{SCHEMA_VERSION}.rev{revision}.json`) that Task 1's existence check must match against
- [Source: ARCHITECTURE-SPINE.md#AD-3, AD-5] — the never-overwritten-snapshot and sole-manifest-identity invariants this story's design leans on
- [Source: project-context.md] — §2 no premature abstraction, §8-12 branch/PR/DoD

## Dev Agent Record

### Agent Model Used

_to be filled by dev-story_

### Debug Log References

_to be filled by dev-story_

### Completion Notes List

_to be filled by dev-story_

### File List

_to be filled by dev-story_
