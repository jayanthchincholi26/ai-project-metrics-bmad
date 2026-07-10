"""Tests for the opsx CLI wrapper (Story 2.4, AC 1). Subprocess and emitter are mocked."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[2]


def load(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# The shared emitter must be importable before the wrapper's `import _events`.
events = load("_events", REPO / "tools" / "hooks" / "_events.py")
wrapper = load("opsx_wrapper", REPO / "tools" / "opsx-wrapper" / "main.py")


class Recorder:
    def __init__(self, cli_rc: int = 0, assembler_rc: int = 0):
        self.cli_calls: list[list[str]] = []
        self.assembler_calls: list[list[str]] = []
        self.cli_rc = cli_rc
        self.assembler_rc = assembler_rc

    def fake_run(self, args, **kwargs):
        if "snapshot-assembler" in " ".join(str(a) for a in args):
            self.assembler_calls.append([str(a) for a in args])
            return SimpleNamespace(returncode=self.assembler_rc)
        self.cli_calls.append([str(a) for a in args])
        return SimpleNamespace(returncode=self.cli_rc)


def setup(monkeypatch, tmp_path, cli="openspec", cli_rc=0, assembler_rc=0):
    recorder = Recorder(cli_rc=cli_rc, assembler_rc=assembler_rc)
    monkeypatch.setattr(wrapper, "find_cli", lambda: cli)
    monkeypatch.setattr(wrapper.subprocess, "run", recorder.fake_run)
    monkeypatch.setattr(events, "repo_root", lambda: tmp_path)
    emitted = []
    monkeypatch.setattr(
        events, "emit", lambda source, etype, payload: emitted.append((source, etype, payload)) or 0
    )
    return recorder, emitted


def test_non_archive_is_pure_passthrough(monkeypatch, tmp_path, capsys):
    recorder, emitted = setup(monkeypatch, tmp_path)

    exit_code = wrapper.main(["list", "--all"])

    assert exit_code == 0
    assert recorder.cli_calls == [["openspec", "list", "--all"]]
    assert emitted == []
    assert recorder.assembler_calls == []


def test_non_archive_mirrors_underlying_exit_code(monkeypatch, tmp_path, capsys):
    recorder, emitted = setup(monkeypatch, tmp_path, cli_rc=4)

    assert wrapper.main(["validate"]) == 4


def test_archive_success_emits_event_and_runs_assembler(monkeypatch, tmp_path, capsys):
    recorder, emitted = setup(monkeypatch, tmp_path)

    exit_code = wrapper.main(["archive", "my-change"])

    assert exit_code == 0
    assert recorder.cli_calls == [["openspec", "archive", "my-change"]]
    assert emitted == [("opsx", "opsx.archive", {"args": ["archive", "my-change"]})]
    (assembler_call,) = recorder.assembler_calls
    assert "--repo-root" in assembler_call
    assert str(tmp_path) in assembler_call


def test_failed_archive_mirrors_code_with_no_capture(monkeypatch, tmp_path, capsys):
    recorder, emitted = setup(monkeypatch, tmp_path, cli_rc=3)

    exit_code = wrapper.main(["archive", "my-change"])

    assert exit_code == 3
    assert emitted == []
    assert recorder.assembler_calls == []


def test_missing_cli_on_archive_still_captures(monkeypatch, tmp_path, capsys):
    recorder, emitted = setup(monkeypatch, tmp_path, cli=None)

    exit_code = wrapper.main(["archive", "my-change"])

    assert exit_code == 0
    assert recorder.cli_calls == []
    assert len(emitted) == 1
    assert len(recorder.assembler_calls) == 1
    assert "no openspec/opsx cli found" in capsys.readouterr().err.lower()


def test_missing_cli_on_non_archive_exits_2(monkeypatch, tmp_path, capsys):
    recorder, emitted = setup(monkeypatch, tmp_path, cli=None)

    assert wrapper.main(["list"]) == 2


def test_assembler_failure_exits_1_even_after_successful_archive(monkeypatch, tmp_path, capsys):
    recorder, emitted = setup(monkeypatch, tmp_path, assembler_rc=1)

    exit_code = wrapper.main(["archive", "my-change"])

    assert exit_code == 1
    assert "snapshot" in capsys.readouterr().err.lower()
