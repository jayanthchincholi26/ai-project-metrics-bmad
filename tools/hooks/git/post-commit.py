#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""post-commit capture hook - git-side producer.

Placeholder: event emission (git.commit -> .story-events.jsonl, AD-1/AD-1a) lands in Story 2.2. Until then this
hook exits 0 so installed wiring never breaks a developer's flow.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    return 0


if __name__ == "__main__":
    sys.exit(main())
