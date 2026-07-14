#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""post_tool_use capture hook - emits `ai.claude-code.tool_use` (AD-1a/AD-10) via the shared emitter.

Returns 0 unconditionally: a non-zero Claude Code hook exit can block the
tool call or disrupt the session, and metrics capture must never do that
(the commit-msg precedent, extended). AD-9 visibility comes from the
emitter's stderr surfacing.

Privacy guard: tool_input is NEVER emitted - tool arguments can carry secrets.
Story 5.4 extends this hook to detect compile/test defects, and keeps this
guard: only a matched pattern NAME (never the actual command text, stdout,
or stderr) is ever written to an event payload.

Also records activity for AD-7's idle-detection (Story 3.2): this is one of
the two signals (with `user_prompt_submit`) that can reveal - in arrears -
that the active slice has been idle past the threshold.

Story 5.4: compile/test defect capture, fully automatic, opt-in via
`.story-config.yaml`'s `test_commands`/`build_commands` (comma-separated
patterns, e.g. `test_commands: pytest, npm test`). A Bash tool call whose
command contains a configured pattern AND exits non-zero appends
`ai.claude-code.defect_test`/`ai.claude-code.defect_compile` - kept within
the existing `ai.<tool>.*` namespace family (AD-1a) rather than a new
top-level `defect.*` namespace. Absent config = unchanged behavior (no new
event ever emitted). MCP tools (e.g. creating a Jira subtask) are NOT
reachable from here - hooks are subprocesses, not a live assistant turn -
so these defects stay local-only by design (see Story 5.4's Dev Notes)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)  # bridge to the shared emitter (spine-sanctioned, Story 2.3)
import _events


def split_patterns(raw: str) -> "list[str]":
    return [p.strip() for p in raw.split(",") if p.strip()]


def matched_pattern(command: str, patterns: "list[str]") -> "str | None":
    for pattern in patterns:
        if pattern in command:
            return pattern
    return None


def main(argv: list[str] | None = None) -> int:
    data = _events.read_stdin_json()
    _events.emit(
        "ai",
        "ai.claude-code.tool_use",
        {"session_id": data.get("session_id"), "tool_name": data.get("tool_name")},
    )

    if data.get("tool_name") == "Bash":
        root = _events.repo_root()
        config = _events.read_story_config(root)
        command = data.get("tool_input", {}).get("command", "")
        exit_code = data.get("exit_code")

        if exit_code not in (None, 0):
            for config_key, event_type in (
                ("test_commands", "ai.claude-code.defect_test"),
                ("build_commands", "ai.claude-code.defect_compile"),
            ):
                patterns = split_patterns(config.get(config_key, ""))
                pattern = matched_pattern(command, patterns)
                if pattern is not None:
                    _events.emit("ai", event_type, {"matched_pattern": pattern})
                    break  # test_commands wins over build_commands on a double match

    _events.record_activity(_events.repo_root())
    return 0


if __name__ == "__main__":
    sys.exit(main())
