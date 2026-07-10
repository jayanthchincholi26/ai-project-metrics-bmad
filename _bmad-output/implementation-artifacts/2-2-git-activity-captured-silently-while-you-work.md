---
baseline_commit: 337b9aad860db5aabc249ce870f710098f98c28b
---

# Story 2.2: Git Activity Captured Silently While You Work

Status: review

## Story

As a developer,
I want my commits/checkouts/merges captured automatically,
so that my metrics build up without extra effort.

## Acceptance Criteria

1. **Given** the hooks from Story 2.1 are installed, **when** a developer commits, checks out, or merges, **then** a `git.*` namespaced event is atomically appended to `.story-events.jsonl` (AD-1, AD-1a) with the fixed envelope `{story_id, source, type, timestamp, payload}`.
2. Events firing before `.story.yaml` exists are buffered, never dropped (AD-1b) — they land in a pending spool with `story_id: null` for the assembler (Story 2.4) to backfill.
3. A failed append retries up to 3 times (4 attempts total), then surfaces a visible error to the developer (AD-9) — never a silent loss, and never a blocked commit.

## Tasks / Subtasks

- [x] Task 1: Shared emitter `tools/hooks/git/_events.py` (AC: 1, 2, 3)
  - [x] Sibling module imported by the four hooks via `import _events` — legal with zero machinery because Python puts the running script's directory on `sys.path`; NOT a package (no `__init__.py`), consistent with declined Issues #2/#5/#7
  - [x] `repo_root()`: `git rev-parse --show-toplevel` via `subprocess.run` with an **argument list, never `shell=True`** (§4); fallback `Path.cwd()` if git itself fails
  - [x] `git_out(*args)`: never raises — returns stdout stripped or `None` (a weird git state degrades payload fields to honest nulls, never fails the hook)
  - [x] `story_id(root)`: parse `.story.yaml` flat YAML for the `story_id` key (copy the established `parse_scalar` approach — BOM-tolerant `utf-8-sig`, paired quotes, inline comments); absent manifest → `None`
  - [x] `envelope(story_id, event_type, payload)`: exactly `{story_id, source: "git", type, timestamp, payload}` — the AD-1 consistency-convention shape, `timestamp` ISO-8601 with offset (single `datetime.now().astimezone()`)
  - [x] `append_line(path, line)`: `os.open(path, O_APPEND | O_CREAT | O_WRONLY)` + one `os.write()` of the full line + `os.close()` — the literal AD-1 single-atomic-append rule; never read-modify-write
  - [x] `emit(event_type, payload) -> int`: manifest present → append to `.story-events.jsonl` with its story_id; absent → append to `.story-events.pending.jsonl` with `story_id: null` (AC 2); retry loop of `ATTEMPTS = 4` (1 + 3 retries, AD-9) with `RETRY_DELAY_SECONDS` module constant (tests patch to 0); exhausted → loud stderr (`METRICS CAPTURE FAILED: <reason> — event lost: <type>`) and return 1
