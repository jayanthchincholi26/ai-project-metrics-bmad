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
    event = read_events(repo)[0]
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
        "time.slice_opened",
        "ai.claude-code.session_end",
        "time.slice_closed",
        "ai.claude-code.tool_start",
        "ai.claude-code.tool_use",
        "ai.claude-code.prompt",
        "ai.claude-code.stop",
    ]


def test_session_start_updates_the_active_story_pointer(repo, monkeypatch):
    feed_stdin(monkeypatch, {"session_id": "s-1"})

    session_start.main([])

    pointer = json.loads((repo / ".active-story").read_text(encoding="utf-8"))
    assert pointer["story_id"] == STORY_ID


def test_session_start_is_a_no_op_on_the_pointer_when_story_is_unchanged(repo, monkeypatch):
    feed_stdin(monkeypatch, {"session_id": "s-1"})
    session_start.main([])

    session_start.main([])

    types = [event["type"] for event in read_events(repo)]
    assert types.count("time.slice_opened") == 1


# --- mid-session checkout precedence (Story 3.3) ---


def test_session_start_marks_the_session_active(repo, monkeypatch):
    feed_stdin(monkeypatch, {"session_id": "s-1"})

    session_start.main([])

    assert events.is_session_active(repo) is True


def test_session_end_closes_the_slice_and_marks_the_session_inactive(repo, monkeypatch):
    feed_stdin(monkeypatch, {"session_id": "s-1"})
    session_start.main([])

    session_end.main([])

    assert not (repo / ".active-story").exists()
    assert events.is_session_active(repo) is False
    types = [event["type"] for event in read_events(repo)]
    assert types == [
        "ai.claude-code.session_start",
        "time.slice_opened",
        "ai.claude-code.session_end",
        "time.slice_closed",
    ]


def test_session_end_without_a_prior_pointer_is_a_clean_no_op_on_the_slice(repo, monkeypatch):
    feed_stdin(monkeypatch, {"session_id": "s-1"})

    exit_code = session_end.main([])

    assert exit_code == 0
    types = [event["type"] for event in read_events(repo)]
    assert "time.slice_closed" not in types


# --- idle detection wiring (Story 3.2) ---


def test_post_tool_use_records_activity_within_threshold_without_pausing(repo, monkeypatch):
    feed_stdin(monkeypatch, {"session_id": "s-1", "tool_name": "Bash"})
    monkeypatch.setattr(
        events, "_now", lambda: events.datetime.fromisoformat("2026-07-10T09:00:00+00:00")
    )
    session_start.main([])
    monkeypatch.setattr(
        events, "_now", lambda: events.datetime.fromisoformat("2026-07-10T09:05:00+00:00")
    )

    post_tool_use.main([])

    types = [event["type"] for event in read_events(repo)]
    assert "time.slice_paused" not in types
    pointer = json.loads((repo / ".active-story").read_text(encoding="utf-8"))
    assert pointer["last_activity_at"] == "2026-07-10T09:05:00+00:00"


def test_post_tool_use_emits_a_pause_after_an_idle_gap(repo, monkeypatch):
    feed_stdin(monkeypatch, {"session_id": "s-1", "tool_name": "Bash"})
    monkeypatch.setattr(
        events, "_now", lambda: events.datetime.fromisoformat("2026-07-10T09:00:00+00:00")
    )
    session_start.main([])
    monkeypatch.setattr(
        events, "_now", lambda: events.datetime.fromisoformat("2026-07-10T09:20:01+00:00")
    )

    post_tool_use.main([])

    types = [event["type"] for event in read_events(repo)]
    assert "time.slice_paused" in types
    pointer = json.loads((repo / ".active-story").read_text(encoding="utf-8"))
    assert pointer["story_id"] == STORY_ID  # activity never switches the active story


def test_user_prompt_submit_emits_a_pause_after_an_idle_gap(repo, monkeypatch):
    feed_stdin(monkeypatch, {"session_id": "s-1", "prompt": "hi"})
    monkeypatch.setattr(
        events, "_now", lambda: events.datetime.fromisoformat("2026-07-10T09:00:00+00:00")
    )
    session_start.main([])
    monkeypatch.setattr(
        events, "_now", lambda: events.datetime.fromisoformat("2026-07-10T09:20:01+00:00")
    )

    user_prompt_submit.main([])

    types = [event["type"] for event in read_events(repo)]
    assert "time.slice_paused" in types


