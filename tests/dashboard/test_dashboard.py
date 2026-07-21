"""Tests for the leadership HTML dashboard (Story 5.5) - a read-only, self-contained
renderer of snapshots/*.json into a single metrics-reports/dashboard.html file."""

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


dashboard = load("dashboard_main", REPO / "tools" / "dashboard" / "main.py")


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
            "reduced_confidence_reasons": ["no decision-narration producer implemented"],
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
    return dashboard.main(["--repo-root", str(root)])


def dashboard_html(root: Path) -> str:
    return (root / "metrics-reports" / "dashboard.html").read_text(encoding="utf-8")


# --- Task 1: discovery reuse, aggregation across all dates ---


def test_discovery_is_reused_from_metrics_report_not_reimplemented(tmp_path, monkeypatch):
    calls = []
    original = dashboard.metrics_report.discover_snapshots

    def spy(root):
        calls.append(root)
        return original(root)

    monkeypatch.setattr(dashboard.metrics_report, "discover_snapshots", spy)
    write_snapshot(tmp_path, "story-a", 1)

    run(tmp_path)

    assert len(calls) == 1
    assert calls[0] == tmp_path


def test_only_the_highest_revision_is_shown_per_story(tmp_path):
    write_snapshot(tmp_path, "story-a", 1, pm_metrics={"goal": "old rev, must not appear"})
    write_snapshot(tmp_path, "story-a", 2, pm_metrics={"goal": "new rev, must appear"})

    run(tmp_path)

    html = dashboard_html(tmp_path)
    assert "new rev, must appear" not in html  # goal isn't rendered in the dashboard table
    assert html.count("story-a") >= 1  # sanity: the story does appear once


def test_stories_from_different_dates_all_appear_in_one_file(tmp_path):
    write_snapshot(
        tmp_path, "story-a", 1, engineering_metrics={"last_event_at": "2026-07-10T10:00:00+05:30"}
    )
    write_snapshot(
        tmp_path, "story-b", 1, engineering_metrics={"last_event_at": "2026-07-14T10:00:00+05:30"}
    )

    run(tmp_path)

    html = dashboard_html(tmp_path)
    assert "story-a" in html
    assert "story-b" in html


def test_rows_are_sorted_by_date_descending(tmp_path):
    write_snapshot(
        tmp_path,
        "story-older",
        1,
        engineering_metrics={"last_event_at": "2026-07-10T10:00:00+05:30"},
    )
    write_snapshot(
        tmp_path,
        "story-newer",
        1,
        engineering_metrics={"last_event_at": "2026-07-14T10:00:00+05:30"},
    )

    run(tmp_path)

    html = dashboard_html(tmp_path)
    assert html.index("story-newer") < html.index("story-older")


# --- Task 2: stat tiles + table rendering ---


def test_total_stories_always_counts_every_story(tmp_path):
    write_snapshot(tmp_path, "story-a", 1)
    write_snapshot(tmp_path, "story-b", 1)

    run(tmp_path)

    html = dashboard_html(tmp_path)
    assert "2" in html  # total stories figure


def test_estimated_cost_total_sums_only_known_values_and_notes_exclusions(tmp_path):
    write_snapshot(tmp_path, "story-a", 1, estimated_cost={"usd": 5.0, "reason": None})
    write_snapshot(tmp_path, "story-b", 1)  # usd stays null

    run(tmp_path)

    html = dashboard_html(tmp_path)
    assert "$5.00" in html
    assert "1 of 2" in html or "1/2" in html  # some visible exclusion note


def test_token_cost_total_is_not_tracked_when_none_are_known(tmp_path):
    write_snapshot(tmp_path, "story-a", 1)

    run(tmp_path)

    html = dashboard_html(tmp_path)
    assert "not tracked" in html.lower()


def test_story_with_no_name_falls_back_to_story_id(tmp_path):
    write_snapshot(tmp_path, "story-20260714-abc123", 1, pm_metrics={"name": None})

    run(tmp_path)

    html = dashboard_html(tmp_path)
    assert "story-20260714-abc123" in html


def test_story_with_a_name_uses_it_in_the_row(tmp_path):
    write_snapshot(tmp_path, "story-20260714-abc123", 1, pm_metrics={"name": "Hello World"})

    run(tmp_path)

    html = dashboard_html(tmp_path)
    assert "Hello World" in html


def test_null_estimated_and_token_cost_show_not_tracked_with_reason(tmp_path):
    write_snapshot(tmp_path, "story-a", 1)

    run(tmp_path)

    html = dashboard_html(tmp_path)
    assert "hourly_rate not configured in .story-config.yaml" in html
    assert "no transcript_path in hook payload" in html


def test_defects_column_falls_back_to_not_tracked_when_defect_metrics_is_absent(tmp_path):
    # A snapshot predating Story 5.4 has no defect_metrics section at all.
    write_snapshot(tmp_path, "story-a", 1)

    run(tmp_path)

    html = dashboard_html(tmp_path)
    assert "not tracked — no reason given" in html


