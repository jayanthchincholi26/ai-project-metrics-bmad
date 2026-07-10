#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""Snapshot assembler — reduces the event log into an immutable versioned snapshot.

The pipeline's ONLY reducer (AD-3): the single component allowed to read
`.story-events.jsonl` and to resolve the AD-1b pending spool. Producers stay
append-only; only the snapshot ever crosses to a central layer, never the raw
log (NFR3).

Envelope (AD-3a, fixed): {schema_version, story_id, revision, pm_metrics,
engineering_metrics, story_point_cost, token_cost}. story_point_cost holds
{phase1_points, phase2_points, variance, reduced_confidence,
reduced_confidence_reasons} (Stories 2.5/2.6).

Phase-1 (Story 2.5) is read back from the manifest's `points_estimated`
(AD-6a: always distinct from the developer-confirmed `points`, written by
Story 2.5's kickoff-time estimator, never recomputed here).

Phase-2 (Story 2.6), computed at close from the event log:
- review_cycles = max(0, ai.*.prompt event count - 1) — AD-6's literal
  "UserPromptSubmit follow-up count", a direct mapping onto our own prompt
  events, no invention needed.
- decision_events = 0, always, today: no producer in this pipeline emits an
  "agent-narrated decision" event (Stories 2.2/2.3 fixed the full producer
  set) — rather than faking this signal, story_point_cost.reduced_confidence
  is set true with a stated reason (AD-10's vocabulary, applied here to a
  same-tool gap rather than a cross-tool one).
- verification/context files: for each git.commit event's hash, bridge-import
  the shared git_out() helper from tools/hooks/_events.py (reused, not
  reimplemented — subprocess argument-list safety, §4) and run
  `git show --stat --format= <hash>`; a path containing "test" (case
  insensitive) counts as a verification file, everything else as a context
  file, deduped by path across all commits. AD-6 asks for sub-type weights
  (unit/integration/manual/perf) this event schema cannot distinguish; a
  uniform x1 (integration-equivalent) is applied instead — a documented
  simplification, not a fabricated classifier. A commit whose hash git can't
  resolve (no git, rewritten history, etc.) contributes 0 and is skipped
  silently — it still counts in engineering_metrics.commits.
- Combination (AD-6 lists these four inputs but gives no arithmetic — this
  formula is this story's own documented invention, exactly like Phase-1's
  volatility fill was): phase2_points = round(review_cycles*1.0 +
  verification_files*1.0 + context_files*0.2). decision_events contributes 0.
- variance = phase2_points - phase1_points, only when phase1_points is not
  null (honest null otherwise — can't diff against nothing).

Revisions (AD-3b): snapshots/{story_id}.v{schema}.rev{N}.json, N = max+1;
files are created exclusively ("x" mode) — an existing revision is refused,
never replaced. Consumers take the highest revision as current; priors are
audit history. Snapshot files are committed artifacts (spine § Deployment).

Backfill (AD-1b): pending-spool events get the manifest's story_id, join the
reduction, are appended to the main log, and the spool is deleted — after a
successful snapshot write, so a failed close never consumes the buffer.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "hooks")
)  # bridge to the shared git_out() helper (spine-sanctioned, reused not reimplemented)
import _events

EVENTS_FILE = ".story-events.jsonl"
PENDING_FILE = ".story-events.pending.jsonl"
MANIFEST = ".story.yaml"
SNAPSHOTS_DIR = "snapshots"
SCHEMA_VERSION = 1
DECISION_EVENTS_REASON = (
    "no decision-narration producer implemented (out of scope through Story 2.6)"
)
STAT_LINE = re.compile(r"^\s*(.+?)\s+\|\s+\d+")


def parse_scalar(raw: str) -> str:
    """One flat-YAML scalar: paired quotes shield `#`; bare values end at ` #`."""
    value = raw.strip()
    if value[:1] in ("'", '"'):
        quote, body = value[0], value[1:]
        end = body.find(quote)
        return body[:end] if end != -1 else body
    if value.startswith("#"):
        return ""
    if " #" in value:
        value = value.split(" #", 1)[0].strip()
    return value


