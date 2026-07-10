"""Tests for the git-side event producers (Story 2.2, AC 1-3). No real git operations."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HOOKS_ROOT = REPO / "tools" / "hooks"
HOOKS_DIR = HOOKS_ROOT / "git"


def load(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# _events (now shared at tools/hooks/, Story 2.3) must be registered in
# sys.modules before the hooks' `import _events` runs.
events = load("_events", HOOKS_ROOT / "_events.py")
post_commit = load("hook_post_commit", HOOKS_DIR / "post-commit.py")
post_checkout = load("hook_post_checkout", HOOKS_DIR / "post-checkout.py")
post_merge = load("hook_post_merge", HOOKS_DIR / "post-merge.py")
commit_msg = load("hook_commit_msg", HOOKS_DIR / "commit-msg.py")

STORY_ID = "story-20260710-abc123"
GIT_ANSWERS = {
    ("rev-parse", "HEAD"): "deadbeef",
    ("rev-parse", "--abbrev-ref", "HEAD"): "story/2.2-git-event-capture",
    ("log", "-1", "--format=%s"): "Implement the emitter",
}


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(events, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(events, "git_out", lambda *args: GIT_ANSWERS.get(args))
    monkeypatch.setattr(events, "RETRY_DELAY_SECONDS", 0)
    return tmp_path


def write_manifest(repo_root: Path) -> None:
    (repo_root / ".story.yaml").write_text(f'story_id: "{STORY_ID}"\n', encoding="utf-8")


def read_events(repo_root: Path, pending: bool = False) -> list[dict]:
    name = ".story-events.pending.jsonl" if pending else ".story-events.jsonl"
    path = repo_root / name
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_commit_event_carries_the_fixed_envelope(repo):
    write_manifest(repo)

    exit_code = post_commit.main([])

    assert exit_code == 0
    (event,) = read_events(repo)
    assert set(event.keys()) == {"story_id", "source", "type", "timestamp", "payload"}
    assert event["story_id"] == STORY_ID
    assert event["source"] == "git"
    assert event["type"] == "git.commit"


def test_two_events_append_two_lines(repo):
    write_manifest(repo)

    post_commit.main([])
    post_commit.main([])

    assert len(read_events(repo)) == 2


def test_event_lines_are_newline_terminated_json(repo):
    write_manifest(repo)

    post_commit.main([])

    raw = (repo / ".story-events.jsonl").read_text(encoding="utf-8")
    assert raw.endswith("\n")
    assert "\n" not in raw[:-1] or raw.count("\n") == 1


def test_timestamp_is_iso_with_offset(repo):
    import re

    write_manifest(repo)
    post_commit.main([])

    (event,) = read_events(repo)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}", event["timestamp"])


def test_pre_manifest_event_is_buffered_never_dropped(repo):
    exit_code = post_commit.main([])

    assert exit_code == 0
    assert read_events(repo) == []
    (event,) = read_events(repo, pending=True)
    assert event["story_id"] is None
    assert event["type"] == "git.commit"


def test_commit_payload_carries_hash_branch_and_subject(repo):
    write_manifest(repo)

    post_commit.main([])

    (event,) = read_events(repo)
    assert event["payload"] == {
        "hash": "deadbeef",
        "branch": "story/2.2-git-event-capture",
        "message_subject": "Implement the emitter",
    }


def test_git_failure_yields_null_payload_fields_but_event_still_emitted(repo, monkeypatch):
    monkeypatch.setattr(events, "git_out", lambda *args: None)
    write_manifest(repo)

    exit_code = post_commit.main([])

    assert exit_code == 0
    (event,) = read_events(repo)
    assert event["payload"] == {"hash": None, "branch": None, "message_subject": None}


def test_checkout_args_are_parsed_and_branch_flag_true(repo):
    write_manifest(repo)

    post_checkout.main(["oldhead", "newhead", "1"])

    (event,) = read_events(repo)
    assert event["type"] == "git.checkout"
    assert event["payload"]["previous_head"] == "oldhead"
    assert event["payload"]["new_head"] == "newhead"
    assert event["payload"]["branch_checkout"] is True


def test_checkout_file_flag_is_false_and_missing_args_are_null(repo):
    write_manifest(repo)

    post_checkout.main(["a", "b", "0"])
    post_checkout.main([])

    first, second = read_events(repo)
    assert first["payload"]["branch_checkout"] is False
    assert second["payload"]["previous_head"] is None
    assert second["payload"]["branch_checkout"] is False


def test_merge_squash_flag_is_captured(repo):
    write_manifest(repo)

    post_merge.main(["1"])

    (event,) = read_events(repo)
    assert event["type"] == "git.merge"
    assert event["payload"]["squash"] is True


def test_commit_msg_reads_first_non_comment_line(repo, tmp_path):
    write_manifest(repo)
    msg_file = tmp_path / "COMMIT_EDITMSG"
    msg_file.write_text("# comment from template\n\nActual subject line\nbody\n", encoding="utf-8")

    exit_code = commit_msg.main([str(msg_file)])

    assert exit_code == 0
    (event,) = read_events(repo)
    assert event["type"] == "git.commit_msg"
    assert event["payload"]["message_subject"] == "Actual subject line"


def test_commit_msg_missing_file_emits_null_subject_and_returns_0(repo):
    write_manifest(repo)

    exit_code = commit_msg.main([str(repo / "no-such-file")])

    assert exit_code == 0
    (event,) = read_events(repo)
    assert event["payload"]["message_subject"] is None


def failing_append(times: int, real):
    calls = {"n": 0}

    def fake(path, line):
        calls["n"] += 1
        if calls["n"] <= times:
            raise OSError("disk unhappy")
        real(path, line)

    return fake


def test_append_failing_twice_still_succeeds(repo, monkeypatch, capsys):
    write_manifest(repo)
    monkeypatch.setattr(events, "append_line", failing_append(2, events.append_line))

    exit_code = post_commit.main([])

    assert exit_code == 0
    assert len(read_events(repo)) == 1
    assert "METRICS CAPTURE FAILED" not in capsys.readouterr().err


def test_append_failing_three_times_succeeds_on_fourth_attempt(repo, monkeypatch, capsys):
    write_manifest(repo)
    monkeypatch.setattr(events, "append_line", failing_append(3, events.append_line))

    exit_code = post_commit.main([])

    assert exit_code == 0
    assert len(read_events(repo)) == 1


def test_append_failing_four_times_surfaces_visible_error(repo, monkeypatch, capsys):
    write_manifest(repo)
    monkeypatch.setattr(events, "append_line", failing_append(4, events.append_line))

    exit_code = post_commit.main([])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "METRICS CAPTURE FAILED" in captured.err
    assert "git.commit" in captured.err
    assert read_events(repo) == []


def test_commit_msg_total_failure_surfaces_but_never_blocks_the_commit(repo, monkeypatch, capsys):
    write_manifest(repo)
    monkeypatch.setattr(events, "append_line", failing_append(4, events.append_line))
    msg_file = repo / "COMMIT_EDITMSG"
    msg_file.write_text("subject\n", encoding="utf-8")

    exit_code = commit_msg.main([str(msg_file)])

    assert exit_code == 0
    assert "METRICS CAPTURE FAILED" in capsys.readouterr().err
