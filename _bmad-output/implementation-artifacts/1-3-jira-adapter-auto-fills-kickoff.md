---
baseline_commit: 00e0c2dc1d9146601cc8c22e763e3bf1ee31afeb
---

# Story 1.3: JIRA Adapter Auto-Fills Kickoff

Status: done

## Story

As a developer on a JIRA-backed project,
I want my story's points/goal/sprint pulled automatically from a JIRA issue key,
so that I don't retype what JIRA already knows.

## Acceptance Criteria

1. **Given** `source_of_truth: jira` and a developer enters a JIRA issue key at kickoff, **when** the kickoff skill runs, **then** it fetches `{points, goal, sprint, description}` from JIRA and populates `.story.yaml`.
2. The JIRA API credential is read from environment variables at call time and never written into `.story.yaml`, the event log, or any snapshot (NFR4) — nor echoed into any ack, error message, or log output.

## Tasks / Subtasks

- [x] Task 1: Implement the JIRA fetch adapter `tools/adapters/jira/main.py` (AC: 1, 2)
  - [x] PEP 723 header + `from __future__ import annotations`; docstring stating the AD-4 contract (fetch-only: returns the normalized shape, never writes any file) and the env-var credential rule (NFR4)
  - [x] CLI: `--repo-root DIR` (required — locates `.story-config.yaml` for field-id overrides), `--issue KEY` (required, e.g. `PROJ-123`)
  - [x] Credentials read at call time from `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`; any missing → exit 2 naming the missing variable(s); the token value must never appear in stdout/stderr
  - [x] Fetch via **stdlib `urllib.request` only — `requests` is prohibited** (§1): `GET {base}/rest/api/2/issue/{key}?fields=summary,description,{points_field},{sprint_field}`, Basic auth header `base64(email:token)`, 15s timeout
  - [x] Field ids from config with defaults: `jira_points_field` (default `customfield_10016`), `jira_sprint_field` (default `customfield_10020`) — reuse the flat-YAML parsing approach (BOM-tolerant, paired quotes, inline comments) duplicated locally per the single-file-script convention
  - [x] Validate the response shape before using it (§3 never-trust-external-input): JSON object, `fields` dict, `summary` str; malformed → exit 2, no traceback
  - [x] Normalize: `goal` ← `summary`; `description` ← plain string or null (API v2 returns plain text); `points` ← numeric or null (int when integral); `sprint` ← handle the three real-world shapes: list of sprint objects (pick `state == "active"`, else last, take `.name`), legacy Greenhopper strings (regex `name=([^,\]]+)`), plain string; null when absent — nulls returned honestly, never defaulted (AD-10 philosophy)
  - [x] HTTP errors → exit 2 with actionable messages: 401/403 "check JIRA_EMAIL/JIRA_API_TOKEN", 404 "issue not found", URLError/timeout named plainly
  - [x] Success ack (one JSON line, exit 0): `{"ok": true, "points": <n|null>, "goal": <str>, "sprint": <str|null>, "description": <str|null>}`