def read_manifest(path: Path) -> dict[str, Any]:
    """Values are strings, except the bare (unquoted) YAML `null` token, which the
    writer (docs-only/main.py's render()) uses to represent Python None — read back
    as None here too, or any nullable numeric field (e.g. points_estimated) would
    receive the literal string "null" instead."""
    manifest: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, raw = stripped.split(":", 1)
        raw_value = raw.strip()
        value = parse_scalar(raw)
        is_bare_null = value == "null" and raw_value[:1] not in ("'", '"')
        manifest[key.strip()] = None if is_bare_null else value
    return manifest


def as_number(value: Optional[str]) -> Any:
    if value is None:
        return None
    try:
        number = float(value)
    except ValueError:
        return value
    return int(number) if number.is_integer() else number


def read_jsonl(path: Path) -> "tuple[list[dict], int]":
    """Return (valid events, malformed line count); a missing file is an empty log."""
    if not path.is_file():
        return [], 0
    events: list[dict] = []
    malformed = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if isinstance(parsed, dict):
            events.append(parsed)
        else:
            malformed += 1
    return events, malformed


def reduce_events(events: "list[dict]") -> dict[str, Any]:
    def count(predicate) -> int:
        return sum(1 for e in events if predicate(e.get("type") or ""))

    timestamps = sorted(e["timestamp"] for e in events if isinstance(e.get("timestamp"), str))
    return {
        "commits": count(lambda t: t == "git.commit"),
        "checkouts": count(lambda t: t == "git.checkout"),
        "merges": count(lambda t: t == "git.merge"),
        "ai_sessions": count(lambda t: t.startswith("ai.") and t.endswith(".session_start")),
        "tool_uses": count(lambda t: t.startswith("ai.") and t.endswith(".tool_use")),
        "prompts": count(lambda t: t.startswith("ai.") and t.endswith(".prompt")),
        "event_count": len(events),
        # ISO-8601 strings with a fixed local offset sort correctly lexicographically
        # for same-offset producers; cross-timezone teams are out of pilot scope.
        "first_event_at": timestamps[0] if timestamps else None,
        "last_event_at": timestamps[-1] if timestamps else None,
    }


def token_cost_of(events: "list[dict]") -> dict[str, Any]:
    session_ends = [
        e
        for e in events
        if (e.get("type") or "").startswith("ai.") and e["type"].endswith(".session_end")
    ]
    costs = [e.get("payload", {}).get("token_cost") for e in session_ends]
    known = [c for c in costs if isinstance(c, (int, float))]
    reasons = [
        e.get("payload", {}).get("token_cost_reason")
        for e in session_ends
        if e.get("payload", {}).get("token_cost_reason")
    ]
    return {
        "total_tokens": sum(known) if known else None,
        "reason": reasons[0] if reasons else None,
        "sessions_observed": len(session_ends),
    }


def touched_files(root: Path, hash_: str) -> "list[str]":
    """Files changed by one commit, via the shared git_out() helper; [] if unresolvable.

    cwd=root is required (not the default None) — the assembler is explicitly
    addressed by --repo-root, which may differ from the ambient process cwd
    (§3); without pinning cwd, `git show` would run against the wrong repo.
    """
    output = _events.git_out("show", "--stat", "--format=", hash_, cwd=root)
    if not output:
        return []
    paths = []
    for line in output.splitlines():
        if "|" not in line or "changed" in line:
            continue
        match = STAT_LINE.match(line)
        if match:
            paths.append(match.group(1).strip())
    return paths


def verification_and_context_counts(root: Path, events: "list[dict]") -> "tuple[int, int]":
    """Union of files touched across all git.commit hashes, classified test vs. context."""
    seen: set[str] = set()
    for e in events:
        if e.get("type") != "git.commit":
            continue
        hash_ = e.get("payload", {}).get("hash")
        if not hash_:
            continue
        seen.update(touched_files(root, hash_))
    verification = sum(1 for path in seen if "test" in path.lower())
    context = len(seen) - verification
    return verification, context