- [x] Task 2: Replace the four placeholder hooks with real producers (AC: 1, 3)
  - [x] `post-commit.py` → `git.commit`, payload `{hash, branch, message_subject}` via `git_out("rev-parse", "HEAD")`, `("rev-parse", "--abbrev-ref", "HEAD")`, `("log", "-1", "--format=%s")` — nulls when unavailable; returns `emit(...)`
  - [x] `post-checkout.py` → `git.checkout`, argv gives `{previous_head, new_head, branch_checkout}` (git passes prev/new/flag; flag "1" = branch checkout) plus current `branch`; emit ALWAYS (filtering is the assembler's concern — producers stay dumb)
  - [x] `post-merge.py` → `git.merge`, payload `{squash, branch}` (argv flag)
  - [x] `commit-msg.py` → `git.commit_msg`, payload `{message_subject}` (first line of the message file argv[1]); **returns 0 unconditionally** — a non-zero commit-msg exit aborts the developer's commit, and metrics capture must never do that (deliberate CAP-1-over-§3 trade-off; failure still surfaces on stderr via `emit`)
  - [x] All four keep `main(argv) -> int` + PEP 723 header; shims from 2.1 are untouched (they already call these files)
- [x] Task 3: Git-ignore the local-only event files (AC: 1, 2)
  - [x] `.gitignore` += `.story-events.jsonl`, `.story-events.pending.jsonl` (spine § Deployment: local-only, never committed; `.story.yaml` stays committed — do NOT ignore it)
- [x] Task 4: Tests `tests/hooks/test_git_hooks.py` (AC: 1, 2, 3)
  - [x] Load `_events` via importlib and register it in `sys.modules["_events"]` **before** loading the hook modules, so their `import _events` resolves to the same instance (no real sys.path mutation needed)
  - [x] Monkeypatch `_events.git_out`/`repo_root` — **no real git operations** (§5); `RETRY_DELAY_SECONDS = 0`
  - [x] Envelope: exactly the five keys, `source == "git"`, namespaced `type`, ISO timestamp with offset (AC 1)
  - [x] With a manifest present: event appends one valid-JSON line to `.story-events.jsonl` carrying the manifest's story_id; two events → two lines (append, not overwrite)
  - [x] Without a manifest: line lands in `.story-events.pending.jsonl` with `story_id: null`; main log untouched (AC 2)
  - [x] AD-9 boundaries (§6: test 2/3/4): append failing 2× then succeeding → success, no error; failing 3× then succeeding → success on the 4th attempt; failing 4× → stderr contains "METRICS CAPTURE FAILED", exit 1 (post-commit) — patch `_events.append_line` with a counting fake
  - [x] `commit-msg` total failure still returns 0 (commit never blocked) while stderr surfaces the loss (AC 3)
  - [x] Per-hook payloads: commit hash/branch/subject; checkout prev/new/flag parsing ("1" → true); merge squash flag; commit_msg reads only the first line of the message file
  - [x] `git_out` returning None → payload fields null, event still emitted (honest nulls, AD-10 philosophy)
- [x] Task 5: Full regression + lint + E2E (all ACs)
  - [x] `uv run pytest -q` (all suites), ruff clean
  - [x] Scratch E2E in a real throwaway git repo (allowed OUTSIDE unit tests): `git init`, run setup-hooks, write a `.story.yaml`, make a commit → assert one `git.commit_msg` + one `git.commit` line in `.story-events.jsonl`; delete manifest, commit again → lines land in pending spool

### Review Follow-ups (AI)

External LLM review (Gemini, via PR #11) triaged per project-context §9 — 2026-07-10:

- Zero functional defects; reviewer highlighted the O_APPEND single-write mechanics, degrading `git_out`, the commit-msg trade-off, and the retry ladder.
- Declined (tracked) — `parse_scalar` duplicated a third time (`resolve.py`, `jira/main.py`, `_events.py`): still the single-file-script convention (Issue #7), no new issue. **Escalation note:** the third-copy threshold named in #7 is now met, and Story 2.3 needs the *whole emitter* cross-family (claude hooks) — the extraction decision (spine-level, e.g. a sanctioned shared module with a documented import bridge, parameterized `source` field) is now due at 2.3 create-story, not later.

## Dev Notes

- **Scope:** git-side producers only. NOT here: Claude Code hooks (2.3), assembler/backfill (2.4 — the pending spool is write-only for us), `.active-story`/time slices (Epic 3 — post-checkout only *emits*; pointer updates are Story 3.1), event-log rotation/cleanup (deferred).
- **AD-1 is the heart:** producers only append; one `os.write` per line so concurrent appends (git hook + Claude hook racing) can't interleave. Never open the log for read, never rewrite it.
- **AD-1b nuance (adversarial-review history):** buffering is the producer's job; **backfilling is the assembler's** (Story 2.4). Do not flush or rewrite the pending spool here — append-only, both files.
- **AD-9 exit-code decisions:** post-commit/post-checkout/post-merge return 1 on final failure (git ignores post-hook exits — honest without harm). `commit-msg` returns 0 always because git ABORTS the commit on non-zero — a metrics failure must never break a developer's commit. This is a documented trade-off, stated in the module docstring; the stderr surfacing satisfies AD-9's visibility requirement.
- **Hook execution context:** git runs hooks with cwd at the working-tree top level, but resolve the root explicitly via `git rev-parse --show-toplevel` anyway (§3 explicit-addressing spirit; also survives `git -C` invocations). commit-msg gets the message-file path as argv[1]; post-checkout gets `<prev> <new> <flag>`; post-merge gets `<squash-flag>`.
- **UPDATE files (read-before-touch):** the four `tools/hooks/git/*.py` placeholders (2.1) — trivial `main -> 0` bodies with PEP 723 headers; everything else about them (names, shim wiring) must stay identical so `setup-hooks` needs zero changes. `tests/test_setup_hooks.py::test_all_placeholder_hooks_exit_0` asserts all 10 hook scripts' `main([]) == 0` — **that test must be updated**: the four git hooks now emit (and their no-arg `main([])` would try to emit for real!). Rework it to cover only the six remaining claude placeholders, and ensure the git-hook count/content assertions move to the new suite. `.gitignore` — read current content; append, don't reorder.
- **Sibling-import precedent:** `import _events` from a same-dir script uses Python's automatic script-dir `sys.path` entry — no package, no PYTHONPATH, no `sys.path` code. This is the sanctioned reuse pattern *within* one producer family. Story 2.3 will face the cross-family version of this (claude hooks need an emitter too) — that's the moment for the Issue #7 spine decision, not now.
- **Previous story intelligence (2.1 + Epic 1):** validate-before-write; `newline`/encoding discipline (`os.write` of `.encode("utf-8")` bytes sidesteps CRLF entirely — JSONL must be `\n`-terminated bytes); f-strings; exact hints; lenient parsing of human-edited files; grep-verify any hallucinated review finding; hypothetical-input hardening counts as improvement, not defect (metrics convention).
- **Testing:** mirror path `tests/hooks/test_git_hooks.py` (project-context §5 names exactly this path); counting-fake for retry boundaries; `capsys` for stderr surfacing; `tmp_path` with hand-written `.story.yaml` (one line: `story_id: "story-x"`) — no writer invocation needed.
- **Process:** branch `story/2.2-git-event-capture`; PR `Story 2.2: Git Activity Captured Silently While You Work` linking FR1 (CAP-1), AD-1, AD-1a, AD-1b, AD-9, NFR2 (local-first: no network anywhere in the emit path); squash-merge; epics annotation inside PR; metrics entry provisional→final; CI must be green.

### References

- [epics.md § Story 2.2](../planning-artifacts/epics.md) (lines 183–195) · [ARCHITECTURE-SPINE.md § AD-1/1a/1b, AD-9, Consistency Conventions](../planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/ARCHITECTURE-SPINE.md) · [review-adversarial.md Finding 4](../planning-artifacts/architecture/architecture-explore-jira-ai-metrics-2026-07-02/reviews/review-adversarial.md) (buffer-vs-drop history) · [project-context.md](../../project-context.md) §3 exit codes, §4 subprocess arg-lists, §5–6 testing/boundary rules · [2-1 story file](2-1-hook-installation-is-a-single-repeatable-setup-step.md) (installer contract + placeholder shapes)

## Dev Agent Record

### Agent Model Used

claude-fable-5 (create-story context engineering)

### Debug Log References

- RED: collection error, `_events.py` absent (17 tests authored first; 2.1's placeholder test reworked to claude-only per the story's regression-trap note)
- GREEN: 115/115 (was 99); ruff check/format clean
- Real-git E2E (scratch repo, outside unit tests): `git init` → setup-hooks → docs-only kickoff → `git commit` → **two real events** (`git.commit_msg` + `git.commit`) in `.story-events.jsonl` with the manifest's story_id and the true hash/branch/subject; manifest deleted → next commit's events landed in `.story-events.pending.jsonl` with `story_id: null`

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created
- `tools/hooks/git/_events.py`: the shared emitter — `git_out()` (arg-list subprocess, degrades to None, never raises), `repo_root()` via `rev-parse --show-toplevel`, manifest `story_id` reader (BOM-tolerant flat-YAML), fixed 5-key envelope, `append_line()` as the literal AD-1 append (`os.open(O_APPEND|O_CREAT|O_WRONLY)` + one `os.write` of the whole line), `emit()` with the AD-1b pending-spool routing and the AD-9 4-attempt retry → loud `METRICS CAPTURE FAILED` stderr. Sibling `import _events` (script-dir sys.path) — no packaging.
- Four placeholders became real producers: `git.commit` (hash/branch/subject), `git.checkout` (prev/new/branch-flag, emits unconditionally — filtering is the consumer's job), `git.merge` (squash flag), `git.commit_msg` (first non-comment line; **returns 0 unconditionally** — the documented CAP-1-over-§3 trade-off since a non-zero commit-msg exit aborts the developer's commit).
- `.gitignore` += the two event files; `.story.yaml` deliberately stays committed.
- AC→test traceability: AC 1 → envelope/namespace/append/payload tests + real-git E2E; AC 2 → pending-spool tests + E2E manifest-deleted leg; AC 3 → §6 boundary tests at attempts 2/3/4 + commit-msg-never-blocks test.
- 2.1's `test_all_placeholder_hooks_exit_0` reworked to `test_all_claude_placeholder_hooks_exit_0` (6 files) exactly as the story's UPDATE-file analysis flagged.

### Change Log

- 2026-07-10: Story 2.2 implemented — shared emitter (AD-1/1a/1b/9), four real git producers, event files git-ignored. 17 new tests (115 total) + real-git E2E. Status → review.
- 2026-07-10: Gemini review of PR #11 — zero defects; parse_scalar duplication acknowledged (Issue #7, third copy) with the extraction decision escalated to Story 2.3 where the emitter itself goes cross-family. No code changes.

### File List

- tools/hooks/git/_events.py (new)
- tools/hooks/git/post-commit.py, post-checkout.py, post-merge.py, commit-msg.py (modified — placeholders → real producers)
- tests/hooks/test_git_hooks.py (new)
- tests/test_setup_hooks.py (modified — placeholder test reworked to claude-only)
- .gitignore (modified — event log + pending spool)
- _bmad-output/implementation-artifacts/2-2-git-activity-captured-silently-while-you-work.md (modified — this story file)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — status transitions + last_updated)
- _bmad-output/planning-artifacts/epics.md (modified — §12 annotation, inside PR)
