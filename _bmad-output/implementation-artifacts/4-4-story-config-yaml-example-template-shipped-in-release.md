---
baseline_commit: 937e0a1
---

# Story 4.4: `.story-config.yaml.example` Template Shipped in the Release

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer adopting this capture tooling,
I want a ready-made, fully-commented `.story-config.yaml.example` in the release artifact,
so that I can copy and edit it instead of hand-typing every key from `INSTALL.md`'s prose — while the tool still never silently creates a *functional* config on my behalf.

## Acceptance Criteria

1. **Given** the release artifact
   **When** it's built
   **Then** it includes a new file at the archive root, `.story-config.yaml.example`, containing every documented config key — `source_of_truth`, `ai_tool`, the JIRA field overrides (`jira_points_field`/`jira_sprint_field`), and the cost rates (`hourly_rate`/`ai_input_rate`/`ai_output_rate`) — each shown **commented out**, with a one-line explanation of what it does and its default when absent

2. **Given** this is a template, not a functional config
   **When** the artifact is extracted
   **Then** **no** `.story-config.yaml` is created or modified automatically — a project's absence of that file is meaningful (AD-4: absent defaults to `docs-only`) and must stay entirely the developer's own explicit choice; this story ships an example file the developer copies themselves, it never auto-copies or renames it into place

3. **Given** `INSTALL.md`'s existing Install step 3 (currently: "create `.story-config.yaml` with this content")
   **When** this story is done
   **Then** it's reworded to: copy `.story-config.yaml.example` to `.story-config.yaml`, then edit it — the exact key/value content shown there is unchanged, just the instruction of *how* the developer gets to that content changes (copy-and-edit vs. type-from-scratch)

4. **Given** `tools/build-release/main.py`'s existing test suite already asserts the artifact's exact contents
   **When** this story is done
   **Then** existing tests are updated (not just new tests bolted on) to reflect the new file's presence — the artifact-contents test, the exclusion test, and any count/sort-order assertions all stay accurate

## Tasks / Subtasks

- [ ] Task 1: write the template (AC: 1, 2)
  - [ ] Subtask 1.1: create `tools/build-release/.story-config.yaml.example` (source lives alongside `INSTALL.md` in `build-release/`, same as that file — not inside `tools/` itself, since it's a repo-root artifact, not part of the capture tooling)
  - [ ] Subtask 1.2: content mirrors exactly what `INSTALL.md`'s Install step 3 and JIRA setup section already document as the real key/value pairs (don't invent new keys or defaults not already documented elsewhere)

- [ ] Task 2: ship it in the build (AC: 1, 4)
  - [ ] Subtask 2.1 (RED): add/update a test in `tests/build_release/test_build.py` asserting `.story-config.yaml.example` is present in the built artifact with the expected content (or at minimum, non-empty and containing each documented key as a commented line)
  - [ ] Subtask 2.2 (GREEN): add the new file to `tools/build-release/main.py`'s `iter_entries()`, following the exact same pattern already used for `INSTALL.md` (a module-level path constant, yielded once at the top of the generator, not part of the `tools/` directory walk)
  - [ ] Subtask 2.3: confirm the existing `test_artifact_excludes_planning_repo_and_build_internals` test still passes unmodified — the new file ships from `build-release/` (normally excluded) via the same explicit-yield exception `INSTALL.md` already uses, so this needs a quick check that the exclusion test's logic doesn't also have to special-case the new file the way `INSTALL.md` already needed a `name != "INSTALL.md"`-style carve-out (if it did; verify by reading the actual test before assuming)

- [ ] Task 3: update the install instructions (AC: 3)
  - [ ] Subtask 3.1: reword `INSTALL.md`'s Install step 3 from "create `.story-config.yaml` at the repo root: ```yaml ...```" to "copy `.story-config.yaml.example` to `.story-config.yaml`, then edit it to declare your project's PM tool" — keep the actual example content block shown inline too, so the instructions are still self-contained for someone reading `INSTALL.md` on GitHub without having extracted the artifact yet

- [ ] Task 4: full regression and live E2E (AC: 1-4)
  - [ ] Subtask 4.1: `uv run pytest` full suite green; `uv run ruff check .`; `uv run ruff format --check tools tests`
  - [ ] Subtask 4.2: live E2E — actually build a real artifact (`uv run tools/build-release/main.py --version v0-test --out-dir <scratch>`), extract it into a scratch git repo, confirm `.story-config.yaml.example` is present and copy-able, `cp .story-config.yaml.example .story-config.yaml` works and produces a file `tools/adapters/resolve.py` correctly parses (a real end-to-end proof, not just "the zip contains a file with this name")

## Dev Notes

### Scope — what this story is and is not

- Purely a packaging/onboarding convenience — no change to `tools/adapters/resolve.py`'s parsing logic, no new config keys beyond what's already documented, no change to any capture behavior.
- **Do NOT auto-create or auto-rename `.story-config.yaml` from the template during install or setup-hooks.** AC 2 is a hard boundary — the file's absence carries real meaning (AD-4's docs-only default), and `setup-hooks.py` must not start silently deciding a project's `source_of_truth` for it.

### Architecture compliance (binding invariants)

- **AD-4** — "declare once... an absent file or key defaults to docs-only." This story must not weaken that: shipping a *template* (never auto-applied) preserves the invariant that the file's presence/absence is always an explicit developer choice.
- `project-context.md` §12 (Story DoD) — existing tests must be updated in place where the artifact's contents assertions live, not left stale alongside new bolted-on tests (AC 4).

### Source tree touched

```text
tools/build-release/.story-config.yaml.example   NEW    the template shipped at the archive root
tools/build-release/main.py                       UPDATE iter_entries() yields the new file, same pattern as INSTALL.md
tests/build_release/test_build.py                 UPDATE existing artifact-contents/exclusion tests reflect the new file
tools/build-release/INSTALL.md                    UPDATE Install step 3 reworded to copy-then-edit
```

### Project Structure Notes

No conflicts — extends `tools/build-release/main.py`'s existing single-purpose "assemble the artifact" role, alongside the `INSTALL.md`-yielding precedent it already has.

### References

- [Source: tools/build-release/main.py#iter_entries] — the exact pattern (a module-level path constant, explicit yield) this story's new file follows, mirroring how `INSTALL.md` itself is already handled
- [Source: tests/build_release/test_build.py] — existing artifact-contents and exclusion tests to extend/verify, not duplicate
- [Source: tools/adapters/resolve.py] — the real config parser the live-E2E copy-and-edit result must actually work against
- [Source: ARCHITECTURE-SPINE.md#AD-4] — the declare-once/absent-defaults-to-docs-only invariant this story must not weaken
- [Source: project-context.md] — §1 stdlib-only, §12 Story DoD (update existing tests, don't just add new ones)

## Dev Agent Record

### Agent Model Used

_to be filled by dev-story_

### Debug Log References

_to be filled by dev-story_

### Completion Notes List

_to be filled by dev-story_

### File List

_to be filled by dev-story_
