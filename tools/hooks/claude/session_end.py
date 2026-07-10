#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""session_end capture hook - emits `ai.claude-code.session_end` (AD-1a/AD-10) via the shared emitter.

Returns 0 unconditionally: a non-zero Claude Code hook exit can block the
tool call or disrupt the session, and metrics capture must never do that
(the commit-msg precedent, extended). AD-9 visibility comes from the
emitter's stderr surfacing.

AD-10 showcase: hooks expose no per-session token usage, so token_cost is
emitted null-with-reason - a real null a dashboard must never read as zero.

AD-7: a session-level slice only closes on SessionEnd (Story 3.3) - closes
whatever story the active-story pointer currently names via
close_active_story_slice(), then clears the live-session marker."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)  # bridge to the shared emitter (spine-sanctioned, Story 2.3)
import _events


def main(argv: list[str] | None = None) -> int:
    data = _events.read_stdin_json()
    _events.emit(
        "ai",
        "ai.claude-code.session_end",
        {
            "session_id": data.get("session_id"),
            "token_cost": None,
            "token_cost_reason": "claude-code hooks do not report token usage",
        },
    )
    root = _events.repo_root()
    _events.close_active_story_slice(root)
    _events.mark_session_inactive(root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
