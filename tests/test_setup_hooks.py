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


def test_hook_commands_use_absolute_paths(fake_repo, capsys):
    # Story 2.7: a relative path breaks the moment a session cd's elsewhere -
    # every hook command must resolve independently of the invoking cwd.
    run(fake_repo)

    settings = settings_of(fake_repo)
    for event, script in setup_hooks.CLAUDE_EVENTS.items():
        commands = our_commands(settings, event)
        assert len(commands) == 1
        prefix = "uv run "
        assert commands[0].startswith(prefix)
        path_str = commands[0][len(prefix) :].strip('"')
        assert Path(path_str).is_absolute()
        assert Path(path_str) == (fake_repo / "tools" / "hooks" / "claude" / script).resolve()


def test_ack_lists_git_hooks_and_events(fake_repo, capsys):
    exit_code = run(fake_repo)

    out_lines = capsys.readouterr().out.strip().splitlines()
    assert exit_code == 0
    assert len(out_lines) == 1
    ack = json.loads(out_lines[0])
    assert ack["ok"] is True
    assert sorted(ack["git_hooks"]) == sorted(GIT_HOOKS)
    assert sorted(ack["events_wired"]) == sorted(CLAUDE_EVENTS)


def test_stale_relative_path_command_is_upgraded_not_duplicated(fake_repo, capsys):
    # Story 2.7: simulates a pre-fix install (relative-path command already wired,
    # e.g. on a pilot machine from before this story). Re-running must upgrade
    # that entry in place, not append a second command alongside the stale one.
    settings_dir = fake_repo / ".claude"
    settings_dir.mkdir()
    stale_command = "uv run tools/hooks/claude/pre_tool_use.py"
    existing = {
        "hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": stale_command}]}]}
    }
    (settings_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

    exit_code = run(fake_repo)

    assert exit_code == 0
    commands = our_commands(settings_of(fake_repo), "PreToolUse")
    assert len(commands) == 1
    assert commands[0] != stale_command
    assert Path(commands[0][len("uv run ") :].strip('"')).is_absolute()


def test_a_similarly_named_custom_hook_is_not_mistaken_for_ours(fake_repo, capsys):
    # Review finding (PR #22): a naive endswith(script) match would treat a
    # hand-added hook like "my_backstop.py" as our "stop.py" (it IS a suffix
    # match) and overwrite the developer's own command. Must not happen.
    settings_dir = fake_repo / ".claude"
    settings_dir.mkdir()
    custom_command = "uv run /usr/local/bin/my_backstop.py"
    existing = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": custom_command}]}]}}
    (settings_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

    exit_code = run(fake_repo)

    assert exit_code == 0
    settings = settings_of(fake_repo)
    stop_commands = [h["command"] for entry in settings["hooks"]["Stop"] for h in entry["hooks"]]
    assert custom_command in stop_commands  # untouched
    assert len(stop_commands) == 2  # the developer's hook, plus ours added alongside it


def test_trailing_whitespace_after_quote_is_still_recognized_as_ours(fake_repo, capsys):
    # Review finding (PR #22): a hand-edited settings.json with trailing
    # whitespace after the closing quote must still be recognized as our
    # entry and upgraded, not duplicated.
    settings_dir = fake_repo / ".claude"
    settings_dir.mkdir()
    padded_command = 'uv run "tools/hooks/claude/pre_tool_use.py" '
    existing = {
        "hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": padded_command}]}]}
    }
    (settings_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

    exit_code = run(fake_repo)

    assert exit_code == 0
    commands = our_commands(settings_of(fake_repo), "PreToolUse")
    assert len(commands) == 1
    assert commands[0] != padded_command


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


def test_existing_settings_with_utf8_bom_is_tolerated(fake_repo, capsys):
    # PowerShell's `Set-Content -Encoding utf8` (5.1) writes a real UTF-8 BOM --
    # confirmed empirically after a real user hit this via uninstall.ps1's own
    # settings.json rewrite step. json.loads() on a plain "utf-8" decode leaves
    # a stray U+FEFF character that raises "Unexpected UTF-8 BOM".
    settings_dir = fake_repo / ".claude"
    settings_dir.mkdir()
    existing = {"model": "opus", "hooks": {}}
    (settings_dir / "settings.json").write_bytes(
        b"\xef\xbb\xbf" + json.dumps(existing).encode("utf-8")
    )

    exit_code = run(fake_repo)

    assert exit_code == 0
    settings = settings_of(fake_repo)
    assert settings["model"] == "opus"
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


def test_all_ten_hook_scripts_exist():
    # Placeholder-behavior tests are superseded: git hooks became producers in
    # 2.2, claude hooks in 2.3 (tests/hooks/). The installer contract only
    # needs the tracked scripts to exist.
    assert len(sorted((REPO / "tools" / "hooks" / "git").glob("*.py"))) == 4
    assert len(sorted((REPO / "tools" / "hooks" / "claude").glob("*.py"))) == 6


# Story 2.8: a minimal-PATH git client (some GUI clients) can't find `uv` -
# every git shell shim must guard against that rather than letting the shell
# itself fail before Python runs.


def test_every_git_hook_shim_guards_against_uv_missing_from_path():
    for name in GIT_HOOKS:
        content = (REPO / "tools" / "hooks" / "git" / f"{name}.sh").read_text(encoding="utf-8")
        assert "command -v uv" in content, name


def test_commit_msg_shim_unconditionally_exits_zero():
    """commit-msg is the one git hook whose non-zero exit actually aborts the
    commit (post-commit/post-checkout/post-merge are advisory only, per
    _events.py's own documented exit-code table) - it must force exit 0
    regardless of whether `uv` was found."""
    content = (REPO / "tools" / "hooks" / "git" / "commit-msg.sh").read_text(encoding="utf-8")
    assert content.strip().endswith("exit 0")


# Story 2.11: .gitignore enforcement for local capture state (prevents silent
# cross-branch event-log forking found during 2026-07-13 pilot testing).


def test_fresh_install_creates_gitignore_with_all_entries(fake_repo, capsys):
    assert not (fake_repo / ".gitignore").exists()

    run(fake_repo)

    lines = (fake_repo / ".gitignore").read_text(encoding="utf-8").splitlines()
    for entry in setup_hooks.GITIGNORE_ENTRIES:
        assert entry in lines


def test_existing_gitignore_gets_only_missing_entries_appended(fake_repo, capsys):
    gitignore = fake_repo / ".gitignore"
    gitignore.write_text("node_modules/\n.story-events.jsonl\n.active-story\n", encoding="utf-8")

    run(fake_repo)

    lines = gitignore.read_text(encoding="utf-8").splitlines()
    assert lines.count("node_modules/") == 1
    assert lines.count(".story-events.jsonl") == 1
    assert lines.count(".active-story") == 1
    assert ".story-events.pending.jsonl" in lines
    assert ".active-claude-session" in lines


def test_gitignore_write_is_idempotent_on_second_run(fake_repo, capsys):
    run(fake_repo)
    first = (fake_repo / ".gitignore").read_text(encoding="utf-8")

    run(fake_repo)

    assert (fake_repo / ".gitignore").read_text(encoding="utf-8") == first


def test_tracked_capture_file_produces_a_visible_warning_but_still_exits_zero(
    fake_repo, capsys, monkeypatch
):
    monkeypatch.setattr(
        setup_hooks._events,
        "git_out",
        lambda *args, **kwargs: ".story-events.jsonl" if "ls-files" in args else None,
    )

    exit_code = run(fake_repo)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "warning" in captured.err.lower()
    assert ".story-events.jsonl" in captured.err
    assert "git rm --cached" in captured.err
    # the stdout contract (exactly one JSON ack line) must not be disturbed by the warning
    out_lines = captured.out.strip().splitlines()
    assert len(out_lines) == 1
    assert json.loads(out_lines[0])["ok"] is True


def test_no_warning_when_nothing_is_tracked(fake_repo, capsys, monkeypatch):
    monkeypatch.setattr(setup_hooks._events, "git_out", lambda *args, **kwargs: None)

    exit_code = run(fake_repo)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""


def test_git_unavailable_is_treated_as_not_tracked_never_blocks_install(
    fake_repo, capsys, monkeypatch
):
    # fake_repo has no real git repository - a real git_out call would fail this
    # way; must degrade to "can't determine, don't warn," never crash the install.
    def raise_like_no_repo(*args, **kwargs):
        return None

    monkeypatch.setattr(setup_hooks._events, "git_out", raise_like_no_repo)

    exit_code = run(fake_repo)

    assert exit_code == 0
    assert (fake_repo / ".gitignore").exists()
    assert (fake_repo / ".claude" / "settings.json").exists()


def test_anchored_slash_prefixed_entry_is_not_redundantly_duplicated(fake_repo, capsys):
    # Review finding (PR #23): a hand-written anchored rule like
    # "/.story-events.jsonl" already covers the file; a naive exact-match
    # check would fail to recognize that and append a duplicate plain entry.
    gitignore = fake_repo / ".gitignore"
    gitignore.write_text("/.story-events.jsonl\n", encoding="utf-8")

    run(fake_repo)

    lines = gitignore.read_text(encoding="utf-8").splitlines()
    assert lines.count("/.story-events.jsonl") == 1
    assert ".story-events.jsonl" not in lines
    assert ".story-events.pending.jsonl" in lines


def test_whitespace_padded_existing_entry_is_recognized_not_duplicated(fake_repo, capsys):
    # Review finding (PR #23): leading/trailing whitespace around an existing
    # entry must not defeat the "already present" check.
    gitignore = fake_repo / ".gitignore"
    gitignore.write_text("  .story-events.jsonl  \n", encoding="utf-8")

    run(fake_repo)

    lines = gitignore.read_text(encoding="utf-8").splitlines()
    assert lines.count("  .story-events.jsonl  ") == 1
    assert ".story-events.jsonl" not in lines


def test_gitignore_as_a_directory_does_not_crash_the_install(fake_repo, capsys):
    # Review finding (PR #23): path.exists() alone doesn't guarantee it's a
    # regular file — a directory named .gitignore must not crash setup.
    (fake_repo / ".gitignore").mkdir()

    exit_code = run(fake_repo)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "not a regular file" in captured.err
    assert (fake_repo / ".claude" / "settings.json").exists()


def test_tracked_check_uses_a_single_batched_git_call(fake_repo, capsys, monkeypatch):
    # Review finding (PR #23): one subprocess per entry is wasteful; a single
    # `git ls-files -- <paths...>` call should cover all 4 entries at once.
    calls = []

    def fake_git_out(*args, **kwargs):
        calls.append(args)
        if "ls-files" in args:
            return ".story-events.jsonl\n.active-story"
        return None

    monkeypatch.setattr(setup_hooks._events, "git_out", fake_git_out)

    run(fake_repo)

    ls_files_calls = [c for c in calls if "ls-files" in c]
    assert len(ls_files_calls) == 1

    captured = capsys.readouterr()
    assert ".story-events.jsonl" in captured.err
    assert ".active-story" in captured.err
    assert ".story-events.pending.jsonl" not in captured.err
