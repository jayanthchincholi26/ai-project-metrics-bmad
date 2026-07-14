#!/usr/bin/env python3
"""Regenerates src/ai_metrics_capture/_bundled/ from the main repo's own
tools/build-release/main.py iter_entries() - the single source of truth for
what capture tooling ships (Story 4.1's zip artifact reads from the exact
same function). Run this before `uv build` - it must be a pre-build step,
not a hatchling build hook, because hatchling's sdist stage has no access to
files outside pypi-package/ once the sdist has been assembled (Story 4.5,
found live while trying the build-hook approach first)."""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
BUILD_RELEASE_MAIN = REPO_ROOT / "tools" / "build-release" / "main.py"
BUNDLED_DIR = PACKAGE_ROOT / "src" / "ai_metrics_capture" / "_bundled"


def load_build_release_main():
    spec = importlib.util.spec_from_file_location("_build_release_main", BUILD_RELEASE_MAIN)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sync() -> int:
    build_release = load_build_release_main()

    if BUNDLED_DIR.exists():
        shutil.rmtree(BUNDLED_DIR)
    BUNDLED_DIR.mkdir(parents=True)

    count = 0
    for source, arcname in build_release.iter_entries(REPO_ROOT):
        dest = BUNDLED_DIR / arcname
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        count += 1

    print(f'{{"ok": true, "bundled_dir": "{BUNDLED_DIR.as_posix()}", "entries": {count}}}')
    return 0


if __name__ == "__main__":
    sys.exit(sync())
