"""Tests for the metrics-report generator (Story 5.3) - a read-only renderer of
snapshots/*.json into human-readable metrics-reports/metrics-<MMDDYYYY>.md files."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


report = load("metrics_report", REPO / "tools" / "metrics-report" / "main.py")


def write_snapshot(root: Path, story_id: str, revision: int, **overrides) -> Path:
    snapshots_dir = root / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": 1,
        "story_id": story_id,
        "revision": revision,
        "pm_metrics": {
            "name": None,
            "points": 2,
            "goal": "Some goal",
            "sprint": None,
            "source_of_truth": "docs-only",
            "ai_tool": "claude-code",
            "created": "2026-07-14T09:00:00+05:30",
        },
        "engineering_metrics": {
            "commits": 2,
            "checkouts": 0,
            "merges": 0,
            "ai_sessions": 1,
            "tool_uses": 10,
            "prompts": 3,
            "event_count": 20,
            "first_event_at": "2026-07-14T09:00:00+05:30",
            "last_event_at": "2026-07-14T09:30:00+05:30",
        },
        "story_point_cost": {
            "phase1_points": None,
            "phase2_points": 3,
            "variance": None,
            "reduced_confidence": True,
            "reduced_confidence_reasons": [
                "no decision-narration producer implemented (out of scope through Story 2.6)"
            ],
        },
        "token_cost": {
            "input_tokens": None,
            "output_tokens": None,
            "reason": "no transcript_path in hook payload",
            "sessions_observed": 1,
            "cost_usd": None,
        },
        "estimated_cost": {
            "usd": None,
            "hourly_rate": None,
            "duration_minutes": 30.0,
            "reason": "hourly_rate not configured in .story-config.yaml",
        },
    }
    for key, value in overrides.items():
        if isinstance(value, dict) and key in data:
            data[key].update(value)
        else:
            data[key] = value
    path = snapshots_dir / f"{story_id}.v1.rev{revision}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def run(root: Path) -> int:
    return report.main(["--repo-root", str(root)])


def report_path(root: Path, mmddyyyy: str) -> Path:
    return root / "metrics-reports" / f"metrics-{mmddyyyy}.md"


# --- Task 1: discovery, revision selection, date grouping ---


def test_only_the_highest_revision_is_rendered_per_story(tmp_path):
    write_snapshot(tmp_path, "story-a", 1, pm_metrics={"goal": "old rev, must not appear"})
    write_snapshot(tmp_path, "story-a", 2, pm_metrics={"goal": "new rev, must appear"})

    run(tmp_path)

    text = report_path(tmp_path, "07142026").read_text(encoding="utf-8")
    assert "new rev, must appear" in text
    assert "old rev, must not appear" not in text


def test_stories_are_grouped_into_separate_files_by_last_event_at_date(tmp_path):
    write_snapshot(
        tmp_path,
        "story-a",
        1,
        engineering_metrics={"last_event_at": "2026-07-13T10:00:00+05:30"},
    )
    write_snapshot(
        tmp_path,
        "story-b",
        1,
        engineering_metrics={"last_event_at": "2026-07-14T10:00:00+05:30"},
    )

    run(tmp_path)

    assert report_path(tmp_path, "07132026").exists()
    assert report_path(tmp_path, "07142026").exists()
    assert "story-a" in report_path(tmp_path, "07132026").read_text(encoding="utf-8")
    assert "story-b" in report_path(tmp_path, "07142026").read_text(encoding="utf-8")


def test_missing_last_event_at_falls_back_to_created_date(tmp_path):
    write_snapshot(
        tmp_path,
        "story-a",
        1,
        engineering_metrics={"last_event_at": None},
        pm_metrics={"created": "2026-07-12T09:00:00+05:30"},
    )

    run(tmp_path)

    assert report_path(tmp_path, "07122026").exists()


def test_no_snapshots_directory_produces_no_reports(tmp_path):
    exit_code = run(tmp_path)

    assert exit_code == 0
    assert not (tmp_path / "metrics-reports").exists() or not list(
        (tmp_path / "metrics-reports").glob("*.md")
    )


def test_non_string_last_event_at_does_not_crash_report_generation(tmp_path):
    # Review finding (PR #27): a corrupted/hand-edited snapshot could carry a
    # non-string in last_event_at/created - must degrade to "unknown-date", not crash.
    write_snapshot(tmp_path, "story-a", 1, engineering_metrics={"last_event_at": 12345})

    exit_code = run(tmp_path)

    assert exit_code == 0
    assert (tmp_path / "metrics-reports" / "metrics-unknown-date.md").exists()


def test_malformed_date_string_does_not_crash_report_generation(tmp_path):
    # Review finding (PR #27): a date-like string that isn't actually YYYY-MM-DD
    # (e.g. corrupted data) must not crash mmddyyyy()'s unpack.
    write_snapshot(tmp_path, "story-a", 1, engineering_metrics={"last_event_at": "not-a-real-date"})

    exit_code = run(tmp_path)

    assert exit_code == 0
    assert (tmp_path / "metrics-reports" / "metrics-unknown-date.md").exists()


# --- Task 2: per-story rendering ---


def test_story_with_no_name_falls_back_to_story_id_as_title(tmp_path):
    write_snapshot(tmp_path, "story-20260714-abc123", 1, pm_metrics={"name": None})

    run(tmp_path)

    text = report_path(tmp_path, "07142026").read_text(encoding="utf-8")
    assert "## story-20260714-abc123" in text


def test_story_with_a_name_uses_it_as_the_title(tmp_path):
    write_snapshot(tmp_path, "story-20260714-abc123", 1, pm_metrics={"name": "Hello World"})

    run(tmp_path)

    text = report_path(tmp_path, "07142026").read_text(encoding="utf-8")
    assert "## Hello World" in text


def test_null_estimated_and_token_cost_show_not_tracked_with_reason(tmp_path):
    write_snapshot(tmp_path, "story-a", 1)

    run(tmp_path)

    text = report_path(tmp_path, "07142026").read_text(encoding="utf-8")
    assert "not tracked" in text
    assert "hourly_rate not configured in .story-config.yaml" in text
    assert "no transcript_path in hook payload" in text


def test_real_estimated_and_token_cost_are_rendered_as_usd(tmp_path):
    write_snapshot(
        tmp_path,
        "story-a",
        1,
        estimated_cost={"usd": 5.0, "hourly_rate": 10, "reason": None},
        token_cost={
            "input_tokens": 1000,
            "output_tokens": 100,
            "cost_usd": 0.00175,
            "reason": None,
        },
    )

    run(tmp_path)

    text = report_path(tmp_path, "07142026").read_text(encoding="utf-8")
    assert "$5.0000" in text
    assert "1000" in text and "100" in text


def test_duration_falls_back_to_engineering_metrics_for_pre_5_2_snapshots(tmp_path):
    # Found via live E2E (Story 5.3) against real snapshots predating Story 5.2's
    # estimated_cost section entirely - must still show a real duration, not "unknown".
    path = write_snapshot(tmp_path, "story-a", 1)
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["estimated_cost"]
    path.write_text(json.dumps(data), encoding="utf-8")

    run(tmp_path)

    text = report_path(tmp_path, "07142026").read_text(encoding="utf-8")
    assert "~30 minutes" in text
    assert "unknown duration" not in text


def test_reduced_confidence_reason_appears_in_notes(tmp_path):
    write_snapshot(tmp_path, "story-a", 1)

    run(tmp_path)

    text = report_path(tmp_path, "07142026").read_text(encoding="utf-8")
    assert "no decision-narration producer implemented" in text


def test_defect_fields_fall_back_to_not_tracked_when_defect_metrics_is_absent(tmp_path):
    # A snapshot predating Story 5.4 has no defect_metrics section at all.
    write_snapshot(tmp_path, "story-a", 1)

    run(tmp_path)

    text = report_path(tmp_path, "07142026").read_text(encoding="utf-8")
    assert "Total Defects**: not tracked — no reason given" in text
    assert "Testing Efficiency**: not tracked — no reason given" in text
    assert "Review Efficiency**: not tracked — no reason given" in text


def test_defect_fields_show_reason_when_zero_defects_logged(tmp_path):
    write_snapshot(
        tmp_path,
        "story-a",
        1,
        defect_metrics={
            "total_defects": None,
            "compile_defects": None,
            "test_defects": None,
            "review_defects": None,
            "testing_efficiency": None,
            "review_efficiency": None,
            "reason": "no defects logged for this story",
        },
    )

    run(tmp_path)

    text = report_path(tmp_path, "07142026").read_text(encoding="utf-8")
    assert "Total Defects**: not tracked — no defects logged for this story" in text
    assert "Testing Efficiency**: not tracked — no defects logged for this story" in text
    assert "Review Efficiency**: not tracked — no defects logged for this story" in text


def test_defect_fields_render_real_values(tmp_path):
    write_snapshot(
        tmp_path,
        "story-a",
        1,
        defect_metrics={
            "total_defects": 4,
            "compile_defects": 1,
            "test_defects": 2,
            "review_defects": 1,
            "testing_efficiency": 75.0,
            "review_efficiency": 25.0,
            "reason": None,
        },
    )

    run(tmp_path)

    text = report_path(tmp_path, "07142026").read_text(encoding="utf-8")
    assert "Total Defects**: 4" in text
    assert "Testing Efficiency**: 75.0%" in text
    assert "Review Efficiency**: 25.0%" in text


# --- Task 3: idempotent regeneration ---


def test_running_twice_with_no_new_snapshots_is_byte_identical(tmp_path):
    write_snapshot(tmp_path, "story-a", 1)

    run(tmp_path)
    first = report_path(tmp_path, "07142026").read_bytes()
    run(tmp_path)
    second = report_path(tmp_path, "07142026").read_bytes()

    assert first == second


def test_regeneration_does_not_leave_a_stale_entry_from_a_prior_run(tmp_path):
    write_snapshot(tmp_path, "story-a", 1)
    run(tmp_path)
    # simulate story-a being superseded by a newer revision with a different goal
    write_snapshot(tmp_path, "story-a", 2, pm_metrics={"goal": "updated goal"})

    run(tmp_path)

    text = report_path(tmp_path, "07142026").read_text(encoding="utf-8")
    assert "updated goal" in text
    assert text.count("## story-a") == 1