- [x] Task 2: Writer gains `--source-of-truth` (AC: 1)
  - [x] `tools/adapters/docs-only/main.py`: optional `--source-of-truth {jira, confluence, docs-only}` (default `docs-only`, via argparse `choices`); manifest field uses it; docstring updated — this script is both the docs-only backend *and* the common manifest writer other adapters compose with (the extraction moment 1.1's notes planned for 1.3, done via composition instead of a shared module)
  - [x] No other writer behavior changes: validation, atomicity, refuse-overwrite, ack all identical
- [x] Task 3: Resolver marks jira implemented (AC: 1)
  - [x] `tools/adapters/resolve.py`: `IMPLEMENTED` gains `"jira"`; docstring line updated
  - [x] Update `tests/adapters/test_resolve.py::test_declared_jira_is_resolved_but_not_implemented` → now asserts `implemented: true` (rename accordingly); confluence case stays false
- [x] Task 4: `story-kickoff` SKILL.md jira branch (AC: 1, 2)
  - [x] On `source_of_truth: jira`: ask for the issue key → run the jira adapter → present fetched values → **always confirm points with the developer** (CAP-1's human bookend), elicit any null field via the Story 1.1 re-prompt rule → call the writer with `--source-of-truth jira`
  - [x] Adapter non-zero exit → surface stderr verbatim (it never contains the token) and stop or re-ask the issue key
  - [x] Note the env vars the developer must have set; never ask the developer to paste a token into chat
  - [x] Confluence branch message updates to "arrives in Story 1.4" only; docs-only flow untouched
- [x] Task 5: Tests (AC: 1, 2)
  - [x] `tests/adapters/test_jira.py` NEW — mock `urllib.request.urlopen` with `unittest.mock` (never a real API call, §5): success normalization (all four fields), null points, sprint as active-object list / legacy string / absent, missing env vars → exit 2 naming them, 401 and 404 → exit 2 friendly, malformed JSON body → exit 2, **token never appears in stdout or stderr** (assert on captured output in both success and error paths), adapter writes no files
  - [x] `tests/adapters/test_docs_only.py` UPDATE — `--source-of-truth jira` lands in the manifest; default stays `docs-only`; invalid value rejected by argparse
  - [x] Pure-function tests for `normalize()`/sprint extraction where practical
- [x] Task 6: Full regression + lint (all ACs)
  - [x] `uv run pytest -q` all green; `uv run ruff check .` + `format --check` clean; docs-only E2E behavior unchanged

### Review Follow-ups (AI)

External LLM review (Gemini, via PR #6) triaged per project-context §9 — 2026-07-09:

- [x] [AI-Review][Low] Fractional story points: adapter could return `1.5` but the writer rejected non-integers — writer now accepts any finite number > 0 (integers stay integers); hardening the `float()` change also added nan/inf rejection (a hole Gemini didn't flag but the fix would have opened). 3 regression tests.
- [x] [AI-Review][Low] Issue key interpolated raw into the URL — now `urllib.parse.quote(issue, safe="")`; regression test asserts `PROJ 123/../x` → `PROJ%20123%2F..%2Fx`.
- Factual correction — "missing test for `--source-of-truth` recorded in manifest": the test exists (`test_source_of_truth_flag_is_recorded`, added in this PR); pointed the reviewer at it, no change needed.
- Declined — extract shared `tools/adapters/config.py` for the duplicated parser: the spine's Stack table fixes single-file self-contained scripts; a shared module needs cross-dir import machinery (sys.path/packaging) the architecture deliberately avoids. **Flagged to Jayanth:** Story 1.4 adds a third copy — if that's the pain threshold, the right move is a spine amendment (e.g. a sanctioned `tools/lib/`), not review-driven drift. Logged as a wontfix issue.
- Declined — `__init__.py`/PYTHONPATH for native test imports: this is Issue #5 verbatim; no new issue.

## Dev Notes

### Scope — what this story is and is not

- Fetch-only JIRA adapter + writer flag + resolver/skill wiring. Do NOT build: Confluence (1.4), `ai_tool` (1.5), any event capture (Epic 2), credential *provisioning* (explicitly deferred by the spine — how the token gets into the env is not designed here), retry logic on HTTP failure (AD-9 retry applies to event appends, not kickoff fetches — a failed fetch just surfaces and the developer retries).
- Composition over shared module: adapters stay self-contained single-file `uv run` scripts (spine Stack table); the ~25-line flat-YAML parser is deliberately duplicated in jira/main.py rather than importing across script dirs (consistent with declined Issues #2/#5 — no packaging).

### Architecture compliance (binding invariants)

- **AD-4** — adapter *returns* the normalized `{points, goal, sprint, description}`; the manifest writer is a separate concern. Credentials from env at call time only; never persisted (NFR4). No adapter-specific fields may leak into `.story.yaml`.
- **§3 never-trust-external-input** — JIRA's response is untrusted: validate before use; malformed data exits 2 cleanly, no tracebacks, nothing written.
- **Nulls are honest** — a JIRA issue without points/sprint yields nulls in the ack; the *skill* resolves them with the developer (CAP-1 keeps points confirmation human). The adapter never invents values.
- **Ack pattern / exit codes / explicit addressing** (§3) — identical contract to 1.1/1.2.
- **Token secrecy is testable** — the fake token string used in tests must be asserted absent from all captured output, success and failure paths both.

### UPDATE-file analysis (read before touching)

- **`tools/adapters/docs-only/main.py`** — does today: validate-before-write, `story-{date}-{6hex}` id, hand-rolled flat YAML via `json.dumps` scalars, `write_atomic`, refuse-overwrite, JSON ack, exit 0/2, single shared `now`. This story adds ONE argparse arg (`--source-of-truth`, `choices=("jira","confluence","docs-only")`, default `"docs-only"`) and threads it into the manifest dict. Everything else is preserved — all 19 existing docs-only tests must pass with zero edits except new flag tests.
- **`tools/adapters/resolve.py`** — `IMPLEMENTED = ("docs-only",)` → `("docs-only", "jira")`. One-line change + docstring touch; the `implemented` ack field drives the skill's dispatch.
- **`.claude/skills/story-kickoff/SKILL.md`** — currently: resolver-first dispatch (docs-only proceeds; jira/confluence stop with "arrives in 1.3/1.4"; invalid config stops), double-kickoff refusal, three-field elicitation + re-prompt, writer invocation, boundaries. This story replaces the jira stop-branch with the fetch flow; docs-only and confluence branches otherwise preserved.

### JIRA API specifics (no web research needed — stable API)

- REST v2 (`/rest/api/2/issue/{key}`) returns `description` as a plain string — deliberately chosen over v3, whose Atlassian Document Format would need structured parsing. `?fields=` limits the payload to exactly the four fields needed.
- Jira Cloud auth: Basic with `email:api_token` base64-encoded (stdlib `base64.b64encode`). Server/DC PAT-Bearer support is out of scope (YAGNI until real demand).
- Story points/sprint are per-instance custom fields — hence the two config keys with the common Cloud defaults. Sprint field value shapes seen in the wild are the three handled in Task 1.
- `urllib.request.Request(url, headers=...)` + `urlopen(req, timeout=15)`; catch `HTTPError` (has `.code`), `URLError`, `json.JSONDecodeError`.

### Previous Story Intelligence (1.1 + 1.2)

- Patterns to copy: `main(argv) -> int`, `fail()`, `ack` via `json.dumps`, PEP 723 header, `dict[str, Any]` hints, f-strings, single shared `now` where timestamps correlate (none here).
- 1.2's parser learnings apply verbatim to the duplicated config reader: `utf-8-sig` (BOM), paired-quote `parse_scalar`, inline `#` comments — copy the fixed version, not the original.
- Test loader: same `importlib.util.spec_from_file_location` pattern (`tools/adapters/jira/main.py` — hyphen-free but consistency rules, see Issues #2/#5).
- Review history to pre-empt: Gemini watches for `.format()` (use f-strings), imprecise type hints, parser edge cases, and split-clock bugs. Mock cleanly with `unittest.mock.patch.object` on the loaded module.
- Tooling exists (pytest 8.3.5, ruff 0.9.6); commands: `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format tools tests`.

### Testing notes

- Mock at the module seam: `patch.object(jira_mod.request, "urlopen", ...)` returning a fake context manager whose `.read()` yields the JSON bytes; `HTTPError(url, 401, ...)` raised for auth cases. Env via `monkeypatch.setenv`/`delenv`.
- Fake token string like `"tok-SECRET-123"`; assert `"tok-SECRET-123" not in captured.out + captured.err` on every path.
- Writer flag tests extend `test_docs_only.py` minimally; do not restructure existing tests.

### Process requirements

- Branch `story/1.3-jira-adapter` off `develop`; PR title `Story 1.3: JIRA Adapter Auto-Fills Kickoff`; body links FR4 (CAP-4), AD-4, NFR4. Squash-merge. epics.md annotation inside the PR. Metrics entry (provisional at PR, final at merge) per docs/metrics.md conventions.

### Project Structure Notes

- `tools/adapters/jira/main.py` matches the spine Structural Seed exactly (`adapters/jira/`). The writer keeping its home in `docs-only/` while serving as the common writer is a pragmatic variance — flagged for a possible future `tools/manifest-writer/` move if 1.4 makes the naming genuinely misleading; not restructured now (§2 no premature abstraction).

### References

- [epics.md § Story 1.3](../planning-artifacts/epics.md) — ACs (lines 123–134)
- [ARCHITECTURE-SPINE.md § AD-4](../planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md) — adapter contract + credential rule; § Structural Seed
- [SPEC.md § CAP-4, CAP-1](../specs/spec-pm-metrics-ai-engineering-flow/SPEC.md) — kickoff adaptation; points confirmation stays human
- [project-context.md](../../project-context.md) — §1 stdlib-only, §3 ack/exit/never-trust-input, §4 credentials, §5–6 testing, §8–12 process
- [1-2 story file](1-2-project-level-source-of-truth-configuration.md) — parser learnings, review follow-ups, declined findings #2/#5

## Dev Agent Record

### Agent Model Used

claude-fable-5 (create-story context engineering + dev-story implementation)

### Debug Log References

- RED: collection error, `tools/adapters/jira/main.py` absent (18 new jira tests + 3 writer-flag tests + 1 resolver test rename authored first)
- GREEN: 56/56 after implementation (was 36)
- Lint: ruff check + format clean
- CLI E2E: missing env vars → `error: missing environment variable(s): JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN`, exit 2, no token anywhere; writer `--source-of-truth jira` → manifest records `source_of_truth: "jira"`

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created
- Implemented `tools/adapters/jira/main.py` as a **fetch-only** adapter (AD-4 literal reading: adapters *return* the shape): stdlib `urllib` GET on REST API v2 with Basic auth from env vars at call time, 15s timeout; response shape validated before use (§3); points/sprint from config-overridable custom fields (`jira_points_field`/`jira_sprint_field`, Jira Cloud defaults); sprint extraction handles active-object lists, legacy Greenhopper strings, and plain strings; nulls returned honestly, never invented; friendly exit-2 messages for missing env, 401/403, 404, network, malformed responses — token never echoed (asserted by test on success and failure paths).
- Writer composition: `docs-only/main.py` gained `--source-of-truth {jira,confluence,docs-only}` (default docs-only) — the extraction moment planned in 1.1 done via composition, no shared module, no packaging (consistent with declined Issues #2/#5). All existing writer behavior byte-identical.
- `resolve.py` `IMPLEMENTED` now `("docs-only", "jira")`; skill dispatch updated: jira flows through fetch → present → **human points confirmation always** (CAP-1) → nulls elicited via the re-prompt rule → writer with `--source-of-truth jira`. Confluence still stops honestly (1.4).
- AC→test traceability: AC 1 → success normalization, sprint/points shape tests, config-override test, writer-flag tests, resolver-implemented test; AC 2 (NFR4) → env-at-call-time test, missing-env naming test, token-absence assertions on both paths, adapter-writes-no-files test.
- No new dependencies (`urllib`/`base64`/`unittest.mock` all stdlib — `requests` deliberately not added).

### Change Log

- 2026-07-09: Story 1.3 implemented — JIRA fetch adapter (urllib, env creds, custom-field config), writer `--source-of-truth` flag, resolver jira→implemented, skill JIRA flow. 20 new tests (56 total). Status → review.
- 2026-07-09: Addressed Gemini review of PR #6 — 2 applied (fractional points end-to-end + nan/inf guard; URL-encoded issue key), 1 factual correction (the `--source-of-truth` test already exists), 2 declined with rationale (shared config module — spine-level question flagged to Jayanth; `__init__.py` = Issue #5). 60 tests passing.
- 2026-07-09: PR #6 squash-merged to `develop` (53b18d3). Status → done. Story branch retained per user preference.

### File List

- tools/adapters/jira/main.py (new)
- tests/adapters/test_jira.py (new)
- tools/adapters/docs-only/main.py (modified — `--source-of-truth` flag + docstring)
- tools/adapters/resolve.py (modified — IMPLEMENTED + docstring)
- .claude/skills/story-kickoff/SKILL.md (modified — JIRA variant step 3a, boundaries)
- tests/adapters/test_docs_only.py (modified — 3 flag tests)
- tests/adapters/test_resolve.py (modified — jira implemented:true)
- _bmad-output/implementation-artifacts/1-3-jira-adapter-auto-fills-kickoff.md (modified — this story file)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — status transitions)
- _bmad-output/planning-artifacts/epics.md (modified — §12 annotation, inside PR)
