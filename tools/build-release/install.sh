#!/bin/sh
# One-command installer (Story 4.3): fetches the latest release zip of
# ai-project-metrics-bmad and extracts it at the current directory's root.
# Usage: curl -fsSL <raw-url-to-this-file> | sh
set -e

REPO="jayanthchincholi26/ai-project-metrics-bmad"

if [ ! -d ".git" ]; then
    echo "error: not a git repository (no .git directory here) — cd to your repo root first" >&2
    exit 1
fi

echo "Fetching latest release info for $REPO..."
RELEASE_JSON=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest")

ZIP_URL=$(echo "$RELEASE_JSON" \
    | grep '"browser_download_url"' \
    | grep '\.zip"' \
    | sed -E 's/.*"browser_download_url": *"([^"]+)".*/\1/' \
    | head -n1)

if [ -z "$ZIP_URL" ]; then
    echo "error: could not find a .zip asset on the latest release of $REPO" >&2
    exit 1
fi

TMP_ZIP=$(mktemp)
echo "Downloading $ZIP_URL..."
curl -fsSL -o "$TMP_ZIP" "$ZIP_URL"

echo "Extracting into $(pwd)..."
unzip -o -q "$TMP_ZIP" -d .
rm -f "$TMP_ZIP"

echo ""
echo "Installed. Next: uv run tools/setup-hooks.py --repo-root ."
