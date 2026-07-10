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
}


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
        else ("ai" if event_type.startswith("ai.") else "opsx")
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
            token_cost=None,
            token_cost_reason="claude-code hooks do not report token usage",
        ),
    ]


def test_envelope_has_exactly_the_seven_ad3a_keys(tmp_path, capsys):
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
    assert token_cost["total_tokens"] is None
    assert token_cost["reason"] == "claude-code hooks do not report token usage"
    assert token_cost["sessions_observed"] == 1


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
    assert not (tmp_path / "snapshots").exists()
