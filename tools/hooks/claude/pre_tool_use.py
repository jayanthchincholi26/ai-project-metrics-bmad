#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""pre_tool_use capture hook - emits `ai.claude-code.tool_start` (AD-1a/AD-10) via the shared emitter.

Returns 0 unconditionally: a non-zero Claude Code hook exit can block the
tool call or disrupt the session, and metrics capture must never do that
(the commit-msg precedent, extended). AD-9 visibility comes from the
emitter's stderr surfacing.

Privacy guard: tool_input is NEVER emitted - tool arguments can carry secrets.

Story 5.8: also rewrites a matched Bash command (opt-in via
`.story-config.yaml`'s `test_commands`/`build_commands`, same patterns Story
5.4 introduced) to append a harmless `; printf '\\n%s:%s\\n' MARKER "$?"`
suffix, via Claude Code's documented PreToolUse `updatedInput` mechanism.
This doesn't change what the command does - it only makes its exit code
observable in stdout, which post_tool_use.py then parses back out. Needed
because Claude Code's PostToolUse payload never exposes a structured exit
code for Bash (a confirmed platform gap, not something this project's own
code can fix around any other way - see _events.py's DEFECT_EXIT_MARKER
docstring). Absent config = unchanged behavior (no rewrite ever happens)."""

from __future__ import annotations

import json
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
        "ai.claude-code.tool_start",
        {"session_id": data.get("session_id"), "tool_name": data.get("tool_name")},
    )

    if data.get("tool_name") == "Bash":
        tool_input = data.get("tool_input") or {}
        command = tool_input.get("command", "")
        config = _events.read_story_config(_events.repo_root())
        patterns = _events.split_config_patterns(
            config.get("test_commands", "")
        ) + _events.split_config_patterns(config.get("build_commands", ""))

        if command and _events.matched_config_pattern(command, patterns) is not None:
            rewritten = command + (f"; printf '\\n{_events.DEFECT_EXIT_MARKER}:%s\\n' \"$?\"")
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "allow",
                            "updatedInput": {**tool_input, "command": rewritten},
                        }
                    }
                )
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
