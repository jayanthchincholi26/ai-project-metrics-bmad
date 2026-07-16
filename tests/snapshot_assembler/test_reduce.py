"""Tests for the snapshot assembler (Stories 2.4/2.6) — the pipeline's only reducer."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def load(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# _events must be registered in sys.modules before the assembler's bridge-import
# `import _events` runs (same pattern as the opsx-wrapper tests, Story 2.4/2.6).
events = load("_events", REPO / "tools" / "hooks" / "_events.py")
assembler = load("snapshot_assembler", REPO / "tools" / "snapshot-assembler" / "main.py")

STORY_ID = "story-20260710-close1"
ENVELOPE_KEYS = {
    "schema_version",
    "story_id",
    "revision",
    "pm_metrics",
    "engineering_metrics",
    "story_point_cost",
    "token_cost",
    "estimated_cost",
    "defect_metrics",
}


def write_story_config(root: Path, **rates) -> None:
    lines = "".join(f"{key}: {value}\n" for key, value in rates.items())
    (root / ".story-config.yaml").write_text(lines, encoding="utf-8")


def write_manifest(root: Path, story_id: str = STORY_ID, points_estimated=None) -> None:
    estimated_line = "null" if points_estimated is None else json.dumps(points_estimated)
    (root / ".story.yaml").write_text(
        f'story_id: "{story_id}"\n'
        'source_of_truth: "docs-only"\n'
        'ai_tool: "claude-code"\n'
        "points: 5\n"
        f"points_estimated: {estimated_line}\n"
        'goal: "Close the loop"\n'
        'sprint: "S3"\n'
        "description: null\n"
        'created: "2026-07-10T09:00:00+05:30"\n',
        encoding="utf-8",
    )


@pytest.fixture(autouse=True)
def no_real_git(monkeypatch):
    """Never spawn a real git process in this unit suite (§5) — default to "unresolvable"."""
    monkeypatch.setattr(events, "git_out", lambda *args, **kwargs: None)


def event(
    event_type: str, story_id: str = STORY_ID, ts: str = "2026-07-10T10:00:00+05:30", **payload
):
    source = (
        "git"
        if event_type.startswith("git.")
        else (
            "ai"
            if event_type.startswith("ai.")
            else ("time" if event_type.startswith("time.") else "opsx")
        )
    )
    return {
        "story_id": story_id,
        "source": source,
        "type": event_type,
        "timestamp": ts,
        "payload": payload,
    }


def write_events(root: Path, events: list, pending: bool = False) -> None:
    name = ".story-events.pending.jsonl" if pending else ".story-events.jsonl"
    lines = "".join(json.dumps(e) + "\n" for e in events)
    (root / name).write_text(lines, encoding="utf-8")


def run(root: Path) -> int:
    return assembler.main(["--repo-root", str(root)])


def run_dry(root: Path) -> int:
    return assembler.main(["--repo-root", str(root), "--dry-run"])


def snapshot_path(root: Path, rev: int) -> Path:
    return root / "snapshots" / f"{STORY_ID}.v1.rev{rev}.json"


def read_snapshot(root: Path, rev: int = 1) -> dict:
    return json.loads(snapshot_path(root, rev).read_text(encoding="utf-8"))


def standard_log() -> list:
    return [
        event("git.commit", ts="2026-07-10T10:01:00+05:30"),
        event("git.commit", ts="2026-07-10T10:05:00+05:30"),
        event("git.checkout", ts="2026-07-10T10:02:00+05:30"),
        event("git.merge", ts="2026-07-10T10:06:00+05:30"),
        event("ai.claude-code.session_start", ts="2026-07-10T10:00:30+05:30", session_id="s1"),
        event("ai.claude-code.tool_use", session_id="s1", tool_name="Bash"),
        event("ai.claude-code.tool_use", session_id="s1", tool_name="Edit"),
        event("ai.claude-code.tool_use", session_id="s1", tool_name="Read"),
        event("ai.claude-code.prompt", session_id="s1", prompt_chars=12),
        event("ai.claude-code.prompt", session_id="s1", prompt_chars=40),
        event(
            "ai.claude-code.session_end",
            ts="2026-07-10T10:09:00+05:30",
            session_id="s1",
            input_tokens=None,
            output_tokens=None,
            token_cost_reason="no transcript_path in hook payload",
        ),
    ]


def test_envelope_has_exactly_the_nine_ad3a_keys(tmp_path, capsys):
    write_manifest(tmp_path)
    write_events(tmp_path, standard_log())

    exit_code = run(tmp_path)

    assert exit_code == 0
    snapshot = read_snapshot(tmp_path)
    assert set(snapshot.keys()) == ENVELOPE_KEYS
    assert snapshot["schema_version"] == 1
    assert snapshot["story_id"] == STORY_ID
    assert snapshot["revision"] == 1


def test_engineering_metrics_reduce_the_log(tmp_path, capsys):
    write_manifest(tmp_path)
    write_events(tmp_path, standard_log())

    run(tmp_path)

    metrics = read_snapshot(tmp_path)["engineering_metrics"]
    assert metrics["commits"] == 2
    assert metrics["checkouts"] == 1
    assert metrics["merges"] == 1
    assert metrics["ai_sessions"] == 1
    assert metrics["tool_uses"] == 3
    assert metrics["prompts"] == 2
    assert metrics["event_count"] == 11
    assert metrics["first_event_at"] == "2026-07-10T10:00:00+05:30"  # the default-ts events
    assert metrics["last_event_at"] == "2026-07-10T10:09:00+05:30"


def test_pm_metrics_come_from_the_manifest(tmp_path, capsys):
    write_manifest(tmp_path)
    write_events(tmp_path, standard_log())

    run(tmp_path)

    pm = read_snapshot(tmp_path)["pm_metrics"]
    assert pm["points"] == 5
    assert pm["goal"] == "Close the loop"
    assert pm["sprint"] == "S3"
    assert pm["source_of_truth"] == "docs-only"
    assert pm["ai_tool"] == "claude-code"
    assert pm["name"] is None  # write_manifest() doesn't set one, matching JIRA/Confluence stories


def test_pm_metrics_name_round_trips_from_the_manifest(tmp_path, capsys):
    write_manifest(tmp_path)
    (tmp_path / ".story.yaml").write_text(
        (tmp_path / ".story.yaml").read_text(encoding="utf-8") + 'name: "Hello World"\n',
        encoding="utf-8",
    )
    write_events(tmp_path, [])

    run(tmp_path)

    assert read_snapshot(tmp_path)["pm_metrics"]["name"] == "Hello World"


def test_story_point_cost_keys_present_with_null_phase1_when_no_estimate(tmp_path, capsys):
    write_manifest(tmp_path)  # points_estimated defaults to None (no Story 2.5 estimate)
    write_events(tmp_path, standard_log())

    run(tmp_path)

    cost = read_snapshot(tmp_path)["story_point_cost"]
    assert set(cost.keys()) == {
        "phase1_points",
        "phase2_points",
        "variance",
        "reduced_confidence",
        "reduced_confidence_reasons",
    }
    assert cost["phase1_points"] is None
    assert cost["variance"] is None  # can't diff against a null phase1


def test_reduced_confidence_is_always_true_today_no_decision_producer(tmp_path, capsys):
    write_manifest(tmp_path)
    write_events(tmp_path, standard_log())

    run(tmp_path)

    cost = read_snapshot(tmp_path)["story_point_cost"]
    assert cost["reduced_confidence"] is True
    assert any("decision" in r.lower() for r in cost["reduced_confidence_reasons"])


def test_review_cycles_from_prompt_count_follow_ups_only(tmp_path, capsys):
    write_manifest(tmp_path, points_estimated=5)
    # standard_log() has 2 prompt events -> 1 follow-up cycle
    write_events(tmp_path, standard_log())

    run(tmp_path)

    cost = read_snapshot(tmp_path)["story_point_cost"]
    # phase2 = review_cycles(1)*1.0 + verification_files(0, git mocked to None) + context(0)
    assert cost["phase2_points"] == 1
    assert cost["variance"] == 1 - 5


def test_single_prompt_yields_zero_review_cycles(tmp_path, capsys):
    write_manifest(tmp_path, points_estimated=0)
    write_events(tmp_path, [event("ai.claude-code.prompt", prompt_chars=3)])

    run(tmp_path)

    assert read_snapshot(tmp_path)["story_point_cost"]["phase2_points"] == 0


def test_zero_prompts_yields_zero_review_cycles_not_negative(tmp_path, capsys):
    write_manifest(tmp_path, points_estimated=0)
    write_events(tmp_path, [event("git.commit")])

    run(tmp_path)

    assert read_snapshot(tmp_path)["story_point_cost"]["phase2_points"] == 0


def test_verification_and_context_files_from_git_show_stat(tmp_path, monkeypatch, capsys):
    write_manifest(tmp_path, points_estimated=2)
    write_events(
        tmp_path,
        [
            event("git.commit", hash="abc123"),
            event("ai.claude-code.prompt", prompt_chars=1),
        ],
    )
    stat_output = (
        " tests/adapters/test_thing.py | 10 ++++++++\n"
        " tools/adapters/thing.py      |  5 +++++\n"
        " 2 files changed, 15 insertions(+)\n"
    )
    monkeypatch.setattr(
        events,
        "git_out",
        lambda *args, **kwargs: stat_output if "abc123" in args else None,
    )

    run(tmp_path)

    cost = read_snapshot(tmp_path)["story_point_cost"]
    # review_cycles=0 (1 prompt) + verification_files(1)*1.0 + context_files(1)*0.2 = 1.2 -> round -> 1
    assert cost["phase2_points"] == round(0 * 1.0 + 1 * 1.0 + 1 * 0.2)
    assert cost["variance"] == cost["phase2_points"] - 2


def test_git_show_is_run_with_cwd_pinned_to_repo_root(tmp_path, monkeypatch, capsys):
    # Regression: the assembler is explicitly addressed by --repo-root, which may
    # differ from the ambient process cwd (§3) — git_out() must be called with
    # cwd=root, or `git show` silently runs against the wrong repository.
    write_manifest(tmp_path, points_estimated=0)
    write_events(tmp_path, [event("git.commit", hash="abc123")])
    seen_cwd = []

    def fake_git_out(*args, cwd=None):
        seen_cwd.append(cwd)
        return None

    monkeypatch.setattr(events, "git_out", fake_git_out)

    run(tmp_path)

    assert seen_cwd == [tmp_path]


def test_binary_file_stat_lines_are_counted_as_context_files(tmp_path, monkeypatch, capsys):
    write_manifest(tmp_path, points_estimated=0)
    write_events(tmp_path, [event("git.commit", hash="abc123")])
    stat_output = (
        " assets/logo.png | Bin 0 -> 4521 bytes\n 1 file changed, 0 insertions(+), 0 deletions(-)\n"
    )
    monkeypatch.setattr(
        events,
        "git_out",
        lambda *args, **kwargs: stat_output if "abc123" in args else None,
    )

    run(tmp_path)

    cost = read_snapshot(tmp_path)["story_point_cost"]
    # 1 context file (binary, no "test" in path) * 0.2 -> round(0.2) -> 0
    assert cost["phase2_points"] == round(1 * 0.2)


def test_unresolvable_commit_hash_is_skipped_not_fatal(tmp_path, monkeypatch, capsys):
    write_manifest(tmp_path, points_estimated=0)
    write_events(tmp_path, [event("git.commit", hash="deadbeef")])
    monkeypatch.setattr(
        events, "git_out", lambda *args, **kwargs: None
    )  # simulates unresolvable/no git

    exit_code = run(tmp_path)

    assert exit_code == 0
    # commit still counted in engineering_metrics even though its stat contribution is skipped
    assert read_snapshot(tmp_path)["engineering_metrics"]["commits"] == 1
    assert read_snapshot(tmp_path)["story_point_cost"]["phase2_points"] == 0


def test_phase1_points_sourced_from_manifest_points_estimated(tmp_path, capsys):
    write_manifest(tmp_path, points_estimated=8)
    write_events(tmp_path, [])

    run(tmp_path)

    assert read_snapshot(tmp_path)["story_point_cost"]["phase1_points"] == 8


def test_fractional_points_estimated_is_preserved(tmp_path, capsys):
    write_manifest(tmp_path, points_estimated=6.5)
    write_events(tmp_path, [])

    run(tmp_path)

    assert read_snapshot(tmp_path)["story_point_cost"]["phase1_points"] == 6.5


def test_token_cost_null_with_reason_propagates(tmp_path, capsys):
    write_manifest(tmp_path)
    write_events(tmp_path, standard_log())

    run(tmp_path)

    token_cost = read_snapshot(tmp_path)["token_cost"]
    assert token_cost["input_tokens"] is None
    assert token_cost["output_tokens"] is None
    assert token_cost["reason"] == "no transcript_path in hook payload"
    assert token_cost["sessions_observed"] == 1
    assert token_cost["cost_usd"] is None


def test_token_cost_reason_explains_zero_sessions_observed(tmp_path, capsys):
    write_manifest(tmp_path)
    write_events(
        tmp_path,
        [
            event("git.commit", ts="2026-07-10T10:01:00+05:30"),
            event("ai.claude-code.session_start", ts="2026-07-10T10:00:30+05:30", session_id="s1"),
            # no matching session_end -- e.g. the developer closed the editor
            # abruptly instead of running /exit or Ctrl+C first
        ],
    )

    run(tmp_path)

    token_cost = read_snapshot(tmp_path)["token_cost"]
    assert token_cost["input_tokens"] is None
    assert token_cost["output_tokens"] is None
    assert token_cost["sessions_observed"] == 0
    assert token_cost["reason"]
    assert token_cost["reason"] != "no transcript_path in hook payload"


def test_token_cost_sums_real_tokens_across_sessions(tmp_path, capsys):
    write_manifest(tmp_path)
    write_events(
        tmp_path,
        [
            event(
                "ai.claude-code.session_end",
                session_id="s1",
                input_tokens=100,
                output_tokens=20,
                token_cost_reason=None,
            ),
            event(
                "ai.claude-code.session_end",
                session_id="s2",
                input_tokens=50,
                output_tokens=10,
                token_cost_reason=None,
            ),
        ],
    )

    run(tmp_path)

    token_cost = read_snapshot(tmp_path)["token_cost"]
    assert token_cost["input_tokens"] == 150
    assert token_cost["output_tokens"] == 30
    assert token_cost["sessions_observed"] == 2


def test_cost_usd_computed_when_tokens_and_rates_are_both_known(tmp_path, capsys):
    write_manifest(tmp_path)
    write_story_config(tmp_path, ai_input_rate=1.25, ai_output_rate=5.00)
    write_events(
        tmp_path,
        [
            event(
                "ai.claude-code.session_end",
                session_id="s1",
                input_tokens=180000,
                output_tokens=18000,
                token_cost_reason=None,
            ),
        ],
    )

    run(tmp_path)

    token_cost = read_snapshot(tmp_path)["token_cost"]
    assert token_cost["cost_usd"] == pytest.approx(0.315)


def test_cost_usd_is_null_when_rates_are_not_configured(tmp_path, capsys):
    write_manifest(tmp_path)
    write_events(
        tmp_path,
        [
            event(
                "ai.claude-code.session_end",
                session_id="s1",
                input_tokens=180000,
                output_tokens=18000,
                token_cost_reason=None,
            ),
        ],
    )

    run(tmp_path)

    assert read_snapshot(tmp_path)["token_cost"]["cost_usd"] is None


def test_reason_is_not_shown_when_a_later_session_has_real_tokens(tmp_path, capsys):
    # Found via live E2E (Story 5.2): a session that failed to report tokens must
    # never leave a stale "reason" visible once another session's real tokens make
    # input_tokens/output_tokens non-null overall.
    write_manifest(tmp_path)
    write_events(
        tmp_path,
        [
            event(
                "ai.claude-code.session_end",
                session_id="s1",
                input_tokens=None,
                output_tokens=None,
                token_cost_reason="no transcript_path in hook payload",
            ),
            event(
                "ai.claude-code.session_end",
                session_id="s2",
                input_tokens=7111,
                output_tokens=500,
                token_cost_reason=None,
            ),
        ],
    )

    run(tmp_path)

    token_cost = read_snapshot(tmp_path)["token_cost"]
    assert token_cost["input_tokens"] == 7111
    assert token_cost["output_tokens"] == 500
    assert token_cost["reason"] is None


def test_cost_usd_is_null_when_tokens_are_unknown_even_with_rates_configured(tmp_path, capsys):
    write_manifest(tmp_path)
    write_story_config(tmp_path, ai_input_rate=1.25, ai_output_rate=5.00)
    write_events(tmp_path, standard_log())

    run(tmp_path)

    assert read_snapshot(tmp_path)["token_cost"]["cost_usd"] is None


def test_estimated_cost_computed_when_hourly_rate_is_configured(tmp_path, capsys):
    write_manifest(tmp_path)
    write_story_config(tmp_path, hourly_rate=10)
    write_events(
        tmp_path,
        [
            event("git.commit", ts="2026-07-10T10:00:00+05:30"),
            event("git.commit", ts="2026-07-10T10:30:00+05:30"),
        ],
    )

    run(tmp_path)

    estimated_cost = read_snapshot(tmp_path)["estimated_cost"]
    assert estimated_cost["duration_minutes"] == pytest.approx(30.0)
    assert estimated_cost["usd"] == pytest.approx(5.0)
    assert estimated_cost["hourly_rate"] == 10
    assert estimated_cost["reason"] is None


def test_estimated_cost_is_null_with_reason_when_hourly_rate_absent(tmp_path, capsys):
    write_manifest(tmp_path)
    write_events(
        tmp_path,
        [
            event("git.commit", ts="2026-07-10T10:00:00+05:30"),
            event("git.commit", ts="2026-07-10T10:30:00+05:30"),
        ],
    )

    run(tmp_path)

    estimated_cost = read_snapshot(tmp_path)["estimated_cost"]
    assert estimated_cost["usd"] is None
    assert estimated_cost["hourly_rate"] is None
    assert isinstance(estimated_cost["reason"], str) and estimated_cost["reason"]


def test_estimated_cost_is_null_when_no_events_exist_even_with_hourly_rate(tmp_path, capsys):
    write_manifest(tmp_path)
    write_story_config(tmp_path, hourly_rate=10)
    write_events(tmp_path, [])

    run(tmp_path)

    estimated_cost = read_snapshot(tmp_path)["estimated_cost"]
    assert estimated_cost["duration_minutes"] is None
    assert estimated_cost["usd"] is None


def test_estimated_cost_degrades_gracefully_on_offset_naive_vs_aware_timestamps(tmp_path, capsys):
    # Review finding (PR #26): subtracting an offset-naive datetime from an
    # offset-aware one raises TypeError, not ValueError - a hand-edited or
    # corrupted event log could produce exactly this mix. Must not crash.
    write_manifest(tmp_path)
    write_story_config(tmp_path, hourly_rate=10)
    write_events(
        tmp_path,
        [
            event("git.commit", ts="2026-07-10T10:00:00"),  # naive - no offset
            event("git.commit", ts="2026-07-10T10:30:00+05:30"),  # aware
        ],
    )

    exit_code = run(tmp_path)

    assert exit_code == 0
    estimated_cost = read_snapshot(tmp_path)["estimated_cost"]
    assert estimated_cost["duration_minutes"] is None
    assert estimated_cost["usd"] is None


def test_active_time_seconds_of_sums_idle_excluded_duration_across_slices():
    events = [
        event(
            "time.slice_opened",
            ts="2026-07-10T10:00:00+05:30",
            opened_at="2026-07-10T10:00:00+05:30",
        ),
        event(
            "time.slice_paused",
            ts="2026-07-10T10:05:00+05:30",
            quiet_since="2026-07-10T09:45:00+05:30",
            resumed_at="2026-07-10T10:05:00+05:30",
            idle_seconds=300,
        ),
        event(
            "time.slice_closed",
            ts="2026-07-10T10:10:00+05:30",
            opened_at="2026-07-10T10:00:00+05:30",
            closed_at="2026-07-10T10:10:00+05:30",
            duration_seconds=600,
        ),
        # a second, later run for the same story
        event(
            "time.slice_opened",
            ts="2026-07-10T14:00:00+05:30",
            opened_at="2026-07-10T14:00:00+05:30",
        ),
        event(
            "time.slice_closed",
            ts="2026-07-10T14:05:00+05:30",
            opened_at="2026-07-10T14:00:00+05:30",
            closed_at="2026-07-10T14:05:00+05:30",
            duration_seconds=300,
        ),
    ]

    result = assembler.active_time_seconds_of(events)

    # first run: 600s duration - 300s idle = 300s; second run: 300s, no idle
    assert result["active_seconds"] == pytest.approx(600.0)
    assert result["reason"] is None


def test_active_time_seconds_of_null_with_reason_when_no_slice_closed():
    events = [event("git.commit"), event("ai.claude-code.tool_use", tool_name="Bash")]

    result = assembler.active_time_seconds_of(events)

    assert result["active_seconds"] is None
    assert isinstance(result["reason"], str) and result["reason"]


def test_active_time_seconds_of_ignores_dangling_open_slice():
    events = [
        event(
            "time.slice_opened",
            ts="2026-07-10T10:00:00+05:30",
            opened_at="2026-07-10T10:00:00+05:30",
        ),
        event(
            "time.slice_closed",
            ts="2026-07-10T10:10:00+05:30",
            opened_at="2026-07-10T10:00:00+05:30",
            closed_at="2026-07-10T10:10:00+05:30",
            duration_seconds=600,
        ),
        # a second run that never closed - session still open at story-close time
        event(
            "time.slice_opened",
            ts="2026-07-10T14:00:00+05:30",
            opened_at="2026-07-10T14:00:00+05:30",
        ),
    ]

    result = assembler.active_time_seconds_of(events)

    # only the completed first run counts; the dangling second run contributes 0
    assert result["active_seconds"] == pytest.approx(600.0)
    assert result["reason"] is None


def test_active_time_seconds_of_degrades_malformed_duration_to_zero_without_raising():
    events = [
        event(
            "time.slice_closed",
            ts="2026-07-10T10:10:00+05:30",
            opened_at="2026-07-10T10:00:00+05:30",
            closed_at="2026-07-10T10:10:00+05:30",
            duration_seconds="not-a-number",
        ),
    ]

    result = assembler.active_time_seconds_of(events)

    assert result["active_seconds"] == pytest.approx(0.0)
    assert result["reason"] is None


def test_estimated_cost_uses_active_time_when_time_slices_present(tmp_path, capsys):
    write_manifest(tmp_path)
    write_story_config(tmp_path, hourly_rate=10)
    write_events(
        tmp_path,
        [
            # raw first/last-event span would be 4 hours (10:00 to 14:00) -
            # active time (idle-excluded) should be used instead: 10 minutes
            event("git.commit", ts="2026-07-10T10:00:00+05:30"),
            event(
                "time.slice_opened",
                ts="2026-07-10T10:00:00+05:30",
                opened_at="2026-07-10T10:00:00+05:30",
            ),
            event(
                "time.slice_closed",
                ts="2026-07-10T10:10:00+05:30",
                opened_at="2026-07-10T10:00:00+05:30",
                closed_at="2026-07-10T10:10:00+05:30",
                duration_seconds=600,
            ),
            event("git.commit", ts="2026-07-10T14:00:00+05:30"),
        ],
    )

    run(tmp_path)

    estimated_cost = read_snapshot(tmp_path)["estimated_cost"]
    assert estimated_cost["duration_minutes"] == pytest.approx(10.0)
    assert estimated_cost["usd"] == pytest.approx(10 * (10.0 / 60))
    assert estimated_cost["reason"] is None


def test_estimated_cost_falls_back_to_raw_span_when_no_time_slices(tmp_path, capsys):
    # unchanged pre-Story-3.4 behavior: no time.slice_* events at all
    write_manifest(tmp_path)
    write_story_config(tmp_path, hourly_rate=10)
    write_events(
        tmp_path,
        [
            event("git.commit", ts="2026-07-10T10:00:00+05:30"),
            event("git.commit", ts="2026-07-10T10:30:00+05:30"),
        ],
    )

    run(tmp_path)

    estimated_cost = read_snapshot(tmp_path)["estimated_cost"]
    assert estimated_cost["duration_minutes"] == pytest.approx(30.0)
    assert estimated_cost["usd"] == pytest.approx(5.0)
    assert estimated_cost["reason"] is None


def test_foreign_story_events_are_excluded(tmp_path, capsys):
    write_manifest(tmp_path)
    log = standard_log() + [event("git.commit", story_id="story-other-999")]
    write_events(tmp_path, log)

    run(tmp_path)

    metrics = read_snapshot(tmp_path)["engineering_metrics"]
    assert metrics["commits"] == 2
    assert metrics["event_count"] == 11


def test_malformed_lines_are_skipped_with_warning_not_fatal(tmp_path, capsys):
    write_manifest(tmp_path)
    write_events(tmp_path, standard_log())
    with open(tmp_path / ".story-events.jsonl", "a", encoding="utf-8") as f:
        f.write("{not json at all\n")

    exit_code = run(tmp_path)

    assert exit_code == 0
    assert read_snapshot(tmp_path)["engineering_metrics"]["event_count"] == 11
    assert "malformed" in capsys.readouterr().err.lower()


def test_second_close_creates_rev2_and_rev1_survives_byte_identical(tmp_path, capsys):
    write_manifest(tmp_path)
    write_events(tmp_path, standard_log())
    run(tmp_path)
    rev1_bytes = snapshot_path(tmp_path, 1).read_bytes()

    exit_code = run(tmp_path)

    assert exit_code == 0
    assert read_snapshot(tmp_path, rev=2)["revision"] == 2
    assert snapshot_path(tmp_path, 1).read_bytes() == rev1_bytes


def test_pre_existing_target_revision_is_refused(tmp_path, capsys, monkeypatch):
    write_manifest(tmp_path)
    write_events(tmp_path, standard_log())
    (tmp_path / "snapshots").mkdir()
    snapshot_path(tmp_path, 1).write_text("forged", encoding="utf-8")
    monkeypatch.setattr(assembler, "next_revision", lambda *a, **k: 1)

    exit_code = run(tmp_path)

    assert exit_code == 2
    assert snapshot_path(tmp_path, 1).read_text(encoding="utf-8") == "forged"


def test_pending_events_are_backfilled_included_and_spool_removed(tmp_path, capsys):
    write_manifest(tmp_path)
    write_events(tmp_path, standard_log())
    write_events(
        tmp_path,
        [
            event("git.commit", story_id=None),
            event("ai.claude-code.prompt", story_id=None, prompt_chars=7),
        ],
        pending=True,
    )

    exit_code = run(tmp_path)

    assert exit_code == 0
    metrics = read_snapshot(tmp_path)["engineering_metrics"]
    assert metrics["commits"] == 3
    assert metrics["prompts"] == 3
    assert not (tmp_path / ".story-events.pending.jsonl").exists()
    main_log = [
        json.loads(line)
        for line in (tmp_path / ".story-events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    backfilled = [e for e in main_log if e["story_id"] == STORY_ID and e["type"] == "git.commit"]
    assert len(backfilled) == 3
    ack = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert ack["pending_backfilled"] == 2


def test_no_pending_spool_means_zero_backfilled(tmp_path, capsys):
    write_manifest(tmp_path)
    write_events(tmp_path, standard_log())

    run(tmp_path)

    ack = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert ack["pending_backfilled"] == 0
    assert ack["events_reduced"] == 11


def test_empty_log_still_produces_a_snapshot(tmp_path, capsys):
    write_manifest(tmp_path)

    exit_code = run(tmp_path)

    assert exit_code == 0
    metrics = read_snapshot(tmp_path)["engineering_metrics"]
    assert metrics["event_count"] == 0
    assert metrics["first_event_at"] is None
    assert metrics["last_event_at"] is None


def test_missing_manifest_exits_2_and_writes_nothing(tmp_path, capsys):
    write_events(tmp_path, standard_log())

    exit_code = run(tmp_path)

    assert exit_code == 2


# --- defect_metrics (Story 5.4) ---


def test_defect_metrics_null_with_reason_when_no_defect_events_logged(tmp_path, capsys):
    write_manifest(tmp_path)
    write_events(tmp_path, standard_log())  # no ai.claude-code.defect_* events

    run(tmp_path)

    defects = read_snapshot(tmp_path)["defect_metrics"]
    assert defects["total_defects"] is None
    assert defects["compile_defects"] is None
    assert defects["test_defects"] is None
    assert defects["review_defects"] is None
    assert defects["testing_efficiency"] is None
    assert defects["review_efficiency"] is None
    assert isinstance(defects["reason"], str) and defects["reason"]


def test_defect_metrics_counts_and_efficiencies_with_a_mix_of_defects(tmp_path, capsys):
    write_manifest(tmp_path)
    write_events(
        tmp_path,
        [
            event("ai.claude-code.defect_compile", matched_pattern="tsc --noEmit"),
            event("ai.claude-code.defect_test", matched_pattern="pytest"),
            event("ai.claude-code.defect_test", matched_pattern="pytest"),
            event("ai.claude-code.defect_review", summary="s", description="d", points=1),
        ],
    )

    run(tmp_path)

    defects = read_snapshot(tmp_path)["defect_metrics"]
    assert defects["total_defects"] == 4
    assert defects["compile_defects"] == 1
    assert defects["test_defects"] == 2
    assert defects["review_defects"] == 1
    assert defects["testing_efficiency"] == pytest.approx(75.0)  # (1 + 2) / 4 * 100
    assert defects["review_efficiency"] == pytest.approx(25.0)  # 1 / 4 * 100
    assert defects["reason"] is None


def test_defect_metrics_all_compile_and_test_no_review(tmp_path, capsys):
    write_manifest(tmp_path)
    write_events(
        tmp_path,
        [
            event("ai.claude-code.defect_compile", matched_pattern="ruff check"),
            event("ai.claude-code.defect_test", matched_pattern="pytest"),
        ],
    )

    run(tmp_path)

    defects = read_snapshot(tmp_path)["defect_metrics"]
    assert defects["total_defects"] == 2
    assert defects["testing_efficiency"] == pytest.approx(100.0)
    assert defects["review_efficiency"] == pytest.approx(0.0)


# --- Story 2.12: --dry-run mode ---------------------------------------------


def test_dry_run_prints_full_snapshot_without_writing_file(tmp_path, capsys):
    write_manifest(tmp_path)
    write_events(tmp_path, standard_log())

    exit_code = run_dry(tmp_path)

    assert exit_code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert out["dry_run"] is True
    assert out["events_reduced"] == 11
    assert out["would_be_revision"] == 1
    snapshot = out["snapshot"]
    assert set(snapshot.keys()) == ENVELOPE_KEYS
    assert snapshot["story_id"] == STORY_ID
    assert snapshot["revision"] == 1
    assert snapshot["engineering_metrics"]["commits"] == 2
    assert not (tmp_path / "snapshots").exists()


def test_real_run_ack_shape_is_unchanged_by_dry_run_addition(tmp_path, capsys):
    write_manifest(tmp_path)
    write_events(tmp_path, standard_log())

    exit_code = run(tmp_path)

    assert exit_code == 0
    ack = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert set(ack.keys()) == {"ok", "snapshot", "revision", "events_reduced", "pending_backfilled"}
    assert isinstance(ack["snapshot"], str)
    assert "dry_run" not in ack


def test_dry_run_leaves_pending_spool_untouched(tmp_path, capsys):
    write_manifest(tmp_path)
    write_events(tmp_path, standard_log())
    write_events(tmp_path, [event("git.commit", story_id=None)], pending=True)

    exit_code = run_dry(tmp_path)

    assert exit_code == 0
    pending_path = tmp_path / ".story-events.pending.jsonl"
    assert pending_path.exists()
    main_log_lines = (tmp_path / ".story-events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(main_log_lines) == len(standard_log())  # nothing appended from the spool
    out = json.loads(capsys.readouterr().out)
    # the pending event is read and reduced-from (computation still sees it)...
    assert out["snapshot"]["engineering_metrics"]["commits"] == 3
    # ...but never actually consumed/deleted


def test_dry_run_then_real_run_matches_real_run_alone(tmp_path, capsys):
    with_dry_run = tmp_path / "with-dry-run"
    without_dry_run = tmp_path / "without-dry-run"
    with_dry_run.mkdir()
    without_dry_run.mkdir()
    for root in (with_dry_run, without_dry_run):
        write_manifest(root)
        write_events(root, standard_log())
        write_events(root, [event("git.commit", story_id=None)], pending=True)

    run_dry(with_dry_run)
    capsys.readouterr()  # discard the dry-run preview output
    run(with_dry_run)
    ack_with = json.loads(capsys.readouterr().out.strip().splitlines()[-1])

    run(without_dry_run)
    ack_without = json.loads(capsys.readouterr().out.strip().splitlines()[-1])

    assert ack_with["pending_backfilled"] == ack_without["pending_backfilled"] == 1
    assert read_snapshot(with_dry_run) == read_snapshot(without_dry_run)


def test_dry_run_degraded_signal_parity_with_written_snapshot(tmp_path, capsys):
    write_manifest(tmp_path)
    write_events(tmp_path, standard_log())

    dry_exit = run_dry(tmp_path)
    dry_out = json.loads(capsys.readouterr().out)
    real_exit = run(tmp_path)
    written = read_snapshot(tmp_path)

    assert dry_exit == 0
    assert real_exit == 0
    assert dry_out["snapshot"]["token_cost"] == written["token_cost"]
    assert dry_out["snapshot"]["defect_metrics"] == written["defect_metrics"]
    assert dry_out["snapshot"]["story_point_cost"] == written["story_point_cost"]
    assert dry_out["snapshot"]["estimated_cost"] == written["estimated_cost"]
