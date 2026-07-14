"""Tests for the log-defect ledger writer (Story 5.4)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "tools" / "log-defect" / "main.py"

# Bridge-import _events first (same pattern as tests/snapshot_assembler), then
# the hyphenated-dir script itself via its file path.
_events_spec = importlib.util.spec_from_file_location(
    "_events", REPO / "tools" / "hooks" / "_events.py"
)
_events = importlib.util.module_from_spec(_events_spec)
sys.modules["_events"] = _events
_events_spec.loader.exec_module(_events)

_spec = importlib.util.spec_from_file_location("log_defect_main", SCRIPT)
log_defect = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(log_defect)


def run(root: Path, **overrides) -> int:
    fields = {
        "repo-root": str(root),
        "type": "review",
        "summary": "Missing null check",
        "description": "estimated_cost_of() crashes on offset-naive timestamps",
    }
    fields.update(overrides)
    argv = []
    for key, value in fields.items():
        if value is not None:
            argv += [f"--{key}", str(value)]
    return log_defect.main(argv)


def read_events(root: Path, pending: bool = False) -> "list[dict]":
    name = ".story-events.pending.jsonl" if pending else ".story-events.jsonl"
    path = root / name
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def write_manifest(root: Path, story_id: str = "story-20260714-abc123") -> None:
    (root / ".story.yaml").write_text(f'story_id: "{story_id}"\n', encoding="utf-8")


def test_appends_a_well_formed_defect_review_event(tmp_path):
    write_manifest(tmp_path)

    exit_code = run(tmp_path)

    assert exit_code == 0
    (event,) = read_events(tmp_path)
    assert event["type"] == "ai.claude-code.defect_review"
    assert event["source"] == "ai"
    assert event["story_id"] == "story-20260714-abc123"
    assert event["payload"]["summary"] == "Missing null check"
    assert (
        event["payload"]["description"] == "estimated_cost_of() crashes on offset-naive timestamps"
    )


def test_points_defaults_to_one(tmp_path):
    write_manifest(tmp_path)

    run(tmp_path)

    (event,) = read_events(tmp_path)
    assert event["payload"]["points"] == 1


def test_points_override_is_recorded(tmp_path):
    write_manifest(tmp_path)

    run(tmp_path, points="2")

    (event,) = read_events(tmp_path)
    assert event["payload"]["points"] == 2


def test_jira_subtask_key_defaults_to_null(tmp_path):
    write_manifest(tmp_path)

    run(tmp_path)

    (event,) = read_events(tmp_path)
    assert event["payload"]["jira_subtask_key"] is None


def test_jira_subtask_key_recorded_when_provided(tmp_path):
    write_manifest(tmp_path)

    run(tmp_path, **{"jira-subtask-key": "AI-140"})

    (event,) = read_events(tmp_path)
    assert event["payload"]["jira_subtask_key"] == "AI-140"


def test_buffers_to_pending_spool_when_no_manifest_exists_yet(tmp_path):
    exit_code = run(tmp_path)

    assert exit_code == 0
    assert read_events(tmp_path) == []
    (event,) = read_events(tmp_path, pending=True)
    assert event["story_id"] is None
    assert event["type"] == "ai.claude-code.defect_review"


def test_blank_summary_exits_2_and_writes_nothing(tmp_path):
    write_manifest(tmp_path)

    exit_code = run(tmp_path, summary="   ")

    assert exit_code == 2
    assert read_events(tmp_path) == []


def test_blank_description_exits_2_and_writes_nothing(tmp_path):
    write_manifest(tmp_path)

    exit_code = run(tmp_path, description="   ")

    assert exit_code == 2
    assert read_events(tmp_path) == []


def test_non_numeric_points_exits_2_and_writes_nothing(tmp_path):
    write_manifest(tmp_path)

    exit_code = run(tmp_path, points="a lot")

    assert exit_code == 2
    assert read_events(tmp_path) == []


def test_zero_points_exits_2_and_writes_nothing(tmp_path):
    write_manifest(tmp_path)

    exit_code = run(tmp_path, points="0")

    assert exit_code == 2
    assert read_events(tmp_path) == []


def test_missing_repo_root_exits_2(tmp_path):
    exit_code = run(tmp_path / "does-not-exist")

    assert exit_code == 2


def test_prints_exactly_one_json_ack(tmp_path, capsys):
    write_manifest(tmp_path)

    run(tmp_path)

    out_lines = capsys.readouterr().out.strip().splitlines()
    assert len(out_lines) == 1
    ack = json.loads(out_lines[0])
    assert ack["ok"] is True
    assert ack["story_id"] == "story-20260714-abc123"
