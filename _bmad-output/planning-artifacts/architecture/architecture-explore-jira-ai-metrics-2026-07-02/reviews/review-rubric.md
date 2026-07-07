# Spine Review — ai-engineering-metrics-capture (rubric-based)

Reviewed: ARCHITECTURE-SPINE.md (2026-07-02)

## Verdict

Solid, well-scoped spine for the capture side, but it is silent on the entire operational/environmental envelope and leaves one real concurrency divergence point unfixed — not ready to call "final" without addressing those.

## 1. Does it fix the real divergence points for the level below? Any missed?

Covered well: producer/writer separation (AD-1), local-vs-network (AD-2), capture↔presentation contract (AD-3), PM-tool abstraction (AD-4), story-identity source (AD-5), estimation method (AD-6), time-tracking pointer (AD-7).

Missed divergence points:

- **Concurrent-append safety on `.story-events.jsonl` is not actually fixed.** AD-1 says "every producer only appends" — this prevents *shared mutable state* races, but three independent processes (a git hook, a Claude Code hook, and the CLI wrapper) can still fire near-simultaneously (e.g., `post-commit` firing while a Claude Code `PostToolUse` hook is writing) and interleave partial line writes to the same file without a specified append mode (`O_APPEND`/flock/single-writer-queue). "Append-only" describes intent, not a mechanism that guarantees atomic line writes across processes. This is a real divergence point (each producer author could pick a different write strategy) and is currently unaddressed.
- **Hook installation/distribution across developer machines is undecided.** `.git/hooks/` scripts and `.claude/hooks/` are not synced by git by default (`.git/hooks` isn't versioned; `.claude/hooks` may or may not be checked in depending on repo conventions). Nothing in the spine says how every contributor's machine ends up with the same hook versions installed — left to chance, two developers' repos could silently diverge (one has the hook, one doesn't; or stale versions). This is exactly the class of thing a spine should pin down.
- **Adapter credentials/auth is unaddressed.** AD-4 fixes the *interface* shape (`{points, goal, sprint, description}`) but not where a JIRA API token or Confluence credential lives (env var? project config file risking a committed secret? OS keychain?). Three adapter implementations could each invent their own auth convention.

## 2. Is every AD's Rule enforceable and does it actually prevent its stated divergence?

- **AD-1**: Enforceable as a code-review/lint rule ("producers may only append"), and does prevent the stated corruption-via-shared-mutable-file risk. However, as noted above, "append" alone does not prevent *interleaved* corruption from concurrent writers — the rule closes the "direct write to `.story.yaml`" divergence but leaves a narrower concurrent-append divergence open. Recommend tightening the rule to specify the write mechanism (e.g., "each append is a single `O_APPEND` write of one newline-terminated JSON line; no producer holds the file open across multiple lines").
- **AD-2**: Enforceable, clear, prevents network/daemon dependency creep. Fine.
- **AD-3**: Enforceable and effective — schema-versioned snapshot is a real contract boundary; raw events explicitly excluded from being load-bearing. Fine.
- **AD-4**: The `{points, goal, sprint, description}` interface plus one-time config is enforceable and prevents hard-coded-JIRA divergence. Fine, modulo the auth gap above.
- **AD-5**: Clear, checkable (grep for branch-name/ticket-key parsing in producer code), prevents the stated divergence. Fine.
- **AD-6**: The Rule is really a detailed algorithm spec, not just an invariant — that's appropriate at this altitude since it's the one place where "silently overwritten" is the specific failure being prevented, and the two-phase-recorded-not-collapsed rule does prevent that. Enforceable via a data-shape check (both phase values must be present in the record). Fine, though it is doing more prescriptive work than a typical AD; acceptable given how easy this is to get wrong.
- **AD-7**: Enforceable (pointer file + hook wiring is testable), and does prevent file-edit-based time inference. It explicitly flags its own scope hole (multi-story-per-branch) as an open risk rather than silently ignoring it — good practice — but see Deferred section below on whether that gap is a live incompatibility risk rather than a truly safe deferral.

## 3. Could anything under Deferred let two units diverge incompatibly?

