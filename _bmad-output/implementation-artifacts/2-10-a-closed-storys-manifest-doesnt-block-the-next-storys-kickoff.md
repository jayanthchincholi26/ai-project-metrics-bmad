---
baseline_commit: 18edb0b
---

# Story 2.10: A Closed Story's Manifest Doesn't Block the Next Story's Kickoff

Status: review

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

- [x] Task 1: teach `story-kickoff` to distinguish a closed story's stale manifest from a genuinely in-progress one (AC: 1, 3)
  - [x] Subtask 1.1: update `.claude/skills/story-kickoff/SKILL.md` step 2 ("Refuse a double kickoff early") — when `.story.yaml` exists, read its `story_id`, then check whether any file matching `snapshots/{story_id}.*.json` exists (a directory listing/glob is sufficient; no new script needed — this is a plain existence check, not a value the manifest writer or resolver needs to compute)
  - [x] Subtask 1.2: if no matching snapshot exists, keep today's exact behavior — stop, tell the developer the story's `story_id`/`goal`, do not delete or overwrite the manifest
  - [x] Subtask 1.3: if a matching snapshot exists, tell the developer plainly that this branch inherited an already-closed story's manifest (name the closed story's `story_id`/`goal` and the snapshot revision found), and ask for explicit confirmation before clearing it — never delete without asking

- [x] Task 2: clear-and-proceed flow (AC: 2, 4)
  - [x] Subtask 2.1: on confirmation, delete `.story.yaml` (a real file delete — this mirrors what a developer would do manually with `git rm .story.yaml`, except kickoff performs the file delete directly; committing that deletion is the developer's own next `git commit`, exactly like any other kickoff-adjacent file change today — kickoff has never auto-committed anything and shouldn't start here)
  - [x] Subtask 2.2: after clearing, fall through to the normal step 3-5 kickoff flow (Phase-1 estimate, field elicitation, manifest write) exactly as if `.story.yaml` had never existed — no special-cased shortened flow
  - [x] Subtask 2.3: on decline (developer says no), stop exactly like today's hard block — do not proceed with kickoff, do not delete anything

