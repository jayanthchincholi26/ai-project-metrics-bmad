#!/bin/sh
# Teardown counterpart to install.sh (Story 4.6): removes everything the
# install + `uv run tools/setup-hooks.py` added. Destructive — prints what it
# will remove and asks for confirmation unless -y/--yes is passed.
# Usage:
#   sh uninstall.sh [--yes]
#   curl -fsSL <raw-url-to-this-file> | sh -s -- --yes
set -e

MARKER="installed by explore-jira-ai-metrics setup-hooks"

YES=""
for arg in "$@"; do
    case "$arg" in
        -y|--yes) YES="1" ;;
    esac
done

if [ ! -e ".git" ]; then
    echo "error: not a git repository (no .git directory or file here) — cd to your repo root first" >&2
    exit 1
fi

PATHS=""
for p in tools .claude/skills/story-kickoff INSTALL.md .story-config.yaml.example \
         .story-config.yaml .story.yaml .story-events.jsonl .story-events.pending.jsonl \
         .active-story .active-claude-session snapshots metrics-reports; do
    if [ -e "$p" ]; then
        PATHS="$PATHS $p"
    fi
done

for h in post-commit post-checkout post-merge commit-msg; do
    hook=".git/hooks/$h"
    if [ -f "$hook" ] && grep -q "$MARKER" "$hook" 2>/dev/null; then
        PATHS="$PATHS $hook"
    fi
done

SETTINGS=".claude/settings.json"

if [ -z "$PATHS" ] && [ ! -f "$SETTINGS" ]; then
    echo "Nothing to remove — this repo has no capture tooling installed."
    exit 0
fi

echo "The following will be removed:"
for p in $PATHS; do
    echo "  $p"
done
if [ -f "$SETTINGS" ]; then
    echo "  (and this tooling's hook entries in $SETTINGS — other keys/entries are preserved)"
fi

if [ -z "$YES" ]; then
    printf "Proceed? [y/N] "
    read -r ans
    case "$ans" in
        y|Y|yes|Yes) ;;
        *)
            echo "Aborted — nothing removed."
            exit 0
            ;;
    esac
fi

for p in $PATHS; do
    rm -rf "$p"
done

if [ -f "$SETTINGS" ]; then
    uv run python - "$SETTINGS" <<'PY'
import json
import os
import sys

path = sys.argv[1]
EVENTS = ("SessionStart", "SessionEnd", "PreToolUse", "PostToolUse", "Stop", "UserPromptSubmit")

try:
    with open(path, encoding="utf-8") as f:
        settings = json.load(f)
except (OSError, json.JSONDecodeError) as exc:
    print(f"warning: could not parse {path} ({exc}) — leaving it untouched", file=sys.stderr)
    sys.exit(0)

hooks = settings.get("hooks")
if isinstance(hooks, dict):
    for event in EVENTS:
        entries = hooks.get(event)
        if not isinstance(entries, list):
            continue
        kept = []
        for entry in entries:
            inner = entry.get("hooks", []) if isinstance(entry, dict) else []
            is_ours = any(
                isinstance(h, dict) and "tools/hooks/claude/" in h.get("command", "") for h in inner
            )
            if not is_ours:
                kept.append(entry)
        if kept:
            hooks[event] = kept
        else:
            hooks.pop(event, None)
    if not hooks:
        settings.pop("hooks", None)

tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8", newline="\n") as f:
    json.dump(settings, f, indent=2)
    f.write("\n")
os.replace(tmp, path)
PY
fi

echo ""
echo "Uninstalled."