def test_defects_column_renders_real_values(tmp_path):
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

    html = dashboard_html(tmp_path)
    assert "4 total (testing 75.00% / review 25.00%)" in html


def test_output_is_self_contained_no_external_network_references(tmp_path):
    write_snapshot(tmp_path, "story-a", 1)

    run(tmp_path)

    html = dashboard_html(tmp_path)
    assert "http://" not in html
    assert "https://" not in html
    assert "cdn." not in html.lower()


def test_output_is_a_real_table_not_an_image_or_divs(tmp_path):
    write_snapshot(tmp_path, "story-a", 1)

    run(tmp_path)

    html = dashboard_html(tmp_path)
    assert "<table" in html
    assert "<img" not in html


def test_output_is_a_complete_html_document_not_a_bare_fragment(tmp_path):
    # Found via live E2E (Story 5.5): browsers render a fragment leniently, but a
    # real document matches this repo's own established HTML-doc convention.
    write_snapshot(tmp_path, "story-a", 1)

    run(tmp_path)

    html = dashboard_html(tmp_path)
    assert html.startswith("<!doctype html>")
    assert "<html" in html
    assert "<head>" in html
    assert "<title>Metrics Dashboard</title>" in html
    assert "<body>" in html


def test_dark_and_light_theme_css_both_present(tmp_path):
    write_snapshot(tmp_path, "story-a", 1)

    run(tmp_path)

    html = dashboard_html(tmp_path)
    assert "prefers-color-scheme: light" in html
    assert 'data-theme="dark"' in html
    assert 'data-theme="light"' in html


# --- Task 3: idempotent regeneration ---


def test_running_twice_with_no_new_snapshots_is_byte_identical(tmp_path):
    write_snapshot(tmp_path, "story-a", 1)

    run(tmp_path)
    first = (tmp_path / "metrics-reports" / "dashboard.html").read_bytes()
    run(tmp_path)
    second = (tmp_path / "metrics-reports" / "dashboard.html").read_bytes()

    assert first == second


def test_no_snapshots_produces_a_dashboard_with_zero_stories(tmp_path):
    exit_code = run(tmp_path)

    assert exit_code == 0
    html = dashboard_html(tmp_path)
    assert "0" in html


def test_table_headers_carry_explanatory_tooltips(tmp_path):
    write_snapshot(tmp_path, "story-a", 1)

    run(tmp_path)

    html = dashboard_html(tmp_path)
    assert '<th title="' in html


def test_stat_tiles_carry_explanatory_tooltips(tmp_path):
    write_snapshot(tmp_path, "story-a", 1)

    run(tmp_path)

    html = dashboard_html(tmp_path)
    assert 'class="tile" title="' in html


# --- Story 6.6: sprint-level rollups ---


def test_parse_iso_handles_real_jira_z_suffixed_dates():
    # Real confirmed shape from Story 6.5's live research: trailing Z + milliseconds,
    # which datetime.fromisoformat() only accepts natively from Python 3.11 onward.
    parsed = dashboard._parse_iso("2026-06-26T06:19:49.000Z")

    assert parsed is not None
    assert parsed.year == 2026 and parsed.month == 6 and parsed.day == 26


def test_parse_iso_returns_none_for_malformed_or_missing_values():
    assert dashboard._parse_iso(None) is None
    assert dashboard._parse_iso("not a date") is None
    assert dashboard._parse_iso("") is None


def test_sprint_status_ended_for_a_past_end_date():
    assert dashboard.sprint_status("2000-01-01T00:00:00.000Z") == "Ended"


def test_sprint_status_active_or_upcoming_for_a_future_end_date():
    assert dashboard.sprint_status("2099-01-01T00:00:00.000Z") == "Active or upcoming"


def test_sprint_status_unknown_when_end_date_missing_or_unparsable():
    assert dashboard.sprint_status(None) == "Unknown"
    assert dashboard.sprint_status("not a date") == "Unknown"


def test_group_by_sprint_groups_by_name_and_counts_no_sprint_stories():
    snapshots = [
        {"pm_metrics": {"sprint": "Sprint 9"}},
        {"pm_metrics": {"sprint": "Sprint 9"}},
        {"pm_metrics": {"sprint": "Sprint 10"}},
        {"pm_metrics": {"sprint": None}},
    ]

    groups, no_sprint_count = dashboard.group_by_sprint(snapshots)

    assert len(groups["Sprint 9"]) == 2
    assert len(groups["Sprint 10"]) == 1
    assert no_sprint_count == 1


def test_group_by_sprint_a_single_story_sprint_still_gets_its_own_group():
    groups, no_sprint_count = dashboard.group_by_sprint([{"pm_metrics": {"sprint": "Sprint 9"}}])

    assert groups == {"Sprint 9": [{"pm_metrics": {"sprint": "Sprint 9"}}]}
    assert no_sprint_count == 0


