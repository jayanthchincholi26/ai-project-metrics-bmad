"""Tests for the Claude Code event producers (Story 2.3, AC 1-3)."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HOOKS_ROOT = REPO / "tools" / "hooks"
CLAUDE_DIR = HOOKS_ROOT / "claude"


def load(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


events = load("_events", HOOKS_ROOT / "_events.py")
session_start = load("hook_session_start", CLAUDE_DIR / "session_start.py")
session_end = load("hook_session_end", CLAUDE_DIR / "session_end.py")
pre_tool_use = load("hook_pre_tool_use", CLAUDE_DIR / "pre_tool_use.py")
post_tool_use = load("hook_post_tool_use", CLAUDE_DIR / "post_tool_use.py")
user_prompt_submit = load("hook_user_prompt_submit", CLAUDE_DIR / "user_prompt_submit.py")
stop = load("hook_stop", CLAUDE_DIR / "stop.py")

ALL_HOOKS = (session_start, session_end, pre_tool_use, post_tool_use, user_prompt_submit, stop)
STORY_ID = "story-20260710-claude1"


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(events, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(events, "RETRY_DELAY_SECONDS", 0)
    (tmp_path / ".story.yaml").write_text(f'story_id: "{STORY_ID}"\n', encoding="utf-8")
    return tmp_path


def feed_stdin(monkeypatch, data: dict) -> None:
    monkeypatch.setattr(events, "read_stdin_json", lambda: data)


def read_events(repo_root: Path, pending: bool = False) -> list[dict]:
    name = ".story-events.pending.jsonl" if pending else ".story-events.jsonl"
    path = repo_root / name
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_session_start_carries_ai_envelope(repo, monkeypatch):
    feed_stdin(monkeypatch, {"session_id": "s-1"})

    exit_code = session_start.main([])

    assert exit_code == 0
    (event,) = read_events(repo)
    assert set(event.keys()) == {"story_id", "source", "type", "timestamp", "payload"}
    assert event["source"] == "ai"
    assert event["type"] == "ai.claude-code.session_start"
    assert event["story_id"] == STORY_ID
    assert event["payload"]["session_id"] == "s-1"


def test_event_types_are_namespaced_per_hook(repo, monkeypatch):
    feed_stdin(monkeypatch, {"session_id": "s-1", "tool_name": "Bash", "prompt": "hi"})

    for hook in ALL_HOOKS:
        hook.main([])

    types = [event["type"] for event in read_events(repo)]
    assert types == [
        "ai.claude-code.session_start",
        "ai.claude-code.session_end",
        "ai.claude-code.tool_start",
        "ai.claude-code.tool_use",
        "ai.claude-code.prompt",
        "ai.claude-code.stop",
    ]


def test_session_end_token_cost_is_null_with_reason(repo, monkeypatch):
    feed_stdin(monkeypatch, {"session_id": "s-1"})

    session_end.main([])

    (event,) = read_events(repo)
    payload = event["payload"]
    assert payload["token_cost"] is None
    assert isinstance(payload["token_cost_reason"], str) and payload["token_cost_reason"]


def test_tool_events_carry_tool_name_but_never_tool_input(repo, monkeypatch):
    secret = "aws_key=AKIA-SUPER-SECRET"
    feed_stdin(
        monkeypatch, {"session_id": "s-1", "tool_name": "Bash", "tool_input": {"command": secret}}
    )

    pre_tool_use.main([])
    post_tool_use.main([])

    raw = (repo / ".story-events.jsonl").read_text(encoding="utf-8")
    assert "AKIA-SUPER-SECRET" not in raw
    first, second = read_events(repo)
    assert first["payload"]["tool_name"] == "Bash"
    assert second["payload"]["tool_name"] == "Bash"


def test_prompt_event_carries_length_but_never_prompt_text(repo, monkeypatch):
    feed_stdin(monkeypatch, {"session_id": "s-1", "prompt": "my proprietary secret plan"})

    user_prompt_submit.main([])

    raw = (repo / ".story-events.jsonl").read_text(encoding="utf-8")
    assert "proprietary secret plan" not in raw
    (event,) = read_events(repo)
    assert event["payload"]["prompt_chars"] == len("my proprietary secret plan")


def test_missing_prompt_yields_null_chars_not_zero(repo, monkeypatch):
    feed_stdin(monkeypatch, {"session_id": "s-1"})

    user_prompt_submit.main([])

    (event,) = read_events(repo)
    assert event["payload"]["prompt_chars"] is None


def test_empty_stdin_yields_null_fields_but_event_still_emitted(repo, monkeypatch):
    feed_stdin(monkeypatch, {})

    exit_code = session_start.main([])

    assert exit_code == 0
    (event,) = read_events(repo)
    assert event["payload"]["session_id"] is None


def test_read_stdin_json_strips_powershell_bom(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("\ufeff" + '{"session_id": "sess-42"}\n'))

    assert events.read_stdin_json() == {"session_id": "sess-42"}


def test_read_stdin_json_strips_cp1252_mojibake_bom(monkeypatch):
    # Windows locale-decoded stdin turns the UTF-8 BOM bytes into three mojibake chars.
    mojibake_bom = "\u00ef\u00bb\u00bf"
    monkeypatch.setattr(sys, "stdin", io.StringIO(mojibake_bom + '{"session_id": "sess-42"}\n'))

    assert events.read_stdin_json() == {"session_id": "sess-42"}


def test_read_stdin_json_tolerates_malformed_input(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("this is not json"))
    assert events.read_stdin_json() == {}

    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    assert events.read_stdin_json() == {}

    monkeypatch.setattr(sys, "stdin", io.StringIO('["a","list"]'))
    assert events.read_stdin_json() == {}


def test_pre_manifest_ai_event_is_buffered(repo, monkeypatch, tmp_path):
    (tmp_path / ".story.yaml").unlink()
    feed_stdin(monkeypatch, {"session_id": "s-1"})

    exit_code = stop.main([])

    assert exit_code == 0
    (event,) = read_events(repo, pending=True)
    assert event["story_id"] is None
    assert event["type"] == "ai.claude-code.stop"


def test_every_claude_hook_returns_0_even_on_total_append_failure(repo, monkeypatch, capsys):
    feed_stdin(monkeypatch, {"session_id": "s-1", "tool_name": "Bash", "prompt": "x"})

    def always_fail(path, line):
        raise OSError("disk unhappy")

    monkeypatch.setattr(events, "append_line", always_fail)

    for hook in ALL_HOOKS:
        assert hook.main([]) == 0, hook.__name__

    err = capsys.readouterr().err
    assert err.count("METRICS CAPTURE FAILED") == len(ALL_HOOKS)
