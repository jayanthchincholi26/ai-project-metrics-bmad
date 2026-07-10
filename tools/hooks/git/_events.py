#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""Shared event emitter for the git-side capture hooks (Story 2.2).

Sibling module imported by the four hook scripts via `import _events` — legal
with zero machinery because Python puts the running script's directory on
sys.path. Not a package; the sanctioned reuse pattern within one producer
family (see Issues #2/#5/#7).

Invariants implemented here:
- AD-1: producers only append — one os.write() of a whole line to a fd opened
  with O_APPEND, so concurrent producers can never interleave a line. The log
  is never read, never rewritten.
- AD-1a: `type` is always namespaced (`git.*`); the envelope is the fixed
  `{story_id, source, type, timestamp, payload}` shape.
- AD-1b: events firing before `.story.yaml` exists are appended to a pending
  spool with story_id null — buffered, never dropped. Backfill is the snapshot
  assembler's job (Story 2.4), not ours.
- AD-9: a failed append retries (4 attempts total = 1 + 3 retries), then
  surfaces a visible stderr error. Never a silent loss.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

EVENTS_FILE = ".story-events.jsonl"
PENDING_FILE = ".story-events.pending.jsonl"
MANIFEST = ".story.yaml"
ATTEMPTS = 4  # 1 initial + 3 retries (AD-9)
RETRY_DELAY_SECONDS = 0.1


def git_out(*args: str) -> Optional[str]:
    """Run a git query (argument list, never shell=True); any failure degrades to None."""
    try:
        proc = subprocess.run(["git", *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def repo_root() -> Path:
    top = git_out("rev-parse", "--show-toplevel")
    return Path(top) if top else Path.cwd()


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


def story_id(root: Path) -> Optional[str]:
    """The manifest is the sole source of story identity (AD-5); absent → None."""
    path = root / MANIFEST
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if stripped.startswith("story_id") and ":" in stripped:
            value = parse_scalar(stripped.split(":", 1)[1])
            return value or None
    return None


def envelope(story: Optional[str], event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "story_id": story,
        "source": "git",
        "type": event_type,
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "payload": payload,
    }


def append_line(path: Path, line: str) -> None:
    """The literal AD-1 append: O_APPEND fd, one os.write of the whole line."""
    fd = os.open(str(path), os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)


def emit(event_type: str, payload: dict[str, Any]) -> int:
    root = repo_root()
    story = story_id(root)
    target = root / (EVENTS_FILE if story else PENDING_FILE)
    line = json.dumps(envelope(story, event_type, payload)) + "\n"
    last_error: Optional[BaseException] = None
    for attempt in range(ATTEMPTS):
        try:
            append_line(target, line)
            return 0
        except OSError as exc:
            last_error = exc
            if attempt < ATTEMPTS - 1:
                time.sleep(RETRY_DELAY_SECONDS)
    print(
        f"METRICS CAPTURE FAILED: {last_error} — event lost: {event_type}",
        file=sys.stderr,
    )
    return 1
