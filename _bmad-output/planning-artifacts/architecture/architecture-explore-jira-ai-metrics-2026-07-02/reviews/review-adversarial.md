# Adversarial Review — ARCHITECTURE-SPINE (ai-engineering-metrics-capture)

**Reviewer stance:** adversarial. Goal: find two units, each fully compliant with AD-1..AD-7 individually, that produce incompatible builds when integrated. All findings assume good-faith literal compliance — no rule is broken, only under-specified.

**Verdict:** The spine correctly isolates producers from the shared store (AD-1/AD-2) and fixes the crossing-the-boundary contract (AD-3), but it fixes only the *outer* envelope shapes, not the internal vocabulary, ownership, or timing inside them — leaving at least seven independently-compliant fork points where two builders diverge.

---

## Finding 1 — Snapshot envelope internals are unowned (SEVERITY: HIGH)

**Rule as written:** AD-3 + Consistency table fix the snapshot envelope to `{schema_version, story_id, pm_metrics, engineering_metrics, story_point_cost, token_cost}`. Nothing constrains what's *inside* `pm_metrics` vs `story_point_cost`, even though AD-6 explicitly produces a Phase-1 estimate, a Phase-2 actual, and a variance — three related numbers that could reasonably live under either key.

**Builder A** (owns the snapshot assembler, reads AD-6 literally): puts `points_estimated`, `points_actual`, `points_variance` inside `story_point_cost`, and leaves `pm_metrics` to hold only adapter-sourced fields (`goal`, `sprint`, `description`, `points` = the JIRA-stated estimate from AD-4).

**Builder B** (owns the JIRA adapter integration, reads AD-4 literally): treats "points" as a single PM-facing concept and puts the full Phase-1/Phase-2/variance triple inside `pm_metrics.points`, leaving `story_point_cost` empty/reserved for token-derived $ cost only.

Both satisfy AD-3 ("only a versioned snapshot schema crosses the boundary"), AD-6 ("both figures recorded, variance logged, never collapsed"), and AD-4 (adapter returns `points` as one of its four fields) — yet a central presentation layer built against Builder A's shape breaks against Builder B's, and vice versa. There are now **two owners of "points"**: the adapter's PM-tool-sourced value and the kickoff skill's computed estimate, with no rule saying which key holds which, or whether they're even distinct fields.

**Tightened/new AD:**
> **AD-3a — Snapshot internal schema is fixed, not just its top-level keys.** Each of the four snapshot families (`pm_metrics`, `engineering_metrics`, `story_point_cost`, `token_cost`) has a companion field-level schema checked into the repo (e.g. `assembly/snapshot.schema.json`) versioned in lockstep with `schema_version`. `story_point_cost` is the *sole* owner of `{estimated, actual, variance}` per AD-6; `pm_metrics.points` (if present) is read-only PM-tool metadata from AD-4 and MUST NOT be interpreted as an estimate. The assembler validates against this schema before writing; a snapshot that doesn't validate is not emitted.

---

## Finding 2 — Event `type` namespace is unowned per-source (SEVERITY: HIGH)

**Rule as written:** AD-1 fixes the event *envelope* (`{story_id, source, type, timestamp, payload}`) but `type` and `payload` are free text/free-form, and nothing scopes `type` values per `source`.

**Builder A** (git hooks): emits `type: "commit"` with `payload: {sha, message, files_changed}` from `post-commit`.

**Builder B** (opsx CLI wrapper): also emits `type: "commit"` — because the wrapper intercepts `opsx apply` steps that internally shell out to git — with `payload: {stage, task_id}`, a structurally different payload for the same `type` string.

Both comply with AD-1 (append-only, no shared-state writes) and with the envelope shape in the Consistency table (which only fixes the five envelope keys, not the payload contents or a `type` vocabulary). The snapshot assembler, reducing the merged log, cannot reliably group or de-duplicate "commit" events — Builder A's and Builder B's events collide under one `type` with incompatible payload shapes, silently corrupting whichever metric (e.g. commit-count for engineering_metrics, or task-progress for pm_metrics) reduces over `type == "commit"`.

