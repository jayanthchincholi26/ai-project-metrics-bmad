---
baseline_commit: bb70d3057de596940fd6fae781efea79b2e6cd60
---

# Story 1.4: Confluence Adapter Auto-Fills Kickoff

Status: done

## Story

As a developer on a Confluence-backed project,
I want the same automatic fill as JIRA,
so that both PM tools are supported identically.

## Acceptance Criteria

1. **Given** `source_of_truth: confluence` and a developer enters a Confluence page reference at kickoff, **when** the kickoff skill runs, **then** it fetches `{points, goal, sprint, description}` from Confluence and populates `.story.yaml` in the same normalized shape as the JIRA adapter.
2. The Confluence credential is likewise never persisted to any shared file (NFR4) — nor echoed into any ack, error message, or output.

## Tasks / Subtasks

- [x] Task 1: Implement the Confluence fetch adapter `tools/adapters/confluence/main.py` (AC: 1, 2)
  - [x] Mirror the jira adapter exactly in contract: fetch-only, PEP 723 header, `main(argv)`, one-line JSON ack `{"ok": true, points, goal, sprint, description}`, exit 0/2, writes nothing
  - [x] CLI: `--repo-root DIR` (required), `--page ID` (required, numeric Confluence content id; URL-encoded before interpolation)
  - [x] Env at call time: `CONFLUENCE_BASE_URL` (incl. `/wiki` for Cloud), `CONFLUENCE_EMAIL`, `CONFLUENCE_API_TOKEN`; missing → exit 2 naming them; token never in output
  - [x] `GET {base}/rest/api/content/{id}?expand=body.storage,metadata.labels` via stdlib `urllib`, Basic auth, 15s timeout
  - [x] Normalize (validate untrusted response first, §3): `goal` ← `title` (required str); `description` ← `body.storage.value` HTML-stripped (regex tag removal + `html.unescape`), whitespace-collapsed, truncated to 500 chars, null when empty/absent; `points` ← label `points-<number>` (invalid number → null, lenient — a label is human-typed); `sprint` ← label `sprint-<rest>` remainder verbatim, null when absent
  - [x] Same friendly exit-2 error mapping as jira: 401/403 credential hint, 404 page not found, URLError, non-JSON body
  - [x] No config parser — Confluence needs no per-instance field ids (labels convention is fixed); document the label convention in the docstring
- [x] Task 2: Resolver + skill wiring (AC: 1)
  - [x] `resolve.py`: `IMPLEMENTED` → `("docs-only", "jira", "confluence")`; docstring's declared-but-unbuilt example removed
  - [x] `test_resolve.py`: confluence test now asserts `implemented: true` (rename)
  - [x] SKILL.md: confluence dispatch goes to a step-3b variant (ask page id → fetch → present → confirm points → elicit nulls → writer `--source-of-truth confluence`); document the `points-N`/`sprint-X` label convention so teams know how to make auto-fill work; remove the "arrives in 1.4" stop
- [x] Task 3: Tests `tests/adapters/test_confluence.py` (AC: 1, 2)
  - [x] Mirror test_jira.py: success normalization, label parsing (points/sprint present, absent, malformed points label → null), HTML-strip + truncation of description, empty body → null description, missing env naming all three, 401/404/network/malformed → exit 2, token-absence on success and failure paths, writes-no-files, page id URL-encoded
- [x] Task 4: Full regression + lint (all ACs)

### Review Follow-ups (AI)