def test_activity_hooks_are_a_no_op_on_the_pointer_without_a_prior_session(repo, monkeypatch):
    feed_stdin(monkeypatch, {"session_id": "s-1", "tool_name": "Bash", "prompt": "hi"})

    assert post_tool_use.main([]) == 0
    assert user_prompt_submit.main([]) == 0

    assert not (repo / ".active-story").exists()
    types = [event["type"] for event in read_events(repo)]
    assert "time.slice_paused" not in types


def test_session_end_with_no_transcript_path_is_null_with_reason(repo, monkeypatch):
    feed_stdin(monkeypatch, {"session_id": "s-1"})

    session_end.main([])

    (event,) = read_events(repo)
    payload = event["payload"]
    assert payload["input_tokens"] is None
    assert payload["output_tokens"] is None
    assert isinstance(payload["token_cost_reason"], str) and payload["token_cost_reason"]


# --- compile/test defect capture (Story 5.4, redesigned Story 5.8) ---
#
# Story 5.7 found the exit code isn't where the docs said (top-level vs
# nested); Story 5.8 then found Claude Code's PostToolUse payload has NO
# exit-code field at all, ever, confirmed via a real captured payload. The
# real response key is `tool_response`, not `tool_output` either. Detection
# now works via pre_tool_use.py rewriting a matched command to also echo
# `_events.DEFECT_EXIT_MARKER:<code>`, which post_tool_use.py parses back out
# of `tool_response.stdout` - these fixtures use that real shape throughout.


def write_story_config(repo_root: Path, **rates) -> None:
    lines = "".join(f"{key}: {value}\n" for key, value in rates.items())
    (repo_root / ".story-config.yaml").write_text(lines, encoding="utf-8")


def marker_stdout(exit_code: int, extra: str = "") -> str:
    return f"{extra}\n{events.DEFECT_EXIT_MARKER}:{exit_code}\n"


def test_post_tool_use_emits_defect_test_on_matched_failing_command(repo, monkeypatch):
    write_story_config(repo, test_commands="pytest, npm test")
    feed_stdin(
        monkeypatch,
        {
            "session_id": "s-1",
            "tool_name": "Bash",
            "tool_input": {"command": "pytest tests/"},
            "tool_response": {"stdout": marker_stdout(1, "FAILED"), "stderr": "boom"},
        },
    )

    post_tool_use.main([])

    types = [event["type"] for event in read_events(repo)]
    assert "ai.claude-code.defect_test" in types


def test_post_tool_use_emits_defect_compile_on_matched_failing_build_command(repo, monkeypatch):
    write_story_config(repo, build_commands="tsc --noEmit, ruff check")
    feed_stdin(
        monkeypatch,
        {
            "session_id": "s-1",
            "tool_name": "Bash",
            "tool_input": {"command": "tsc --noEmit"},
            "tool_response": {"stdout": marker_stdout(2)},
        },
    )

    post_tool_use.main([])

    types = [event["type"] for event in read_events(repo)]
    assert "ai.claude-code.defect_compile" in types


def test_post_tool_use_defect_payload_never_contains_command_text_or_output(repo, monkeypatch):
    write_story_config(repo, test_commands="pytest")
    feed_stdin(
        monkeypatch,
        {
            "session_id": "s-1",
            "tool_name": "Bash",
            "tool_input": {"command": "pytest tests/ -k secret_token_xyz"},
            "tool_response": {
                "stdout": marker_stdout(1, "leaked stdout"),
                "stderr": "leaked stderr",
            },
        },
    )

    post_tool_use.main([])

    raw = (repo / ".story-events.jsonl").read_text(encoding="utf-8")
    assert "secret_token_xyz" not in raw
    assert "leaked stdout" not in raw
    assert "leaked stderr" not in raw
    assert events.DEFECT_EXIT_MARKER not in raw


def test_post_tool_use_no_defect_on_successful_matched_command(repo, monkeypatch):
    write_story_config(repo, test_commands="pytest")
    feed_stdin(
        monkeypatch,
        {
            "session_id": "s-1",
            "tool_name": "Bash",
            "tool_input": {"command": "pytest tests/"},
            "tool_response": {"stdout": marker_stdout(0)},
        },
    )

    post_tool_use.main([])

    types = [event["type"] for event in read_events(repo)]
    assert "ai.claude-code.defect_test" not in types
    assert "ai.claude-code.defect_compile" not in types