**Tightened/new AD:**
> **AD-1a — Event `type` is namespaced by source and enumerated.** `type` values are drawn from a closed, per-source enum declared in `capture/<source>/EVENTS.md` (e.g. `git.commit`, `git.checkout`, `cc.tool_use`, `cc.session_start`, `opsx.stage_change`). No two sources may emit the same `type` string. The assembler rejects/quarantines any event whose `type` isn't in the declared enum for its `source`.

---

## Finding 3 — Concurrent pointer-close race at branch-checkout-inside-session (SEVERITY: HIGH)

**Rule as written:** AD-7 says the pointer "is updated automatically on `git checkout` and Claude Code `SessionStart`" and that changing the pointer closes the outgoing slice / opens the incoming one — but a `git checkout` performed *from inside* an already-running Claude Code session (e.g., the agent runs `git checkout` as a tool call) fires the git `post-checkout` hook without any `SessionStart`/`SessionEnd` boundary.

**Builder A** (owns the git hook): on `post-checkout`, unconditionally closes the current time slice and opens a new one keyed to the new branch's story, regardless of whether a Claude Code session is mid-flight.

**Builder B** (owns the Claude Code hooks): treats slice boundaries as owned exclusively by `SessionStart`/`SessionEnd`/idle-timeout, and has the `PostToolUse` hook re-affirm (touch) the *existing* active-story slice after every tool call — including the `git checkout` tool call — because from its perspective the session never ended.

Both are individually faithful to AD-7's text (it names both triggers but never says which wins, nor what happens when both could fire from one causal action within one continuous session). The result: Builder A closes story-X's slice and opens story-Y's at time T; Builder B's next `PostToolUse` re-opens/extends story-X's slice at T+ε. Time-on-task is double-counted for one story and truncated for the other, non-deterministically depending on hook execution order.

**Tightened/new AD:**
> **AD-7a — Single pointer-mutation authority with an explicit precedence rule.** Only one hook family may write `.active-story` for a given transition: if a `git checkout` occurs while a Claude Code session is active (a live session lock file / PID marker exists), the git hook MUST NOT mutate the pointer — it only appends an informational event; the Claude Code `PostToolUse` hook (which observed the `git checkout` tool call) is the sole slice-closer/opener in that case. `git post-checkout` mutates the pointer only when no session lock is present.

---

## Finding 4 — Manifest-not-yet-written window has no defined producer behavior (SEVERITY: MEDIUM)

**Rule as written:** AD-5 says producers "read [story ID] from the manifest" and "never parse it out of a branch name or ticket key" — but it doesn't say what a producer does when `.story.yaml` doesn't exist yet (e.g., a `commit-msg` hook fires from a WIP commit made during `/opsx:explore`, before the kickoff skill has written the manifest).

**Builder A**: on missing manifest, buffers the event locally (in-memory / temp file) with `story_id: null` and backfills it once the manifest appears, later reconciling into `.story-events.jsonl`.

**Builder B**: on missing manifest, drops the event entirely (no-op) on the theory that "no story ID" means "not yet in scope," and only starts appending once the manifest exists.

Both comply with AD-5 literally (neither infers the ID from branch/ticket). But Builder A's events show up in the log with a reconciliation step the assembler must know how to handle (null-then-backfilled `story_id`), while Builder B's events are silently lost — the assembler behaves correctly against A's log and silently under-counts against B's, with no way to tell which convention a given repo followed.

**Tightened/new AD:**
> **AD-5a — Pre-manifest events are explicitly buffered, never dropped.** Producers that fire before `.story.yaml` exists MUST buffer events to a fixed pre-manifest spool (`local-store/.pending-events.jsonl`) and the kickoff skill, on writing the manifest, flushes the spool into `.story-events.jsonl` with the now-known `story_id`. Dropping pre-manifest events is non-compliant.

---

## Finding 5 — Snapshot re-emission semantics (versioning vs. revision) are ambiguous (SEVERITY: MEDIUM)

**Rule as written:** AD-3 makes the assembler "the only writer of a snapshot" and the Structural Seed names the file `snapshot.v1`, but nothing states whether `v1` is a fixed *schema* version (one mutable snapshot file per story, overwritten on every close/re-close) or a *revision* counter (a new immutable file per assembler run).

**Builder A**: treats `story-close` as re-runnable (e.g., a developer reopens a story after QA feedback) and overwrites `snapshot.v1` in place each time the assembler runs, so there is always exactly one current snapshot per story.

