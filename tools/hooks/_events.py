#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""Shared event emitter for ALL capture hooks (git + Claude Code families).

Extracted from tools/hooks/git/_events.py in Story 2.3 (user-approved spine
amendment resolving review Issue #7): one emitter, one retry ladder, one
manifest parser. Hook scripts reach it via a one-line documented sys.path
bridge to this parent directory — the sanctioned exception to strict
single-file self-containment.

Invariants implemented here:
- AD-1: producers only append — one os.write() of a whole line to a fd opened
  with O_APPEND, so concurrent producers can never interleave a line. The log
  is never read, never rewritten.
- AD-1a: `type` is always namespaced (`git.*`, `ai.<tool>.*`); the envelope is
  the fixed `{story_id, source, type, timestamp, payload}` shape with `source`
  supplied by the calling family ("git" | "ai").
- AD-1b: events firing before `.story.yaml` exists are appended to a pending
  spool with story_id null — buffered, never dropped. Backfill is the snapshot
  assembler's job (Story 2.4), not ours.
- AD-9: a failed append retries (4 attempts total = 1 + 3 retries), then
  surfaces a visible stderr error. Never a silent loss.

Namespace note (Story 1.5 vs facts): Claude Code hooks always emit under
`ai.claude-code.*` because they ARE the Claude Code adapter — the manifest's
`ai_tool` field tells the kickoff skill and assembler which adapter family is
expected, and a declared/actual mismatch stays detectable, never falsified.

Exit-code table (AD-9 visibility is stderr in every case):
- git post-commit/post-checkout/post-merge → 1 on final failure (git ignores
  post-hook exits; honest without harm)
- git commit-msg → 0 always (non-zero aborts the developer's commit)
- claude hooks (all six) → 0 always (non-zero can block a tool call or
  disrupt the session)
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
ACTIVE_STORY_FILE = ".active-story"
ATTEMPTS = 4  # 1 initial + 3 retries (AD-9)
RETRY_DELAY_SECONDS = 0.1


def git_out(*args: str, cwd: Optional[Path] = None) -> Optional[str]:
    """Run a git query (argument list, never shell=True); any failure degrades to None.

    `cwd` defaults to the ambient process cwd (correct for git hooks, which git
    itself invokes with cwd already at the repo — AD-8). A caller addressed by an
    explicit --repo-root (e.g. the snapshot assembler) MUST pass cwd=<that root>,
    or git runs against whatever directory the process happened to start in
    instead of the repo being operated on (§3 explicit-addressing).
    """
    try:
        proc = subprocess.run(["git", *args], capture_output=True, text=True, timeout=10, cwd=cwd)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def repo_root() -> Path:
    top = git_out("rev-parse", "--show-toplevel")
    return Path(top) if top else Path.cwd()


def read_stdin_json() -> dict[str, Any]:
    """Claude Code passes hook input as JSON on stdin; tolerate empty/malformed input.

    Windows reality (the third BOM bug this project has caught): pipes prepend
    a UTF-8 BOM, and worse, Python may decode stdin with the locale codepage
    (cp1252), turning the BOM bytes into three mojibake chars — every piped
    payload then silently degrades to nulls. Reconfiguring stdin to utf-8-sig
    fixes the decode layer; the strip fallbacks cover streams that cannot
    reconfigure (e.g. StringIO in tests).
    """
    stdin = sys.stdin
    try:
        stdin.reconfigure(encoding="utf-8-sig")
    except (AttributeError, ValueError, OSError):
        pass
    try:
        raw = stdin.read()
    except OSError:
        return {}
    raw = raw.lstrip("\ufeff")
    if raw.startswith("\u00ef\u00bb\u00bf"):  # UTF-8 BOM bytes decoded as cp1252 mojibake
        raw = raw[3:]
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


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


def envelope(
    story: Optional[str], source: str, event_type: str, payload: dict[str, Any]
) -> dict[str, Any]:
    return {
        "story_id": story,
        "source": source,
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


def emit(
    source: str, event_type: str, payload: dict[str, Any], story_override: Optional[str] = None
) -> int:
    root = repo_root()
    story = story_override if story_override is not None else story_id(root)
    target = root / (EVENTS_FILE if story else PENDING_FILE)
    line = json.dumps(envelope(story, source, event_type, payload)) + "\n"
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


def write_atomic_json(path: Path, data: dict[str, Any]) -> None:
    """Temp file -> flush -> fsync -> os.replace (project-context.md §2); never an in-place write."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def read_active_story(root: Path) -> Optional[dict[str, Any]]:
    path = root / ACTIVE_STORY_FILE
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def update_active_story(root: Path, incoming_story_id: Optional[str]) -> None:
    """AD-7: one pointer tracks the currently active story.

    Changing the pointer closes the outgoing story's time slice
    (`time.slice_closed`, with `duration_seconds`) and opens a new one for the
    incoming story (`time.slice_opened`). A story-id of None (nothing to
    attribute time to) or a story-id matching the current pointer is a no-op —
    mirrors AD-1b's "buffer/skip rather than corrupt" philosophy rather than
    writing a meaningless or duplicate slice.
    """
    if incoming_story_id is None:
        return

    current = read_active_story(root)
    if current is not None and current.get("story_id") == incoming_story_id:
        return

    now = datetime.now().astimezone()
    if current is not None:
        opened_at = current.get("opened_at")
        duration_seconds = None
        if opened_at:
            try:
                duration_seconds = (now - datetime.fromisoformat(opened_at)).total_seconds()
            except ValueError:
                duration_seconds = None
        emit(
            "time",
            "time.slice_closed",
            {
                "opened_at": opened_at,
                "closed_at": now.isoformat(timespec="seconds"),
                "duration_seconds": duration_seconds,
            },
            story_override=current.get("story_id"),
        )

    write_atomic_json(
        root / ACTIVE_STORY_FILE,
        {"story_id": incoming_story_id, "opened_at": now.isoformat(timespec="seconds")},
    )
    emit(
        "time",
        "time.slice_opened",
        {"opened_at": now.isoformat(timespec="seconds")},
        story_override=incoming_story_id,
    )