- **"Manual-override path for the active-story pointer"**: This is deferred as a future feature, but the *absence* of an override is not just a missing nice-to-have — it means any project/team that doesn't strictly follow branch-per-story will silently produce wrong time-on-task data with no detection mechanism, and different teams may independently invent ad hoc workarounds (e.g., manually editing `.active-story`) that diverge. Recommend at minimum an open question or guard: detect (and warn/error on) multi-story-per-branch situations rather than deferring silently, since two teams "solving" this informally in different ways is exactly the incompatible-divergence AD-7 exists to prevent.
- **Central presentation layer** deferral is safe — only its input contract (AD-3 snapshot) is fixed, tech/hosting genuinely can be decided later without affecting capture-side units.
- **Snapshot schema exact shape / migration strategy** deferral is reasonably safe since `v1` and `schema_version` are already in the envelope (Consistency Conventions), giving a forward-compatible seam.
- **Story-point weight tuning** deferral is safe — it's a calibration/data question, not a structural one; the two-phase mechanism (AD-6) is fixed regardless of the specific weights.

## 4. Named tech verified-current / flag vague items

- "current Claude Code hooks feature set" (Stack table) is explicitly non-pinned — flagged by the author's own wording as a moving target, but that also means it's unverifiable as written. At minimum the specific hook names actually used (`SessionStart`, `SessionEnd`, `PreToolUse`, `PostToolUse`, `Stop`, `UserPromptSubmit`) should be checked against the current Claude Code hooks documentation for exact event names and payload shape guarantees before build starts — these are used load-bearingly in AD-7 and AD-6 Phase 2 (e.g., counting `UserPromptSubmit` events as a proxy for human review cycles). No version/date pin is given for "current," so this will drift silently.
- git hooks (`post-commit`, `post-checkout`, `post-merge`, `commit-msg`) — these are standard, real git hook names; no concern.
- openspec/speckit CLI — described as "existing project tooling, wrapped not modified," not a new external dependency; fine, nothing to verify.
- No pinned versions given at all in the Stack table (no Claude Code version, no minimum git version) — for a spine marked `status: final`, an unpinned dependency table is a gap.

## 5. Dimension coverage — decided / deferred / open question, especially operational envelope

Decided: data flow/paradigm, producer/writer boundaries, local storage layout, story identity, snapshot contract, PM-tool abstraction, story-point estimation, time-tracking mechanism.

**Left entirely silent (not decided, not deferred, not flagged as an open question) — the operational/environmental envelope:**

- **Deployment & environments**: no mention of how this ships to a developer's machine, whether it targets a single OS or must be cross-platform (git hooks are typically POSIX shell — is Windows/PowerShell support required, given this is being authored in a Windows environment?), no dev/staging/prod distinction (arguably N/A for a local-only capture layer, but that should be stated, not left implicit).
- **Infra/provider strategy**: N/A is plausible for the capture side (everything is local files), but the spine should say so explicitly rather than leaving the reader to infer it — especially since the *deferred* central layer will need one, and this document doesn't even flag that as an upcoming decision point.
- **Operations**: no mention of failure/observability behavviour — what happens when a hook script itself errors (does it fail the git commit? fail silently? is failure ever surfaced to the developer)? No mention of log rotation/size bounds for `.story-events.jsonl` over a long-running story, no mention of how `.gitignore` entries for the local-only files (`.story-events.jsonl`, `.active-story`) get established on a fresh clone (a missed `.gitignore` line is exactly the kind of thing that causes one developer's repo to diverge from another's, e.g. by accidentally committing event logs).
- **Secrets/credentials handling** (adapters) — noted above under point 1, also an operational-envelope gap.

This is the clearest rubric miss: the whole operational/environmental envelope dimension is un-decided and un-flagged, not merely deferred with a rationale. At minimum it should be captured as an explicit Open Question so it isn't lost, since the checklist calls this out as especially important and the document is otherwise thorough enough that its absence reads as an oversight rather than a deliberate scope cut.

## Summary of Findings by Severity

1. **[High]** Operational/environmental envelope (deployment/OS targets, hook installation/distribution, failure handling, `.gitignore` setup, secrets handling) is entirely unaddressed — not decided, not deferred, not even an open question.
2. **[Medium]** AD-1's "append-only" rule does not actually guarantee atomic/non-interleaved writes across three concurrent producer processes — the concurrency-safety mechanism itself is unspecified, leaving room for exactly the kind of divergent implementation choices ADs exist to prevent.
3. **[Medium]** Hook script distribution/versioning across developer machines is unaddressed (`.git/hooks` isn't git-versioned by default) — two developers could silently run different hook versions or lack them entirely.
4. **[Medium]** AD-4's adapter interface fixes the data shape but not credential/auth handling for JIRA/Confluence — a real divergence point left open.
5. **[Low]** Stack table has no pinned versions ("current Claude Code hooks feature set" is explicitly unpinned) despite `status: final`; the specific hook names used are load-bearing in AD-6/AD-7 and should be verified against current docs before build.