def test_sprint_rollup_row_takes_first_non_null_date_found_in_the_group():
    # An older snapshot (predating Story 6.5) sits alongside one that does carry dates.
    group = [
        {"pm_metrics": {"sprint": "Sprint 9", "sprint_start_date": None, "sprint_end_date": None}},
        {
            "pm_metrics": {
                "sprint": "Sprint 9",
                "sprint_start_date": "2026-06-08T06:03:51.792Z",
                "sprint_end_date": "2026-06-26T06:19:49.000Z",
            }
        },
    ]

    row = dashboard.sprint_rollup_row("Sprint 9", group)

    assert row["start_date"] == "2026-06-08T06:03:51.792Z"
    assert row["end_date"] == "2026-06-26T06:19:49.000Z"
    assert row["story_count"] == 2
    assert row["status"] == "Ended"


def test_sprint_rollup_row_dates_null_when_no_snapshot_in_the_group_has_them():
    group = [{"pm_metrics": {"sprint": "Sprint 9"}}]

    row = dashboard.sprint_rollup_row("Sprint 9", group)

    assert row["start_date"] is None
    assert row["end_date"] is None
    assert row["status"] == "Unknown"


def test_rollup_section_absent_when_no_snapshot_has_a_sprint(tmp_path):
    write_snapshot(tmp_path, "story-a", 1)  # default fixture: sprint is None

    run(tmp_path)

    html = dashboard_html(tmp_path)
    assert "Sprint Rollups" not in html


def test_rollup_section_present_and_shows_sprint_row(tmp_path):
    write_snapshot(
        tmp_path,
        "story-a",
        1,
        pm_metrics={
            "sprint": "Sprint 9",
            "sprint_start_date": "2026-06-08T06:03:51.792Z",
            "sprint_end_date": "2000-01-01T00:00:00.000Z",
        },
    )

    run(tmp_path)

    html = dashboard_html(tmp_path)
    assert "Sprint Rollups" in html
    assert "Sprint 9" in html
    assert "2026-06-08T06:03:51.792Z" in html
    assert "Ended" in html


def test_rollup_unknown_dates_show_unknown_not_blank(tmp_path):
    write_snapshot(tmp_path, "story-a", 1, pm_metrics={"sprint": "Sprint 9"})

    run(tmp_path)

    html = dashboard_html(tmp_path)
    assert "unknown" in html.lower()
    assert "Unknown" in html  # Overall Status


def test_rollup_no_sprint_row_appears_only_when_count_is_nonzero(tmp_path):
    write_snapshot(tmp_path, "story-a", 1, pm_metrics={"sprint": "Sprint 9"})
    write_snapshot(tmp_path, "story-b", 1)  # no sprint

    run(tmp_path)

    html = dashboard_html(tmp_path)
    assert "No Sprint" in html


def test_rollup_gives_each_distinct_sprint_its_own_row_even_a_single_story_sprint(tmp_path):
    write_snapshot(tmp_path, "story-a", 1, pm_metrics={"sprint": "Sprint 9"})
    write_snapshot(tmp_path, "story-b", 1, pm_metrics={"sprint": "Sprint 10"})
    write_snapshot(tmp_path, "story-c", 1, pm_metrics={"sprint": "Sprint 10"})

    run(tmp_path)

    html = dashboard_html(tmp_path)
    assert "Sprint 9" in html
    assert "Sprint 10" in html


def test_rollup_headers_carry_explanatory_tooltips(tmp_path):
    write_snapshot(tmp_path, "story-a", 1, pm_metrics={"sprint": "Sprint 9"})

    run(tmp_path)

    html = dashboard_html(tmp_path)
    # Story 6.5's own FIELD_GUIDE wording, distinctive to the new sprint-date columns.
    assert "Story 6.5" in html


def test_a_present_but_null_section_does_not_crash_generation(tmp_path):
    # Review finding (PR #28): dict.get(key, {}) only supplies its default for an
    # ABSENT key - a corrupted/hand-edited snapshot with e.g. "pm_metrics": null
    # (key present, value None) would crash aggregate_stats()/render_row() with
    # AttributeError on the chained .get() call. Must degrade gracefully instead.
    path = write_snapshot(tmp_path, "story-a", 1)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["pm_metrics"] = None
    data["estimated_cost"] = None
    data["token_cost"] = None
    data["engineering_metrics"] = None
    path.write_text(json.dumps(data), encoding="utf-8")

    exit_code = run(tmp_path)

    assert exit_code == 0
    html = dashboard_html(tmp_path)
    assert "story-a" in html  # falls back to story_id since pm_metrics.name is unavailable
    assert "not set" in html  # points, gracefully degraded rather than crashing