- [x] Task 3: manual E2E verification and doc parity (AC: 1-4)
  - [x] Subtask 3.1: this is a skill-instruction change (SKILL.md), not a Python code change — there is no automated test surface for it, matching this project's established pattern for skill-level behavior (e.g. Story 1.6's MCP two-call sequence is verified via live E2E, not pytest)
  - [x] Subtask 3.2: reproduce the exact scenario found in testing — kick off a story, archive it (produces a snapshot), branch a second story off the same lineage (inheriting the closed story's `.story.yaml`), attempt kickoff for the second story, confirm it now offers to clear the stale manifest instead of hard-blocking, confirm accepting proceeds to a normal kickoff with a new `story_id`
  - [x] Subtask 3.3: separately verify AC 3 is not weakened — attempt kickoff for a second story on a branch where `.story.yaml` exists **and no snapshot exists yet** for its `story_id` (the still-in-progress case); confirm today's hard block still fires unchanged
  - [x] Subtask 3.4: verify AC 4's backend-agnostic claim — this scenario must not reference or depend on `tools/opsx-wrapper/main.py` at all; the check is purely "does `snapshots/{story_id}.*.json` exist," which is produced by the snapshot assembler regardless of which source-of-truth backend or close-out path (wrapper vs plain `uv run tools/snapshot-assembler/main.py`) was used

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

claude-sonnet-5 (create-story context engineering + dev-story implementation)

### Debug Log References

- No pytest surface for this story (skill-instruction change only, per Dev Notes) — Definition of Done is live manual E2E, executed for real (not simulated):
- Live E2E #1 (AC 1, 2, 4 — closed manifest, offer-to-clear): a scratch repo with `.story.yaml` for `story-20260710-abc123` and a matching `snapshots/story-20260710-abc123.v1.rev1.json` — actually invoked the `story-kickoff` skill (via the Skill tool) against this repo. It correctly detected the matching snapshot, named the closed story's `story_id`/`goal`/snapshot revision, and asked for confirmation. On confirming, it deleted `.story.yaml` and proceeded through steps 3-5 (Phase-1 estimate → null, docs-only elicitation via `AskUserQuestion`, manifest write) to a **successful kickoff with a new, distinct `story_id`** (`story-20260713-2f8b11`, vs. the old `story-20260710-abc123`)
- Live E2E #2 (AC 3 — still-open manifest, unweakened hard block): same scratch repo, `.story.yaml` swapped to `story-20260713-stillopen` with **no** matching snapshot file — re-invoked the skill; it correctly hard-blocked exactly as before ("this story is already kicked off," showing `story_id`/goal), no clear offered, nothing deleted
- Full regression (`uv run pytest -q`, `uv run ruff check .`) confirmed green — this story touches no Python, so this is a no-change confirmation, not a meaningful regression test in itself
- Post-review Live E2E #3 (missing `snapshots/` directory entirely): scratch repo, `.story.yaml` with a real `story_id` but no `snapshots/` folder at all (a fresh repo where nothing has ever been archived) — re-invoked the skill; correctly treated the missing directory as "no matching snapshot," hard-blocked exactly as the still-open case, manifest untouched
- Post-review Live E2E #4 (malformed manifest, no `story_id` key): scratch repo, `.story.yaml` missing its `story_id` key entirely, **with** a `snapshots/` file present matching a different, old `story_id` (deliberately planted to prove the malformed-manifest check runs first and isn't fooled by an unrelated snapshot) — re-invoked the skill; correctly treated the malformed manifest as still-open without even attempting the snapshot check, hard-blocked, manifest untouched

### Completion Notes List

- Task 1: `.claude/skills/story-kickoff/SKILL.md` step 2 ("Refuse a double kickoff early") now reads the existing manifest's `story_id`, then checks `snapshots/` for a file matching `{story_id}.*.json`. No matching snapshot → today's exact hard-block behavior, unchanged. A matching snapshot → tells the developer the closed story's identity and the snapshot revision found, asks for confirmation before clearing.
- Task 2: on confirmation, the instructions direct a real file delete of `.story.yaml` (never an auto-commit — that stays the developer's own next commit, consistent with every other kickoff-adjacent file change), then fall through to steps 3-5 unmodified. On decline, behavior matches today's hard block exactly — nothing proceeds, nothing is deleted.
- Task 3: both ACs' scenarios were exercised via **real invocations of the actual skill** (not just read through and reasoned about) in a scratch repo, per this project's established live-E2E discipline for skill-level changes (matching Story 1.6/1.7's precedent) — the closed-manifest path correctly produced a fresh `story_id` after clearing, and the still-open path correctly stayed hard-blocked.
- No new dependencies, no Python code changes, no architecture deviations from the story file. The resolved design decision (kickoff-side snapshot check, rejecting both a wrapper-side auto-teardown and a manual checklist step) was made during story creation and implemented exactly as specified.

### File List

- .claude/skills/story-kickoff/SKILL.md (modified — step 2 gains the snapshot-existence check and confirm-then-clear flow; post-review, also a missing-`story_id` fallback and a missing-`snapshots/`-directory fallback)
- _bmad-output/implementation-artifacts/2-10-a-closed-storys-manifest-doesnt-block-the-next-storys-kickoff.md (this file — task checkboxes, Dev Agent Record, status)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — story status transitions)

### Review Follow-ups (AI)

External LLM review (Gemini, via PR #24) — 2026-07-13, all 3 findings genuine (this PR's own new instruction text, no misattribution):

- [x] [AI-Review][Minor] Instructions didn't explicitly say `snapshots/` resolves from the same `<repo-root>` passed to every other command, risking a cwd-drift bug if the agent checked the wrong directory. Fixed: explicit `<repo-root>/snapshots/` wording added.
- [x] [AI-Review][Medium] A repo where no story has ever been archived yet has no `snapshots/` directory at all — instructions didn't say what to do, risking a stall or error. Fixed: explicitly treat a missing `snapshots/` directory as "no matching snapshot." Verified live (Live E2E #3).
- [x] [AI-Review][Medium] A malformed or `story_id`-less `.story.yaml` wasn't handled — the agent could have tried a generic glob or failed parsing. Fixed: explicitly treat a missing/unparseable `story_id` as still-open, skipping the snapshot check entirely. Verified live (Live E2E #4), including the case where an unrelated snapshot exists for a different `story_id` — confirmed it doesn't fool the check.

All 3 findings verified against the actual PR #24 diff before fixing (`git log --oneline -1 story/2.10-stale-manifest-guard -- .claude/skills/story-kickoff/SKILL.md` confirms the file is this PR's own new instruction text) — no misattribution this round.
