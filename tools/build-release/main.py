#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""build-release — assembles the distributable capture-tooling artifact (Story 4.1).

Produces one zip a target repo extracts at its root: `tools/` (every capture
producer, the shared emitter, setup-hooks), every skill in `SKILLS`
(story-kickoff, story-close — Story 6.2), and INSTALL.md at the archive root.
Nothing else — no planning artifacts, specs,
prompts, or tests ever ship (the whole point of Epic 4: adopting capture must
not mean importing this planning repo).

Exclusions from tools/: this packager itself (a target repo installs the
artifact, it never builds one) and __pycache__/bytecode. The zip is built
deterministically enough to diff: entries are written in sorted order.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path
from typing import Iterator, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS = [
    Path(".claude/skills/story-kickoff/SKILL.md"),
    Path(".claude/skills/story-close/SKILL.md"),  # Story 6.2
    Path(".claude/skills/log-review-defect/SKILL.md"),  # Story 6.3
]
INSTALL = Path(__file__).resolve().parent / "INSTALL.md"
STORY_CONFIG_EXAMPLE = Path(__file__).resolve().parent / ".story-config.yaml.example"
DASHBOARD_WORKFLOW = Path(__file__).resolve().parent / "dashboard-workflow.yml"
EXCLUDED_DIR_NAMES = {"__pycache__", "build-release"}


def iter_entries(root: Path) -> Iterator[Tuple[Path, str]]:
    """Yield (absolute source, archive name) pairs, sorted for a reproducible zip."""
    yield INSTALL, "INSTALL.md"
    yield STORY_CONFIG_EXAMPLE, ".story-config.yaml.example"
    yield DASHBOARD_WORKFLOW, ".github/workflows/generate-dashboard.yml"
    for skill in SKILLS:
        yield root / skill, skill.as_posix()
    tools = root / "tools"
    for path in sorted(tools.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if EXCLUDED_DIR_NAMES.intersection(relative.parts):
            continue
        if path.suffix == ".pyc":
            continue
        yield path, relative.as_posix()


def build(root: Path, out_dir: Path, version: str) -> Path:
    missing = [
        str(p)
        for p in (
            INSTALL,
            STORY_CONFIG_EXAMPLE,
            DASHBOARD_WORKFLOW,
            *(root / skill for skill in SKILLS),
            root / "tools",
        )
        if not p.exists()
    ]
    if missing:
        raise FileNotFoundError(f"required artifact inputs missing: {', '.join(missing)}")
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"ai-metrics-capture-{version}.zip"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for source, arcname in iter_entries(root):
            zf.write(source, arcname)
    return target


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 2


def main(argv: "list[str] | None" = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--version",
        required=True,
        help="version label baked into the artifact filename (e.g. v0.1.0 — pass the git tag)",
    )
    p.add_argument(
        "--out-dir",
        default=str(REPO_ROOT / "dist"),
        help="directory the zip is written to (default: <repo>/dist)",
    )
    args = p.parse_args(argv)

    try:
        target = build(REPO_ROOT, Path(args.out_dir), args.version)
    except FileNotFoundError as exc:
        return fail(str(exc))

    with zipfile.ZipFile(target) as zf:
        count = len(zf.namelist())
    print(f'{{"ok": true, "artifact": "{target.as_posix()}", "entries": {count}}}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
