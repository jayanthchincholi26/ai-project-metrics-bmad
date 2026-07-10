"""Tests for the shared active-story pointer mechanics (Story 3.1, AC 1)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HOOKS_ROOT = REPO / "tools" / "hooks"

ACTIVE_STORY_FILE = ".active-story"


def load(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


events = load("_events", HOOKS_ROOT / "_events.py")


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(events, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(events, "RETRY_DELAY_SECONDS", 0)
    return tmp_path


def read_events(repo_root: Path, pending: bool = False) -> list[dict]:
    name = ".story-events.pending.jsonl" if pending else ".story-events.jsonl"
    path = repo_root / name
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def read_pointer(repo_root: Path) -> dict:
    return json.loads((repo_root / ACTIVE_STORY_FILE).read_text(encoding="utf-8"))


def test_first_ever_call_opens_a_slice_with_no_close_event(repo):
    events.update_active_story(repo, "story-a")

    pointer = read_pointer(repo)
    assert pointer["story_id"] == "story-a"
    assert pointer["opened_at"]

    all_events = read_events(repo)
    assert len(all_events) == 1
    assert all_events[0]["type"] == "time.slice_opened"
    assert all_events[0]["story_id"] == "story-a"


def test_switching_story_closes_outgoing_and_opens_incoming(repo):
    events.update_active_story(repo, "story-a")
    events.update_active_story(repo, "story-b")

    pointer = read_pointer(repo)
    assert pointer["story_id"] == "story-b"

    _, closed, opened = read_events(repo)
    assert closed["type"] == "time.slice_closed"
    assert closed["story_id"] == "story-a"
    assert isinstance(closed["payload"]["duration_seconds"], (int, float))
    assert closed["payload"]["duration_seconds"] >= 0

    assert opened["type"] == "time.slice_opened"
    assert opened["story_id"] == "story-b"


def test_same_story_id_is_a_no_op(repo):
    events.update_active_story(repo, "story-a")
    first_pointer_mtime = (repo / ACTIVE_STORY_FILE).stat().st_mtime_ns

    events.update_active_story(repo, "story-a")

    assert read_events(repo) == read_events(repo)  # sanity: still readable
    assert len(read_events(repo)) == 1  # no additional events appended
    assert (repo / ACTIVE_STORY_FILE).stat().st_mtime_ns == first_pointer_mtime
    assert read_pointer(repo)["story_id"] == "story-a"


def test_none_incoming_story_id_is_a_no_op(repo):
    events.update_active_story(repo, None)

    assert not (repo / ACTIVE_STORY_FILE).exists()
    assert read_events(repo) == []


def test_none_incoming_story_id_does_not_disturb_an_existing_pointer(repo):
    events.update_active_story(repo, "story-a")

    events.update_active_story(repo, None)

    assert read_pointer(repo)["story_id"] == "story-a"
    assert len(read_events(repo)) == 1
