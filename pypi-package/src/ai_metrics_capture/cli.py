"""ai-metrics-capture CLI (Story 4.5) - a third distribution front door.

Unlike Story 4.3's curl/irm scripts (which fetch the latest GitHub release
at run time), this package bundles the capture tooling directly inside its
own wheel (see hatch_build.py) - `uvx` already resolved and fetched the
right version, so `install` makes no further network call. Same on-disk
result and same "must be a git repo" precondition as the other two paths
(Story 4.1's manual zip, Story 4.3's curl/irm) - all three ship the exact
same file set, sourced from the same tools/build-release/main.py manifest.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

BUNDLED = Path(__file__).resolve().parent / "_bundled"


def install(target: Path) -> int:
    if not (target / ".git").exists():
        print(
            "error: not a git repository (no .git directory or file here) "
            "— cd to your repo root first",
            file=sys.stderr,
        )
        return 2

    for source in sorted(BUNDLED.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(BUNDLED)
        dest = target / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)

    print("Installed. Next: uv run tools/setup-hooks.py --repo-root .")
    return 0


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(prog="ai-metrics-capture")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("install", help="install capture tooling into the current git repo")
    args = parser.parse_args(argv)

    if args.command == "install":
        return install(Path.cwd())
    return 2


if __name__ == "__main__":
    sys.exit(main())
