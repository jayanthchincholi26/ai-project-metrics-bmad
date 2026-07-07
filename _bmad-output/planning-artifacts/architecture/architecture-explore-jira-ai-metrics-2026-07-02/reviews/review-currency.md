# Currency / Reality-Check Review — ARCHITECTURE-SPINE.md

**Reviewed:** `_bmad-output/planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md`
**Method:** Web verification (docs.claude.com hooks reference) via a claude-code-guide sub-agent, plus reasoning against well-established git internals.
**Date of check:** 2026-07-06

## Verdict

Most named technologies exist and are correctly named, but one structural claim about Claude Code hooks is factually wrong and will not work if implemented as written, and the stack table's hook list is presented as complete when it is a curated subset of a much larger event surface — worth an explicit caveat.

## Findings

### 1. INCORRECT — Structural Seed's hook layout does not match how Claude Code hooks are actually configured (Severity: High)

- **Location:** Structural Seed block, `.claude/hooks/` line ("`PreToolUse / PostToolUse / Stop / SessionStart / SessionEnd / UserPromptSubmit`" implying a directory-per-event layout).
- **Reality:** Claude Code hooks are registered declaratively in `settings.json` (project or user-level) under a `hooks` key, structured as `hooks > <EventName> > [matcher groups] > hooks > [handler commands]`. The `.claude/hooks/` directory (if used) holds hook *script files* referenced from that JSON — it is not auto-discovered by event-name subfolders.
- **Impact:** If AD-7's "git `post-checkout` hook, Claude Code `SessionStart`/`PostToolUse`" mechanism, and the Structural Seed's directory layout, are taken literally by an implementer, the hooks will silently never fire — there is no settings.json wiring shown anywhere in the spine. This is a build-blocking gap, not just a cosmetic one.
- **Source:** https://code.claude.com/docs/en/hooks.md (confirmed via web search 2026-07-06).
- **Recommendation:** Add an explicit note (or a companion doc) that hook activation requires `settings.json` entries pointing at the scripts under `.claude/hooks/`, and that the directory names are organizational only, not event-discovery mechanisms.

### 2. STALE / INCOMPLETE PRESENTATION — Stack table's Claude Code hook list reads as exhaustive but is a subset (Severity: Low)

- **Location:** Stack table, row "Claude Code hooks (`SessionStart`, `SessionEnd`, `PreToolUse`, `PostToolUse`, `Stop`, `UserPromptSubmit`)".
- **Reality:** These six event names are current and correctly spelled (verified against current docs), but Claude Code's actual hook surface is much larger (includes `SubagentStop`, `PreCompact`, `PostCompact`, `Notification`, `PermissionRequest`/`PermissionDenied`, `PostToolUseFailure`, `TaskCreated`/`TaskCompleted`, etc.).
- **Impact:** Not incorrect, but the phrasing "current Claude Code hooks feature set" in the Version column implies this is the whole feature set, which could mislead an implementer scanning for a specific event later (e.g. for idle/compaction-aware time tracking, `PreCompact` might have been relevant to AD-7's idle-timeout logic).
- **Recommendation:** Reword to "subset of Claude Code's hook events, selected for this use case" to avoid implying completeness.

### 3. VERIFIED — openspec / speckit CLI tools are real and correctly named (Severity: None)

- **Location:** Stack table row "openspec/speckit CLI"; also referenced throughout (AD-1, AD-6, Structural Seed `opsx-wrapper/`).
- **Reality:** OpenSpec (github.com/Fission-AI/OpenSpec) and Spec Kit (github.com/github/spec-kit) are both real, currently maintained spec-driven-development tooling projects. Naming matches.
- **No action needed**, beyond noting the doc correctly hedges these as "existing project tooling, wrapped not modified" rather than asserting internal details about them.

### 4. VERIFIED (common knowledge, but confirmed) — Named git hooks are real, standard git hook points (Severity: None)

- **Location:** Stack table row "git hooks (`post-commit`, `post-checkout`, `post-merge`, `commit-msg`)"; Structural Seed `.git/hooks/` block; AD-7.
- **Reality:** `post-commit`, `post-checkout`, `post-merge`, and `commit-msg` are all standard, long-stable native git hook names with no version dependency (git hooks are not versioned/deprecated the way SaaS APIs are). No currency risk here — these have been stable for well over a decade and are not the kind of claim that goes stale.
- **No action needed.**

### 5. UNVERIFIED BY DESIGN (correctly deferred) — Central presentation layer stack (Severity: None — flagged as already deferred)

- **Location:** "Deferred" section, first bullet.
- **Note:** The document explicitly defers technology choice for the central presentation layer rather than asserting a stack, so there is nothing to fact-check here. This is good practice and is called out only to confirm the review covered it and found no unverified assertion.

## Summary Table

| # | Claim | Status | Severity |
|---|---|---|---|
| 1 | `.claude/hooks/` directory-per-event structure activates hooks | INCORRECT | High |
| 2 | Six listed Claude Code hooks = "current feature set" | STALE/INCOMPLETE PHRASING | Low |
| 3 | openspec/speckit exist and are named correctly | VERIFIED | — |
| 4 | git hook names (post-commit/post-checkout/post-merge/commit-msg) | VERIFIED | — |
| 5 | Central presentation layer stack | N/A — correctly deferred | — |

## Recommended Follow-ups Before Implementation

1. Add a companion note (or amend AD-7 / Structural Seed) clarifying that Claude Code hooks require `settings.json` registration, with a minimal example of the `hooks` JSON block wiring `SessionStart`/`PostToolUse`/etc. to the scripts under `.claude/hooks/`.
2. Soften the Stack table's Claude Code row to avoid implying the six listed events are the entirety of what Claude Code offers.
3. No changes needed for git hooks or openspec/speckit naming/version claims.
