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
engineering_metrics, story_point_cost, token_cost}. story_point_cost is the
sole home of {phase1_points, phase2_points, variance} — null today (honest
nulls, never zeros) until Stories 2.5/2.6 compute them.

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
import sys
from pathlib import Path
from typing import Any, Optional

EVENTS_FILE = ".story-events.jsonl"
PENDING_FILE = ".story-events.pending.jsonl"
MANIFEST = ".story.yaml"
SNAPSHOTS_DIR = "snapshots"
SCHEMA_VERSION = 1


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


def read_manifest(path: Path) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, raw = stripped.split(":", 1)
        manifest[key.strip()] = parse_scalar(raw)
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
        "story_point_cost": {"phase1_points": None, "phase2_points": None, "variance": None},
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
