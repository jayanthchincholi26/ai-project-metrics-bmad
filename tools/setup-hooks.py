#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""setup-hooks — the single committed installer for all capture hooks (AD-8).

Copies the git-tracked shims in tools/hooks/git/ into .git/hooks/ and merges
the six Claude Code hook entries (SessionStart, SessionEnd, PreToolUse,
PostToolUse, Stop, UserPromptSubmit) into .claude/settings.json, each pointing
at tools/hooks/claude/*.py via `uv run`. Runs once per clone; re-running is
idempotent (our own installs are upgraded in place, nothing duplicates).

Safety rules: a pre-existing .git/hooks file WITHOUT our marker is somebody
else's hook — the installer refuses (exit 2) and touches nothing. A malformed
settings.json is likewise refused, never clobbered. All validation happens
before any write, and every write is atomic.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

MARKER = "installed by explore-jira-ai-metrics setup-hooks"
GIT_HOOKS = ("post-commit", "post-checkout", "post-merge", "commit-msg")
CLAUDE_EVENTS = {
    "SessionStart": "session_start.py",
    "SessionEnd": "session_end.py",
    "PreToolUse": "pre_tool_use.py",
    "PostToolUse": "post_tool_use.py",
    "Stop": "stop.py",
    "UserPromptSubmit": "user_prompt_submit.py",
}


def write_atomic(path: Path, text: str) -> None:
    """Temp + flush + fsync + atomic rename, so a crash never half-writes a file."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def command_for(root: Path, script: str) -> str:
    """Absolute, quoted path (Story 2.7) — a relative path breaks the moment a
    session cd's elsewhere, since Claude Code's hook invocation reuses whatever
    cwd the session has drifted to rather than always using the repo root.
    Quoting guards against a repo root containing spaces; .as_posix() keeps
    forward slashes for cross-platform consistency."""
    abs_path = (root / "tools" / "hooks" / "claude" / script).resolve()
    return f'uv run "{abs_path.as_posix()}"'


def references_our_script(command: str, script: str) -> bool:
    """True if `command` invokes `script` specifically — the old relative form,
    the new absolute form, or either quoted/padded with incidental whitespace —
    never merely a *substring* collision (PR #22 review): a hand-added hook
    like `my_backstop.py` must never be mistaken for our `stop.py` just
    because the filename happens to end the same way. Requires a path
    boundary (`/`) immediately before the script name, or an exact match."""
    cleaned = command.strip().rstrip('"').strip().replace("\\", "/")
    return cleaned == script or cleaned.endswith("/" + script)


def merge_settings(root: Path, settings: dict[str, Any]) -> dict[str, Any]:
    """Additively wire our six events; user keys and user hook entries are
    preserved. An existing entry for one of our six scripts — old relative-path
    form or current absolute form — is upgraded in place rather than
    duplicated (Story 2.7)."""
    hooks = settings.setdefault("hooks", {})
    for event, script in CLAUDE_EVENTS.items():
        entries = hooks.setdefault(event, [])
        wanted = command_for(root, script)
        upgraded = False
        for entry in entries:
            for hook in entry.get("hooks", []):
                if references_our_script(hook.get("command", ""), script):
                    hook["command"] = wanted
                    upgraded = True
        if not upgraded:
            entries.append({"hooks": [{"type": "command", "command": wanted}]})
    return settings


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--repo-root", required=True, help="root of the clone to install into")
    args = p.parse_args(argv)

    root = Path(args.repo_root).resolve()
    if not (root / ".git").is_dir():
        return fail(f"{root} is not a git clone (no .git directory)")
    sources = {name: root / "tools" / "hooks" / "git" / f"{name}.sh" for name in GIT_HOOKS}
    missing = [name for name, src in sources.items() if not src.is_file()]
    if missing:
        return fail(f"tracked hook source(s) missing under tools/hooks/git/: {', '.join(missing)}")

    hooks_dir = root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    def is_conflict(target: Path) -> bool:
        """Anything we can't prove is ours: a non-file (e.g. a directory) or a
        file without our marker."""
        if not target.exists():
            return False
        if not target.is_file():
            return True
        return MARKER not in target.read_text(encoding="utf-8", errors="replace")

    conflicts = [name for name in GIT_HOOKS if is_conflict(hooks_dir / name)]
    if conflicts:
        return fail(
            f"existing hook(s) not installed by this tool: {', '.join(conflicts)} — "
            "move them aside (or chain them manually) and re-run"
        )

    settings_path = root / ".claude" / "settings.json"
    settings: dict[str, Any] = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return fail(f"{settings_path} is not valid JSON ({exc}) — fix it and re-run")

    for name in GIT_HOOKS:
        target = hooks_dir / name
        write_atomic(target, sources[name].read_text(encoding="utf-8"))
        os.chmod(target, 0o755)

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(settings_path, json.dumps(merge_settings(root, settings), indent=2) + "\n")

    print(
        json.dumps(
            {
                "ok": True,
                "git_hooks": list(GIT_HOOKS),
                "settings": str(settings_path.resolve()),
                "events_wired": list(CLAUDE_EVENTS),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