**Builder B**: treats every assembler run as producing a new immutable artifact for audit purposes, writing `snapshot.v1`, `snapshot.v2`, etc., and expects the central layer to take the highest revision.

Both are compliant with AD-3 ("the only writer of a snapshot" — singular writer role, not singular output count) and with `schema_version` in the envelope (which both populate identically, e.g. `1`, since it describes schema shape, not revision). A central presentation layer built against Builder A's "always exactly one file, latest wins" assumption will silently ignore Builder B's `snapshot.v2`..`vN` follow-ups (or vice versa, double-ingest them as separate stories' worth of metrics).

**Tightened/new AD:**
> **AD-3b — Snapshot re-close produces a new immutable, sequentially-numbered artifact; `schema_version` and `revision` are distinct fields.** Every assembler run appends a new file `snapshot.<schema_version>.rev<N>.json` (or equivalent) and never overwrites a prior one. The central contract (AD-3) is: consumers take the highest `revision` for a given `story_id` + `schema_version` as current; prior revisions are retained for audit, not silently superseded in place.

---

## Finding 6 — Adapter's `points` vs. AD-6 Phase-1 estimate: two legitimate "sources of truth" for the same word (SEVERITY: MEDIUM, subsumed by/related to Finding 1)

**Rule as written:** AD-4's adapter returns `{points, goal, sprint, description}` "regardless of backend" — for JIRA, `points` is presumably the JIRA story-point field (often manually set by a PM, possibly stale/pre-AI). AD-6 Phase 1 computes an *independent* estimate from `tasks.md` + openspec maturity + novelty. The spine never states the relationship between these two numbers (same field? parallel fields? does one override the other? is JIRA's `points` even meaningful post-AI, given AD-6's stated motivation that "manual point entry [is] meaningless once code is LLM-generated"?).

**Builder A**: kickoff skill writes JIRA's adapter-provided `points` into `.story.yaml` as `points_jira` purely for reference, and stores its own AD-6 Phase-1 number as `points_estimated` — two clearly distinct fields.

**Builder B**: kickoff skill, on the reasoning that AD-4 already gives it "the" points field and JIRA is the project's declared source of truth (`source_of_truth: jira`), treats the adapter's `points` as authoritative and only computes/records the AD-6 formula as a fallback when the adapter returns null — collapsing two conceptually different numbers into one field whenever JIRA has a value.

Both are compliant with AD-4 (adapter contract respected) and AD-6 (a Phase-1 figure is still "recorded" — just conditionally). But Builder B's manifests are missing the AD-6 estimate whenever JIRA has a pre-existing point value, breaking any downstream variance calculation (Finding 1) that assumes Phase-1 is *always* the AD-6-computed number.

**Tightened/new AD:**
> **AD-6a — AD-6's Phase-1 estimate is always computed and always distinct from any PM-tool-native points field.** The kickoff manifest stores both `points_source_of_truth` (verbatim from the AD-4 adapter, may be null) and `points_estimated` (always computed via the AD-6 formula, never substituted). The two are never merged into one field, in the manifest or in the snapshot.

---

## Summary Table

| # | Incompatibility | Severity | AD(s) implicated | Fix |
|---|---|---|---|---|
| 1 | `pm_metrics` vs `story_point_cost` internal ownership of points/variance | High | AD-3, AD-6 | AD-3a: field-level schema per family |
| 2 | Event `type` string collides across sources with different payloads | High | AD-1 | AD-1a: per-source `type` enum |
| 3 | Pointer double-mutation race on in-session `git checkout` | High | AD-7 | AD-7a: single mutation authority + precedence |
| 4 | Pre-manifest events dropped vs. buffered | Medium | AD-5 | AD-5a: mandatory pre-manifest spool |
| 5 | Snapshot overwrite vs. immutable revision series | Medium | AD-3 | AD-3b: revision field, append-only artifacts |
| 6 | PM-tool `points` vs. AD-6 computed estimate conflated | Medium | AD-4, AD-6 | AD-6a: always-distinct fields |

All six pairs are constructed so each builder's choice is a literal, defensible reading of the current AD text — the spine's top-level contracts (event envelope, snapshot envelope, pointer ownership, adapter interface, manifest-as-identity-source) are sound, but none of them reach far enough into internal shape, namespacing, timing precedence, or field ownership to force convergence.
