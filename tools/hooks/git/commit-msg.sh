#!/bin/sh
# installed by explore-jira-ai-metrics setup-hooks (AD-8) - do not edit; source of truth: tools/hooks/git/
uv run tools/hooks/git/commit-msg.py "$@"