External LLM review (Gemini, via PR #8) triaged per project-context §9 — 2026-07-09:

- [x] [AI-Review][Low] Label parsing stopped at the first prefix match even when invalid — a typo'd `points-typo`/bare `sprint-` could mask a valid label later in the list. Fixed with `continue`-style search (first *valid* label wins); 2 regression tests.
- Factual correction — "local `import math` inside try block in docs-only/main.py": no `math` import exists anywhere in that file (grep-verified); the finiteness check deliberately uses `float("inf")` to avoid one. Hallucinated finding; corrected on the PR, no change needed.

## Dev Notes

- **Same shape as JIRA is the whole point (AC 1):** the ack keys and null semantics must be byte-compatible with the jira adapter's — the skill's step-3a/3b logic is identical except for the fetch command and reference prompt (issue key vs page id).
- **Confluence reality check:** pages carry no native points/sprint. The pilot convention is labels (`points-5`, `sprint-13`); anything absent is null and the skill elicits it — points confirmation stays human regardless (CAP-1). Never invent values.
- **UPDATE files:** `resolve.py` (one tuple + docstring), `SKILL.md` (replace confluence stop-branch with 3b; keep everything else verbatim), `test_resolve.py` (one test rename+assert). Writer needs NO change — `confluence` is already in its `--source-of-truth` choices.
- **Previous story intelligence (1.3 review):** URL-encode the page reference (`parse.quote(page, safe="")`); f-strings; exact type hints; nan/inf lesson doesn't apply (no numeric CLI input — points come from labels and are parsed leniently). Copy jira/main.py's structure including error mapping; skip parse_scalar/read_config entirely (unneeded here — the spine-level shared-lib question from Issue #7 stays moot).
- **Testing:** same mocked-urlopen seam and fixtures style as test_jira.py; fake token `tok-CONF-SECRET` asserted absent both paths.
- **Process:** branch `story/1.4-confluence-adapter`; PR `Story 1.4: Confluence Adapter Auto-Fills Kickoff` linking FR4 (CAP-4), AD-4, NFR4; squash-merge; epics.md annotation inside PR; metrics entry provisional→final.

### References

- [epics.md § Story 1.4](../planning-artifacts/epics.md) (lines 136–147) · [ARCHITECTURE-SPINE.md § AD-4](../planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md) · [project-context.md](../../project-context.md) §1/§3/§4/§5–6 · [1-3 story file](1-3-jira-adapter-auto-fills-kickoff.md) (pattern source + review learnings)

## Dev Agent Record

### Agent Model Used

claude-fable-5 (create-story context engineering + dev-story implementation)

### Debug Log References

- RED: collection error, `tools/adapters/confluence/main.py` absent (18 new tests authored first + 1 resolver test rename)
- GREEN: 77/77 (was 60); ruff check/format clean
- CLI E2E: missing env vars → exit 2 naming all three CONFLUENCE_* variables

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created
- Implemented `tools/adapters/confluence/main.py`: fetch-only mirror of the jira adapter — stdlib urllib GET on `/rest/api/content/{id}?expand=body.storage,metadata.labels`, Basic auth from CONFLUENCE_* env at call time, page id URL-encoded, response validated before use. goal ← title; description ← HTML-stripped/unescaped body truncated to 500 chars (null when empty); points/sprint ← page labels `points-<n>` / `sprint-<name>` with honest nulls (malformed points label = human typo → null, skill elicits).
- No config parser needed (labels convention is fixed, no per-instance field ids) — the third parser copy feared in Issue #7 never materialized.
- `resolve.py` IMPLEMENTED now covers all three backends; SKILL.md gained step 3b (Confluence variant) documenting the label convention; writer untouched (`confluence` was already a choice).
- AC→test traceability: AC 1 → shape-parity test (ack keys identical to jira's), label parsing (present/absent/fractional/malformed), HTML-strip/truncate/null-description tests, resolver-implemented test; AC 2 (NFR4) → env-at-call-time guard naming all three vars, token-absence assertions on success and failure paths, writes-no-files test.
- 1.3 review learnings pre-applied: URL-encoded reference, f-strings, exact hints, lenient human-typed label parsing.

### Change Log

- 2026-07-09: Story 1.4 implemented — Confluence fetch adapter (labels convention for points/sprint, HTML-stripped description), resolver all-implemented, skill step 3b. 18 new tests (77 total). Status → review.
- 2026-07-09: Addressed Gemini review of PR #8 — 1 applied (resilient label parsing: first *valid* label wins), 1 factual correction (no `import math` exists in docs-only/main.py — hallucinated finding). 79 tests passing.
- 2026-07-09: PR #8 squash-merged to `develop` (43e779c). Status → done. Story branch retained per user preference.

### File List

- tools/adapters/confluence/main.py (new)
- tests/adapters/test_confluence.py (new)
- tools/adapters/resolve.py (modified — IMPLEMENTED + docstring)
- tests/adapters/test_resolve.py (modified — confluence implemented:true)
- .claude/skills/story-kickoff/SKILL.md (modified — step 3b, dispatch)
- _bmad-output/implementation-artifacts/1-4-confluence-adapter-auto-fills-kickoff.md (modified — this story file)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — status transitions)
- _bmad-output/planning-artifacts/epics.md (modified — §12 annotation, inside PR)
