# Review Bugs — Story {N}.{M}: {Story Title}

**Story:** {N}.{M} — {Story Title}
**Type:** UI / API
**Reviewer:** Claude Opus 4.8 / Claude Sonnet 5 / Gemini 2.5 Pro
**PR Branch:** feature/m{M}-story-{N}.{M}-{short-name}
**Review Date:** {YYYY-MM-DD}
**Status:** Open / Resolved

---

## Bug {N}.{M}-R{seq}: {Short bug title}

**Severity:** S1 Critical / S2 High / S3 Medium / S4 Low
**Complexity:** C1 Simple / C2 Moderate / C3 Complex
**File:** {path/to/file.ts or Controller.cs}
**Line:** {line number if applicable}
**Status:** Open / Fixed

### Reviewer Finding
{Exact finding raised by the LLM reviewer — what issue was identified}

### Code in Question
```
{Paste the relevant code snippet the reviewer flagged}
```

### Why It's a Problem
{Reviewer's explanation — security risk, logic error, AC not met, performance issue, etc.}

### Fix Applied
{What was changed to resolve the review finding}

### Verification
{How confirmed — re-review passed, test added, manual check}

---

<!-- Repeat Bug block for each review finding in this story -->
