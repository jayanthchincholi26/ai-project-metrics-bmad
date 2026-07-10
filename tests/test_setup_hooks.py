"""Tests for the hook installer (Story 2.1, AC 1-2). Fake .git dir — no real git operations."""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "tools" / "setup-hooks.py"
_spec = importlib.util.spec_from_file_location("setup_hooks", SCRIPT)
setup_hooks = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(setup_hooks)

GIT_HOOKS = ("post-commit", "post-checkout", "post-merge", "commit-msg")
CLAUDE_EVENTS = (
    "SessionStart",
    "SessionEnd",
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "UserPromptSubmit",
)


@pytest.fixture
def fake_repo(tmp_path):
    shutil.copytree(REPO / "tools" / "hooks", tmp_path / "tools" / "hooks")
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    return tmp_path


def run(repo_root: Path) -> int:
    return setup_hooks.main(["--repo-root", str(repo_root)])


def settings_of(repo_root: Path) -> dict:
    return json.loads((repo_root / ".claude" / "settings.json").read_text(encoding="utf-8"))


def our_commands(settings: dict, event: str) -> list[str]:
    commands = []
    for entry in settings.get("hooks", {}).get(event, []):
        for hook in entry.get("hooks", []):
            if "tools/hooks/claude/" in hook.get("command", ""):
                commands.append(hook["command"])
    return commands


def test_fresh_install_copies_all_git_hooks_with_marker(fake_repo, capsys):
    exit_code = run(fake_repo)

    assert exit_code == 0
    for name in GIT_HOOKS:
        installed = fake_repo / ".git" / "hooks" / name
        source = fake_repo / "tools" / "hooks" / "git" / f"{name}.sh"
        assert installed.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
        assert setup_hooks.MARKER in installed.read_text(encoding="utf-8")


def test_fresh_install_creates_settings_with_all_six_events(fake_repo, capsys):
    run(fake_repo)

    settings = settings_of(fake_repo)
    for event in CLAUDE_EVENTS:
        assert len(our_commands(settings, event)) == 1


def test_ack_lists_git_hooks_and_events(fake_repo, capsys):
    exit_code = run(fake_repo)

    out_lines = capsys.readouterr().out.strip().splitlines()
    assert exit_code == 0
    assert len(out_lines) == 1
    ack = json.loads(out_lines[0])
    assert ack["ok"] is True
    assert sorted(ack["git_hooks"]) == sorted(GIT_HOOKS)
    assert sorted(ack["events_wired"]) == sorted(CLAUDE_EVENTS)


def test_second_run_is_idempotent(fake_repo, capsys):
    run(fake_repo)
    first_settings = settings_of(fake_repo)
    first_hook = (fake_repo / ".git" / "hooks" / "post-commit").read_bytes()

    exit_code = run(fake_repo)

    assert exit_code == 0
    assert settings_of(fake_repo) == first_settings
    assert (fake_repo / ".git" / "hooks" / "post-commit").read_bytes() == first_hook
    for event in CLAUDE_EVENTS:
        assert len(our_commands(settings_of(fake_repo), event)) == 1


def test_foreign_hook_is_refused_and_untouched(fake_repo, capsys):
    foreign = fake_repo / ".git" / "hooks" / "post-commit"
    foreign.write_text("#!/bin/sh\necho mine\n", encoding="utf-8")

    exit_code = run(fake_repo)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "post-commit" in captured.err
    assert foreign.read_text(encoding="utf-8") == "#!/bin/sh\necho mine\n"
    assert not (fake_repo / ".claude" / "settings.json").exists()


def test_directory_named_like_a_hook_is_a_conflict_not_a_crash(fake_repo, capsys):
    (fake_repo / ".git" / "hooks" / "post-commit").mkdir()

    exit_code = run(fake_repo)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "post-commit" in captured.err
    assert (fake_repo / ".git" / "hooks" / "post-commit").is_dir()


def test_our_marked_hook_is_upgraded_in_place(fake_repo, capsys):
    stale = fake_repo / ".git" / "hooks" / "post-commit"
    stale.write_text(f"#!/bin/sh\n# {setup_hooks.MARKER}\nold content\n", encoding="utf-8")

    exit_code = run(fake_repo)

    assert exit_code == 0
    source = fake_repo / "tools" / "hooks" / "git" / "post-commit.sh"
    assert stale.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")


def test_existing_settings_and_user_hooks_are_preserved(fake_repo, capsys):
    settings_dir = fake_repo / ".claude"
    settings_dir.mkdir()
    existing = {
        "model": "opus",
        "hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "echo hi"}]}]},
    }
    (settings_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

    exit_code = run(fake_repo)

    assert exit_code == 0
    settings = settings_of(fake_repo)
    assert settings["model"] == "opus"
    session_start = settings["hooks"]["SessionStart"]
    all_commands = [h["command"] for entry in session_start for h in entry["hooks"]]
    assert "echo hi" in all_commands
    assert len(our_commands(settings, "SessionStart")) == 1


def test_malformed_settings_json_is_refused_and_untouched(fake_repo, capsys):
    settings_dir = fake_repo / ".claude"
    settings_dir.mkdir()
    (settings_dir / "settings.json").write_text("{not json", encoding="utf-8")

    exit_code = run(fake_repo)

    assert exit_code == 2
    assert (settings_dir / "settings.json").read_text(encoding="utf-8") == "{not json"
    assert not (fake_repo / ".git" / "hooks" / "post-commit").exists()


def test_missing_git_dir_exits_2(tmp_path, capsys):
    shutil.copytree(REPO / "tools" / "hooks", tmp_path / "tools" / "hooks")

    exit_code = run(tmp_path)

    assert exit_code == 2


def test_missing_hook_sources_exit_2(tmp_path, capsys):
    (tmp_path / ".git" / "hooks").mkdir(parents=True)

    exit_code = run(tmp_path)

    assert exit_code == 2


def test_all_claude_placeholder_hooks_exit_0():
    # The four git hooks became real producers in Story 2.2 (covered by
    # tests/hooks/test_git_hooks.py); only the claude placeholders remain inert.
    hook_files = sorted((REPO / "tools" / "hooks" / "claude").rglob("*.py"))
    assert len(hook_files) == 6
    for path in hook_files:
        spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.main([]) == 0, path.name
