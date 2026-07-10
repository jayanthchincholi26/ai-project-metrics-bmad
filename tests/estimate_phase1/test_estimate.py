"""Tests for the AD-6 Phase-1 story-point estimator (Story 2.5, AC 1-2)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "estimate-phase1" / "main.py"
_spec = importlib.util.spec_from_file_location("estimate_phase1", SCRIPT)
estimator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(estimator)

ACK_KEYS = {
    "ok",
    "phase1_points",
    "phase1_points_reason",
    "task_count",
    "base_points",
    "volatility_bonus",
    "novelty_modifier",
    "must_split",
    "change_dir",
}


def make_tasks_md(change_dir: Path, count: int) -> None:
    change_dir.mkdir(parents=True, exist_ok=True)
    lines = "\n".join(f"- [ ] Task {i}" for i in range(count))
    (change_dir / "tasks.md").write_text(lines + "\n", encoding="utf-8")


def run(root: Path, change_dir: "Path | None" = None) -> "tuple[int, dict]":
    argv = ["--repo-root", str(root)]
    if change_dir is not None:
        argv += ["--change-dir", str(change_dir)]
    import io
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exit_code = estimator.main(argv)
    out = buf.getvalue().strip().splitlines()
    ack = json.loads(out[-1]) if out else {}
    return exit_code, ack


def write_snapshot(root: Path, story_id: str, source_of_truth: str, points: int) -> None:
    snapshots = root / "snapshots"
    snapshots.mkdir(exist_ok=True)
    snapshot = {
        "schema_version": 1,
        "story_id": story_id,
        "revision": 1,
        "pm_metrics": {"points": points, "source_of_truth": source_of_truth},
        "engineering_metrics": {},
        "story_point_cost": {"phase1_points": None, "phase2_points": None, "variance": None},
        "token_cost": {},
    }
    (snapshots / f"{story_id}.v1.rev1.json").write_text(json.dumps(snapshot), encoding="utf-8")


def test_ack_always_has_all_keys(tmp_path):
    exit_code, ack = run(tmp_path)

    assert exit_code == 0
    assert set(ack.keys()) == ACK_KEYS


def test_no_change_dirs_yields_null_with_reason(tmp_path):
    exit_code, ack = run(tmp_path)

    assert exit_code == 0
    assert ack["phase1_points"] is None
    assert "no openspec change found" in ack["phase1_points_reason"]


def test_single_change_dir_is_auto_selected(tmp_path):
    change = tmp_path / "openspec" / "changes" / "add-thing"
    make_tasks_md(change, 3)

    exit_code, ack = run(tmp_path)

    assert exit_code == 0
    assert ack["phase1_points"] is not None
    assert "add-thing" in ack["change_dir"]


def test_multiple_change_dirs_without_override_exits_2(tmp_path, capsys):
    make_tasks_md(tmp_path / "openspec" / "changes" / "a", 3)
    make_tasks_md(tmp_path / "openspec" / "changes" / "b", 3)

    exit_code, _ = run(tmp_path)

    assert exit_code == 2
    err = capsys.readouterr().err
    assert "a" in err and "b" in err


def test_explicit_change_dir_overrides_auto_detection(tmp_path):
    make_tasks_md(tmp_path / "openspec" / "changes" / "a", 3)
    override = tmp_path / "openspec" / "changes" / "b"
    make_tasks_md(override, 10)

    exit_code, ack = run(tmp_path, change_dir=override)

    assert exit_code == 0
    assert ack["task_count"] == 10
    assert "b" in ack["change_dir"]


def test_change_dir_without_tasks_md_degrades_to_null(tmp_path):
    change = tmp_path / "openspec" / "changes" / "empty-change"
    change.mkdir(parents=True)

    exit_code, ack = run(tmp_path)

    assert exit_code == 0
    assert ack["phase1_points"] is None
    assert ack["phase1_points_reason"]


def test_base_points_bucket_boundaries(tmp_path):
    cases = [(5, 2), (6, 5), (15, 5), (16, 13), (30, 13), (31, 20)]
    for count, expected_base in cases:
        change = tmp_path / f"c{count}" / "openspec" / "changes" / "x"
        make_tasks_md(change, count)
        exit_code, ack = run(tmp_path / f"c{count}")
        assert exit_code == 0, count
        assert ack["base_points"] == expected_base, (count, ack)


def test_must_split_flag_set_only_above_30(tmp_path):
    make_tasks_md(tmp_path / "openspec" / "changes" / "x", 31)

    _, ack = run(tmp_path)

    assert ack["must_split"] is True


def test_must_split_false_at_boundary(tmp_path):
    make_tasks_md(tmp_path / "openspec" / "changes" / "x", 30)

    _, ack = run(tmp_path)

    assert ack["must_split"] is False


def test_volatility_bonus_by_artifact_count(tmp_path):
    cases = [
        (0, 5),
        (1, 3),
        (2, 2),
        (3, 0),
    ]
    artifacts = ["proposal.md", "design.md", "specs"]
    for present_count, expected_bonus in cases:
        root = tmp_path / f"v{present_count}"
        change = root / "openspec" / "changes" / "x"
        make_tasks_md(change, 3)
        for name in artifacts[:present_count]:
            if name == "specs":
                (change / "specs").mkdir(parents=True, exist_ok=True)
                (change / "specs" / "spec.md").write_text("x", encoding="utf-8")
            else:
                (change / name).write_text("x", encoding="utf-8")
        _, ack = run(root)
        assert ack["volatility_bonus"] == expected_bonus, (present_count, ack)


def test_novelty_first_time_when_no_snapshots(tmp_path):
    make_tasks_md(tmp_path / "openspec" / "changes" / "x", 3)

    _, ack = run(tmp_path)

    assert ack["novelty_modifier"] == 1.5


def test_novelty_standard_when_snapshots_have_different_source(tmp_path):
    make_tasks_md(tmp_path / "openspec" / "changes" / "x", 3)
    write_snapshot(tmp_path, "story-prior-1", "jira", points=2)

    _, ack = run(tmp_path)

    assert ack["novelty_modifier"] == 1.0


def test_novelty_reuse_when_snapshot_matches_source_and_bucket(tmp_path):
    make_tasks_md(tmp_path / "openspec" / "changes" / "x", 3)  # base bucket = 2
    write_snapshot(tmp_path, "story-prior-1", "docs-only", points=2)

    _, ack = run(tmp_path)

    assert ack["novelty_modifier"] == 0.8


def test_novelty_reuse_requires_matching_bucket_not_task_count_confusion(tmp_path):
    # Regression: a prior snapshot's recorded `points` (5) must be compared
    # directly against this estimate's base_points bucket value, never
    # re-interpreted as if it were a task count fed back through the
    # base-points formula (base_points_for(5) would wrongly yield 2).
    make_tasks_md(tmp_path / "openspec" / "changes" / "x", 8)  # base bucket = 5
    write_snapshot(tmp_path, "story-prior-1", "docs-only", points=5)

    _, ack = run(tmp_path)

    assert ack["base_points"] == 5
    assert ack["novelty_modifier"] == 0.8


def test_novelty_standard_when_snapshot_points_do_not_match_bucket(tmp_path):
    make_tasks_md(tmp_path / "openspec" / "changes" / "x", 8)  # base bucket = 5
    write_snapshot(tmp_path, "story-prior-1", "docs-only", points=13)

    _, ack = run(tmp_path)

    assert ack["novelty_modifier"] == 1.0


def test_full_combination_arithmetic(tmp_path):
    # 8 tasks -> base 5; 1 of 3 artifacts -> volatility 3; no snapshots -> novelty 1.5
    make_tasks_md(tmp_path / "openspec" / "changes" / "x", 8)
    (tmp_path / "openspec" / "changes" / "x" / "proposal.md").write_text("x", encoding="utf-8")

    _, ack = run(tmp_path)

    assert ack["base_points"] == 5
    assert ack["volatility_bonus"] == 3
    assert ack["novelty_modifier"] == 1.5
    assert ack["phase1_points"] == round((5 + 3) * 1.5)


def test_estimator_writes_no_files(tmp_path):
    make_tasks_md(tmp_path / "openspec" / "changes" / "x", 3)

    run(tmp_path)

    assert not (tmp_path / ".story.yaml").exists()
    assert not (tmp_path / ".story-events.jsonl").exists()


def test_missing_repo_root_exits_2(tmp_path):
    exit_code, _ = run(tmp_path / "does-not-exist")

    assert exit_code == 2
