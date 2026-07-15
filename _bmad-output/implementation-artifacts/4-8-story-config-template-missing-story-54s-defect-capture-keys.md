---
baseline_commit: dbf46f9
---

# Story 4.8: `.story-config.yaml.example` Template Missing Story 5.4's Defect-Capture Keys

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer copying `.story-config.yaml.example` to configure my project,
I want the shipped template to document `test_commands`/`build_commands`,
so that I can actually discover and opt into Story 5.4's automatic compile/test defect capture without reading source code.

## Background

Reported live by the user (2026-07-14): after Story 5.4 shipped automatic compile/test defect capture (opt-in via `test_commands`/`build_commands` in `.story-config.yaml`), the actual shipped `.story-config.yaml.example` template — and `INSTALL.md`'s own embedded config example — were never updated to mention either key. Story 4.4's own test (`test_story_config_example_contains_every_documented_key`) has a hardcoded key list that also wasn't updated, so it silently kept passing without ever validating the new keys were present — a real gap in Story 5.4's own Definition of Done that should have caught this.

## Acceptance Criteria

1. **Given** the release artifact's `.story-config.yaml.example`
   **When** a developer opens it
   **Then** it documents `test_commands`/`build_commands` (commented out, with an explanation), same as every other optional key

2. **Given** `INSTALL.md`'s own embedded config example (Install step 3)
   **When** a developer reads it on GitHub without extracting the artifact
   **Then** it shows the same two keys, matching Story 4.4's original "self-contained without extracting" intent

3. **Given** Story 4.4's existing template-completeness test
   **When** this story is done
   **Then** its hardcoded key list includes `test_commands`/`build_commands`, so a future story adding a new config key without updating the template fails this test rather than passing silently

## Tasks / Subtasks

- [x] Task 1: update the shipped template (AC 1)
  - [x] Subtask 1.1: add `test_commands`/`build_commands` to `tools/build-release/.story-config.yaml.example`, commented out, matching the file's existing style
- [x] Task 2: update `INSTALL.md`'s embedded example (AC 2)
  - [x] Subtask 2.1: add the same two keys to the config block in Install step 3
- [x] Task 3: close the test gap (AC 3)
  - [x] Subtask 3.1: add `test_commands`/`build_commands` to `test_story_config_example_contains_every_documented_key`'s expected-key list
- [x] Task 4: verify live
  - [x] Subtask 4.1: full test suite green; build a real artifact and inspect the actual shipped `.story-config.yaml.example` content directly (not just the test passing)

## Dev Notes

### Scope

Pure documentation-completeness fix — no behavior change to `test_commands`/`build_commands` themselves (Story 5.4 already implemented the actual capture logic correctly; only the template/docs/completeness-test lagged).

### Source tree touched

```text
tools/build-release/.story-config.yaml.example  UPDATE  add test_commands/build_commands
tools/build-release/INSTALL.md                  UPDATE  add same keys to the embedded example
tests/build_release/test_build.py               UPDATE  completeness test's expected-key list
```

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5

### Debug Log References

Full suite: 323 passed. Built a real release artifact (`ai-metrics-capture-v0-test.zip`) and inspected the actual shipped `.story-config.yaml.example` content directly to confirm the new keys are really there, not just asserted by the test.

### Completion Notes List

- This is exactly the kind of gap the Story 4.4 completeness test exists to catch — but a hardcoded expected-key list only protects against omissions if it's kept in sync manually; worth remembering to update it whenever a future story adds a new `.story-config.yaml` key.

### File List

tools/build-release/.story-config.yaml.example (updated)
tools/build-release/INSTALL.md (updated)
tests/build_release/test_build.py (updated)