def test_post_tool_use_no_defect_on_unmatched_command(repo, monkeypatch):
    write_story_config(repo, test_commands="pytest")
    feed_stdin(
        monkeypatch,
        {
            "session_id": "s-1",
            "tool_name": "Bash",
            "tool_input": {"command": "echo hello"},
            "tool_response": {"stdout": marker_stdout(1)},
        },
    )

    post_tool_use.main([])

    types = [event["type"] for event in read_events(repo)]
    assert "ai.claude-code.defect_test" not in types
    assert "ai.claude-code.defect_compile" not in types


def test_post_tool_use_ignores_a_bare_exit_code_field_since_it_doesnt_exist_in_real_payloads(
    repo, monkeypatch
):
    """Regression guard (Story 5.8): Claude Code never sends a structured
    exit_code field at all (top-level or nested) - confirmed via a real
    captured payload. Even if one is present (e.g. stale test data, or a
    future payload shape change this project hasn't verified), it must never
    be trusted on its own - only the marker in tool_response.stdout counts."""
    write_story_config(repo, test_commands="pytest")
    feed_stdin(
        monkeypatch,
        {
            "session_id": "s-1",
            "tool_name": "Bash",
            "tool_input": {"command": "pytest tests/"},
            "tool_response": {"stdout": "no marker here"},
            "exit_code": 1,
            "tool_output": {"exit_code": 1},
        },
    )

    post_tool_use.main([])

    types = [event["type"] for event in read_events(repo)]
    assert "ai.claude-code.defect_test" not in types


def test_post_tool_use_no_defect_when_no_config_present(repo, monkeypatch):
    feed_stdin(
        monkeypatch,
        {
            "session_id": "s-1",
            "tool_name": "Bash",
            "tool_input": {"command": "pytest tests/"},
            "tool_response": {"stdout": marker_stdout(1)},
        },
    )

    post_tool_use.main([])

    types = [event["type"] for event in read_events(repo)]
    assert types == ["ai.claude-code.tool_use"]


def test_post_tool_use_non_bash_tool_never_emits_a_defect(repo, monkeypatch):
    write_story_config(repo, test_commands="pytest")
    feed_stdin(monkeypatch, {"session_id": "s-1", "tool_name": "Edit"})

    post_tool_use.main([])

    types = [event["type"] for event in read_events(repo)]
    assert "ai.claude-code.defect_test" not in types
    assert "ai.claude-code.defect_compile" not in types


def test_extract_exit_code_takes_the_last_marker_occurrence(repo):
    stdout = f"{events.DEFECT_EXIT_MARKER}:0 (a decoy inside command output)\n" + marker_stdout(1)
    assert post_tool_use.extract_exit_code(stdout) == 1


def test_extract_exit_code_returns_none_without_a_marker(repo):
    assert post_tool_use.extract_exit_code("plain output, no marker") is None
    assert post_tool_use.extract_exit_code("") is None


# --- pre_tool_use command rewriting (Story 5.8) ---


