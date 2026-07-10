#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""docs-only kickoff adapter — writes the story manifest `.story.yaml`.

The docs-only backend of the AD-4 source-of-truth adapter contract
({points, goal, sprint, description}): values come from the developer's
confirmed answers (elicited by the story-kickoff skill) instead of a PM-tool
API. It doubles as the common manifest writer for the fetch-only adapters
(jira/confluence pass confirmed values here with --source-of-truth, so the
manifest records which backend supplied them). The manifest this writes is
the sole source of story identity (AD-5) —
producers read `story_id` from it and never infer identity from a branch name
or ticket key. An existing manifest is never overwritten, since a re-kickoff
would change story identity mid-story.

story_id format: `story-{YYYYMMDD}-{6 hex of uuid4}` — unique and date-sortable
with no PII; the format is a Story 1.1 decision (the architecture spine leaves
it open).

AD-6a (Story 2.6): `points_estimated` (the raw AD-6 Phase-1 estimate) is
always a distinct field from `points` (the developer-confirmed value) — never
substituted, never merged. `points_estimated` is null when no Phase-1
estimate was available at kickoff.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

MANIFEST = ".story.yaml"


def new_story_id(now: datetime) -> str:
    return f"story-{now:%Y%m%d}-{uuid.uuid4().hex[:6]}"


def clean(text: str) -> str:
    """Collapse newlines/whitespace runs so a value is always one manifest line."""
    return " ".join(text.split())


def render(manifest: dict[str, Any]) -> str:
    """Flat YAML by hand (stdlib-only rule): JSON scalars are valid YAML scalars."""
    return "".join(
        f"{key}: {'null' if value is None else json.dumps(value)}\n"
        for key, value in manifest.items()
    )


def write_atomic(path: Path, text: str) -> None:
    """Temp + flush + fsync + atomic rename, so a crash never half-writes the manifest."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--repo-root",
        required=True,
        help="repository root; the manifest is {repo-root}/.story.yaml",
    )
    p.add_argument(
        "--points",
        required=True,
        help="confirmed story points (number > 0; fractional allowed for teams that use them)",
    )
    p.add_argument(
        "--points-estimated",
        help="the raw AD-6 Phase-1 estimate (Story 2.5), distinct from --points and never "
        "substituted for it (AD-6a); omitted/null when no estimate was available",
    )
    p.add_argument("--goal", required=True, help="story goal (one line)")
    p.add_argument("--sprint", required=True, help="sprint the story belongs to")
    p.add_argument("--description", help="optional longer description")
    p.add_argument(
        "--source-of-truth",
        choices=("jira", "confluence", "docs-only"),
        default="docs-only",
        help="which backend supplied the values (default: docs-only)",
    )
    p.add_argument(
        "--ai-tool",
        default="claude-code",
        help="AI tool whose adapter captures this story's sessions (default: claude-code; "
        "lowercase token — it becomes the ai.<tool>.* event namespace)",
    )
    args = p.parse_args(argv)

    if not re.fullmatch(r"[a-z][a-z0-9-]*", args.ai_tool):
        return fail(f"--ai-tool {args.ai_tool!r} must match [a-z][a-z0-9-]*")

    try:
        points = float(args.points)
    except ValueError:
        return fail(f"--points must be a number, got {args.points!r}")
    if not 0 < points < float("inf"):  # also rejects nan: every nan comparison is false
        return fail(f"--points must be a finite number > 0, got {args.points}")
    if points.is_integer():
        points = int(points)

    points_estimated: Any = None
    if args.points_estimated is not None:
        try:
            points_estimated = float(args.points_estimated)
        except ValueError:
            return fail(f"--points-estimated must be a number, got {args.points_estimated!r}")
        if points_estimated.is_integer():
            points_estimated = int(points_estimated)

    goal = clean(args.goal)
    if not goal:
        return fail("--goal must not be empty")
    sprint = clean(args.sprint)
    if not sprint:
        return fail("--sprint must not be empty")
    description = clean(args.description) if args.description else ""

    root = Path(args.repo_root)
    if not root.is_dir():
        return fail(f"--repo-root {args.repo_root!r} is not a directory")
    path = root / MANIFEST
    if path.exists():
        return fail(f"{path} already exists; re-running kickoff would change story identity (AD-5)")

    now = datetime.now().astimezone()
    story_id = new_story_id(now)
    write_atomic(
        path,
        render(
            {
                "story_id": story_id,
                "source_of_truth": args.source_of_truth,
                "ai_tool": args.ai_tool,
                "points": points,
                "points_estimated": points_estimated,
                "goal": goal,
                "sprint": sprint,
                "description": description or None,
                "created": now.isoformat(timespec="seconds"),
            }
        ),
    )
    print(json.dumps({"ok": True, "story_yaml": str(path.resolve()), "story_id": story_id}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
