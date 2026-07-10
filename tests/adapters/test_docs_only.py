"""Tests for the docs-only kickoff adapter (Story 1.1, AC 1-3)."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

# The structural seed fixes the hyphenated dir name (`docs-only`), which cannot be
# imported as a package, so the script is loaded from its file path instead.
SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "adapters" / "docs-only" / "main.py"
_spec = importlib.util.spec_from_file_location("docs_only_main", SCRIPT)
docs_only = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(docs_only)

MANIFEST_KEYS = [
    "story_id",
    "source_of_truth",
    "ai_tool",
    "points",
    "points_estimated",
    "goal",
    "sprint",
    "description",
    "created",
]


def kickoff(repo_root: Path, **overrides) -> int:
    fields = {"points": "5", "goal": "Ship the docs-only kickoff", "sprint": "Sprint 12"}
    fields.update(overrides)
    argv = ["--repo-root", str(repo_root)]
    for key, value in fields.items():
        if value is not None:
            argv += [f"--{key}", value]
    return docs_only.main(argv)


def manifest_path(repo_root: Path) -> Path:
    return repo_root / ".story.yaml"


def parse_manifest(repo_root: Path) -> dict:
    parsed = {}
    for line in manifest_path(repo_root).read_text(encoding="utf-8").splitlines():
        key, raw = line.split(": ", 1)
        parsed[key] = json.loads(raw)
    return parsed


def test_success_writes_manifest_with_all_keys_in_fixed_order(tmp_path):
    exit_code = kickoff(tmp_path)

    assert exit_code == 0
    keys = [
        line.split(":", 1)[0]
        for line in manifest_path(tmp_path).read_text(encoding="utf-8").splitlines()
    ]
    assert keys == MANIFEST_KEYS


def test_success_records_confirmed_values_and_docs_only_source(tmp_path):
    kickoff(tmp_path, points="8", goal="Build the thing", sprint="Sprint 3")

    manifest = parse_manifest(tmp_path)
    assert manifest["points"] == 8
    assert manifest["goal"] == "Build the thing"
    assert manifest["sprint"] == "Sprint 3"
    assert manifest["source_of_truth"] == "docs-only"


def test_success_prints_exactly_one_json_ack(tmp_path, capsys):
    kickoff(tmp_path)

    out_lines = capsys.readouterr().out.strip().splitlines()
    assert len(out_lines) == 1
    ack = json.loads(out_lines[0])
    assert ack["ok"] is True
    assert ack["story_id"] == parse_manifest(tmp_path)["story_id"]
    assert Path(ack["story_yaml"]) == manifest_path(tmp_path).resolve()


def test_story_id_matches_generated_format(tmp_path):
    kickoff(tmp_path)

    assert re.fullmatch(r"story-\d{8}-[0-9a-f]{6}", parse_manifest(tmp_path)["story_id"])


def test_two_kickoffs_generate_distinct_story_ids(tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    first.mkdir()
    second.mkdir()

    kickoff(first)
    kickoff(second)

    assert parse_manifest(first)["story_id"] != parse_manifest(second)["story_id"]


def test_description_defaults_to_null(tmp_path):
    kickoff(tmp_path)

    assert parse_manifest(tmp_path)["description"] is None


def test_description_recorded_when_provided(tmp_path):
    kickoff(tmp_path, description="A short summary")

    assert parse_manifest(tmp_path)["description"] == "A short summary"


def test_created_is_isoformat_with_offset(tmp_path):
    kickoff(tmp_path)

    assert re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}", parse_manifest(tmp_path)["created"]
    )


def test_source_of_truth_flag_is_recorded(tmp_path):
    kickoff(tmp_path, **{"source-of-truth": "jira"})

    assert parse_manifest(tmp_path)["source_of_truth"] == "jira"


def test_source_of_truth_defaults_to_docs_only(tmp_path):
    kickoff(tmp_path)

    assert parse_manifest(tmp_path)["source_of_truth"] == "docs-only"


def test_invalid_source_of_truth_is_rejected_and_writes_nothing(tmp_path):
    with pytest.raises(SystemExit) as excinfo:
        kickoff(tmp_path, **{"source-of-truth": "gitlab"})

    assert excinfo.value.code == 2
    assert not manifest_path(tmp_path).exists()


def test_ai_tool_defaults_to_claude_code(tmp_path):
    kickoff(tmp_path)

    assert parse_manifest(tmp_path)["ai_tool"] == "claude-code"


def test_ai_tool_flag_is_recorded(tmp_path):
    kickoff(tmp_path, **{"ai-tool": "cursor"})

    assert parse_manifest(tmp_path)["ai_tool"] == "cursor"


def test_invalid_ai_tool_format_exits_2_and_writes_nothing(tmp_path):
    exit_code = kickoff(tmp_path, **{"ai-tool": "Claude Code!"})

    assert exit_code == 2
    assert not manifest_path(tmp_path).exists()


def test_points_estimated_is_recorded_when_given(tmp_path):
    kickoff(tmp_path, **{"points-estimated": "7"})

    assert parse_manifest(tmp_path)["points_estimated"] == 7


def test_points_estimated_defaults_to_null_when_omitted(tmp_path):
    kickoff(tmp_path)

    assert parse_manifest(tmp_path)["points_estimated"] is None


def test_points_estimated_accepts_fractional_values(tmp_path):
    kickoff(tmp_path, **{"points-estimated": "6.5"})

    assert parse_manifest(tmp_path)["points_estimated"] == 6.5


def test_story_id_date_matches_created_date(tmp_path):
    kickoff(tmp_path)

    manifest = parse_manifest(tmp_path)
    story_id_date = manifest["story_id"].split("-")[1]
    created_date = manifest["created"][:10].replace("-", "")
    assert story_id_date == created_date


def test_multiline_goal_collapses_to_single_line(tmp_path):
    kickoff(tmp_path, goal="line one\nline two\n\tindented")

    assert parse_manifest(tmp_path)["goal"] == "line one line two indented"


def test_zero_points_exits_2_and_writes_nothing(tmp_path, capsys):
    exit_code = kickoff(tmp_path, points="0")

    assert exit_code == 2
    assert not manifest_path(tmp_path).exists()
    assert "points" in capsys.readouterr().err


def test_negative_points_exits_2_and_writes_nothing(tmp_path):
    exit_code = kickoff(tmp_path, points="-3")

    assert exit_code == 2
    assert not manifest_path(tmp_path).exists()


def test_fractional_points_are_accepted_and_recorded(tmp_path):
    kickoff(tmp_path, points="1.5")

    assert parse_manifest(tmp_path)["points"] == 1.5


def test_integral_float_points_are_recorded_as_int(tmp_path):
    kickoff(tmp_path, points="5.0")

    points = parse_manifest(tmp_path)["points"]
    assert points == 5
    assert isinstance(points, int)


def test_non_numeric_points_exits_2_and_writes_nothing(tmp_path):
    exit_code = kickoff(tmp_path, points="a lot")

    assert exit_code == 2
    assert not manifest_path(tmp_path).exists()


def test_nan_and_inf_points_exit_2_and_write_nothing(tmp_path):
    for value in ("nan", "inf"):
        exit_code = kickoff(tmp_path, points=value)

        assert exit_code == 2
        assert not manifest_path(tmp_path).exists()
    # "-inf" never even reaches validation: argparse rejects it as an unknown option
    with pytest.raises(SystemExit) as excinfo:
        kickoff(tmp_path, points="-inf")
    assert excinfo.value.code == 2
    assert not manifest_path(tmp_path).exists()


def test_blank_goal_exits_2_and_writes_nothing(tmp_path):
    exit_code = kickoff(tmp_path, goal="   ")

    assert exit_code == 2
    assert not manifest_path(tmp_path).exists()


def test_blank_sprint_exits_2_and_writes_nothing(tmp_path):
    exit_code = kickoff(tmp_path, sprint=" \n ")

    assert exit_code == 2
    assert not manifest_path(tmp_path).exists()


def test_missing_sprint_argument_exits_2_and_writes_nothing(tmp_path):
    with pytest.raises(SystemExit) as excinfo:
        kickoff(tmp_path, sprint=None)

    assert excinfo.value.code == 2
    assert not manifest_path(tmp_path).exists()


def test_existing_manifest_is_refused_and_left_unchanged(tmp_path, capsys):
    kickoff(tmp_path, goal="Original story")
    original = manifest_path(tmp_path).read_bytes()

    exit_code = kickoff(tmp_path, goal="Second kickoff attempt")

    assert exit_code == 2
    assert manifest_path(tmp_path).read_bytes() == original
    assert "already exists" in capsys.readouterr().err


def test_missing_repo_root_exits_2_and_writes_nothing(tmp_path):
    exit_code = kickoff(tmp_path / "does-not-exist")

    assert exit_code == 2
    assert not (tmp_path / "does-not-exist").exists()


def test_no_temp_file_left_behind_after_success(tmp_path):
    kickoff(tmp_path)

    assert [p.name for p in tmp_path.iterdir()] == [".story.yaml"]