def test_pre_tool_use_rewrites_a_matched_command_with_the_exit_marker(repo, monkeypatch, capsys):
    write_story_config(repo, build_commands="tsc --noEmit")
    feed_stdin(
        monkeypatch,
        {
            "session_id": "s-1",
            "tool_name": "Bash",
            "tool_input": {"command": "tsc --noEmit", "description": "type-check"},
        },
    )

    pre_tool_use.main([])

    out = json.loads(capsys.readouterr().out)
    updated = out["hookSpecificOutput"]["updatedInput"]
    assert updated["command"].startswith("tsc --noEmit")
    assert events.DEFECT_EXIT_MARKER in updated["command"]
    assert updated["description"] == "type-check"  # other tool_input fields preserved
    assert out["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_pre_tool_use_does_not_rewrite_an_unmatched_command(repo, monkeypatch, capsys):
    write_story_config(repo, build_commands="tsc --noEmit")
    feed_stdin(
        monkeypatch,
        {"session_id": "s-1", "tool_name": "Bash", "tool_input": {"command": "echo hello"}},
    )

    pre_tool_use.main([])

    assert capsys.readouterr().out == ""


def test_pre_tool_use_does_not_rewrite_when_no_config_present(repo, monkeypatch, capsys):
    feed_stdin(
        monkeypatch,
        {"session_id": "s-1", "tool_name": "Bash", "tool_input": {"command": "tsc --noEmit"}},
    )

    pre_tool_use.main([])

    assert capsys.readouterr().out == ""


def test_pre_tool_use_never_rewrites_non_bash_tools(repo, monkeypatch, capsys):
    write_story_config(repo, build_commands="tsc --noEmit")
    feed_stdin(monkeypatch, {"session_id": "s-1", "tool_name": "Edit"})

    pre_tool_use.main([])

    assert capsys.readouterr().out == ""


def test_pre_tool_use_rewrite_then_post_tool_use_round_trip_emits_a_defect(
    repo, monkeypatch, capsys
):
    """Full loop, matching real Claude Code behavior: pre_tool_use rewrites the
    command, the (simulated) shell actually runs the rewritten command and
    produces marker-suffixed stdout, post_tool_use reads that back out."""
    write_story_config(repo, build_commands="tsc --noEmit")
    tool_input = {"command": "tsc --noEmit"}
    feed_stdin(monkeypatch, {"session_id": "s-1", "tool_name": "Bash", "tool_input": tool_input})

    pre_tool_use.main([])
    rewritten_command = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["updatedInput"][
        "command"
    ]

    # simulate the rewritten command actually failing when run for real
    simulated_stdout = "error TS2322: ...\n" + marker_stdout(2)
    feed_stdin(
        monkeypatch,
        {
            "session_id": "s-1",
            "tool_name": "Bash",
            "tool_input": {"command": rewritten_command},
            "tool_response": {"stdout": simulated_stdout},
        },
    )
    post_tool_use.main([])

    types = [event["type"] for event in read_events(repo)]
    assert "ai.claude-code.defect_compile" in types


def write_transcript(tmp_path: Path, lines: list[dict]) -> str:
    path = tmp_path / "transcript.jsonl"
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")
    return str(path)


def test_session_end_sums_real_tokens_from_the_transcript(repo, monkeypatch, tmp_path):
    transcript = write_transcript(
        tmp_path,
        [
            {"type": "user", "message": {"content": "hi"}},
            {"type": "assistant", "message": {"usage": {"input_tokens": 100, "output_tokens": 20}}},
            {"type": "assistant", "message": {"usage": {"input_tokens": 50, "output_tokens": 10}}},
        ],
    )
    feed_stdin(monkeypatch, {"session_id": "s-1", "transcript_path": transcript})

    session_end.main([])

    (event,) = read_events(repo)
    payload = event["payload"]
    assert payload["input_tokens"] == 150
    assert payload["output_tokens"] == 30
    assert payload["token_cost_reason"] is None


def test_session_end_ignores_malformed_lines_in_the_transcript(repo, monkeypatch, tmp_path):
    path = tmp_path / "transcript.jsonl"
    path.write_text(
        "not json at all\n"
        + json.dumps(
            {"type": "assistant", "message": {"usage": {"input_tokens": 5, "output_tokens": 1}}}
        )
        + "\n"
        + json.dumps({"type": "assistant", "message": {}})
        + "\n",  # assistant line with no usage - must not crash, contributes 0
        encoding="utf-8",
    )
    feed_stdin(monkeypatch, {"session_id": "s-1", "transcript_path": str(path)})

    exit_code = session_end.main([])

    assert exit_code == 0
    (event,) = read_events(repo)
    assert event["payload"]["input_tokens"] == 5
    assert event["payload"]["output_tokens"] == 1


def test_session_end_transcript_path_pointing_nowhere_is_null_with_reason(
    repo, monkeypatch, tmp_path
):
    missing = str(tmp_path / "does-not-exist.jsonl")
    feed_stdin(monkeypatch, {"session_id": "s-1", "transcript_path": missing})

    exit_code = session_end.main([])

    assert exit_code == 0
    (event,) = read_events(repo)
    payload = event["payload"]
    assert payload["input_tokens"] is None
    assert payload["output_tokens"] is None
    assert isinstance(payload["token_cost_reason"], str) and payload["token_cost_reason"]


def test_session_end_transcript_with_no_assistant_usage_lines_is_null_with_reason(
    repo, monkeypatch, tmp_path
):
    transcript = write_transcript(tmp_path, [{"type": "user", "message": {"content": "hi"}}])
    feed_stdin(monkeypatch, {"session_id": "s-1", "transcript_path": transcript})

    exit_code = session_end.main([])

    assert exit_code == 0
    (event,) = read_events(repo)
    payload = event["payload"]
    assert payload["input_tokens"] is None
    assert payload["output_tokens"] is None
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
    event = read_events(repo)[0]
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
    # +1: session_start also emits time.slice_opened via update_active_story (Story 3.1)
    # +1: session_end also emits time.slice_closed via close_active_story_slice (Story 3.3)
    assert err.count("METRICS CAPTURE FAILED") == len(ALL_HOOKS) + 2