def review_cycles_of(events: "list[dict]") -> int:
    prompts = sum(
        1
        for e in events
        if (e.get("type") or "").startswith("ai.") and e["type"].endswith(".prompt")
    )
    return max(0, prompts - 1)


def story_point_cost_of(
    root: Path, events: "list[dict]", manifest: dict[str, str]
) -> dict[str, Any]:
    phase1_points = as_number(manifest.get("points_estimated"))

    review_cycles = review_cycles_of(events)
    verification_files, context_files = verification_and_context_counts(root, events)
    decision_events = 0  # always, today — see DECISION_EVENTS_REASON

    phase2_points = round(
        review_cycles * 1.0 + verification_files * 1.0 + context_files * 0.2 + decision_events
    )
    variance = (phase2_points - phase1_points) if phase1_points is not None else None

    return {
        "phase1_points": phase1_points,
        "phase2_points": phase2_points,
        "variance": variance,
        "reduced_confidence": True,
        "reduced_confidence_reasons": [DECISION_EVENTS_REASON],
    }


def next_revision(snapshots: Path, story_id: str) -> int:
    prefix = f"{story_id}.v{SCHEMA_VERSION}.rev"
    highest = 0
    if snapshots.is_dir():
        for path in snapshots.glob(f"{prefix}*.json"):
            suffix = path.name[len(prefix) : -len(".json")]
            if suffix.isdigit():
                highest = max(highest, int(suffix))
    return highest + 1


def append_line(path: Path, line: str) -> None:
    fd = os.open(str(path), os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 2


def main(argv: "list[str] | None" = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--repo-root", required=True, help="repository root of the story being closed")
    args = p.parse_args(argv)

    root = Path(args.repo_root)
    if not root.is_dir():
        return fail(f"--repo-root {args.repo_root!r} is not a directory")
    manifest_path = root / MANIFEST
    if not manifest_path.is_file():
        return fail("no .story.yaml found — kick off the story before closing it (AD-5)")
    manifest = read_manifest(manifest_path)
    story = manifest.get("story_id")
    if not story:
        return fail(f"{manifest_path} carries no story_id")

    log_events, malformed_main = read_jsonl(root / EVENTS_FILE)
    pending_events, malformed_pending = read_jsonl(root / PENDING_FILE)
    malformed = malformed_main + malformed_pending
    if malformed:
        print(f"warning: skipped {malformed} malformed event line(s)", file=sys.stderr)

    for pending in pending_events:
        pending["story_id"] = story
    ours = [e for e in log_events if e.get("story_id") == story] + pending_events

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "story_id": story,
        "revision": next_revision(root / SNAPSHOTS_DIR, story),
        "pm_metrics": {
            "points": as_number(manifest.get("points")),
            "goal": manifest.get("goal"),
            "sprint": manifest.get("sprint"),
            "source_of_truth": manifest.get("source_of_truth"),
            "ai_tool": manifest.get("ai_tool"),
            "created": manifest.get("created"),
        },
        "engineering_metrics": reduce_events(ours),
        "story_point_cost": story_point_cost_of(root, ours, manifest),
        "token_cost": token_cost_of(ours),
    }

    snapshots_dir = root / SNAPSHOTS_DIR
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    target = snapshots_dir / f"{story}.v{SCHEMA_VERSION}.rev{snapshot['revision']}.json"
    try:
        with open(target, "x", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(snapshot, indent=2) + "\n")
            f.flush()
            os.fsync(f.fileno())
    except FileExistsError:
        return fail(
            f"{target} already exists — revisions are immutable (AD-3), refusing to replace"
        )

    if pending_events:
        main_log = root / EVENTS_FILE
        for pending in pending_events:
            append_line(main_log, json.dumps(pending) + "\n")
        (root / PENDING_FILE).unlink()

    print(
        json.dumps(
            {
                "ok": True,
                "snapshot": str(target.resolve()),
                "revision": snapshot["revision"],
                "events_reduced": len(ours),
                "pending_backfilled": len(pending_events),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
