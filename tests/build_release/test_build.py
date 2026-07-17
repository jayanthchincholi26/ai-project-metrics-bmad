"""Tests for the release-artifact builder (Story 4.1). Builds real zips into tmp_path."""

from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "tools" / "build-release" / "main.py"
_spec = importlib.util.spec_from_file_location("build_release", SCRIPT)
build_release = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_release)


def build_zip(tmp_path: Path, version: str = "v0.0.0-test") -> Path:
    exit_code = build_release.main(["--version", version, "--out-dir", str(tmp_path)])
    assert exit_code == 0
    return tmp_path / f"ai-metrics-capture-{version}.zip"


def names_of(artifact: Path) -> "list[str]":
    with zipfile.ZipFile(artifact) as zf:
        return zf.namelist()


def test_artifact_contains_the_deployable_surface(tmp_path):
    names = names_of(build_zip(tmp_path))
    assert "INSTALL.md" in names
    assert ".story-config.yaml.example" in names  # Story 4.4
    assert ".claude/skills/story-kickoff/SKILL.md" in names
    assert ".claude/skills/story-close/SKILL.md" in names  # Story 6.2
    assert ".claude/skills/log-review-defect/SKILL.md" in names  # Story 6.3
    assert "tools/setup-hooks.py" in names
    assert "tools/hooks/_events.py" in names
    assert "tools/hooks/claude/session_start.py" in names
    assert "tools/hooks/git/post-checkout.py" in names
    assert "tools/adapters/docs-only/main.py" in names
    assert "tools/adapters/jira/main.py" in names  # Story 1.6 fallback path ships too
    assert "tools/snapshot-assembler/main.py" in names
    assert "tools/opsx-wrapper/main.py" in names
    assert "tools/estimate-phase1/main.py" in names
    assert ".github/workflows/generate-dashboard.yml" in names  # Story 5.9


def test_story_config_example_contains_every_documented_key(tmp_path):
    artifact = build_zip(tmp_path)
    with zipfile.ZipFile(artifact) as zf:
        content = zf.read(".story-config.yaml.example").decode("utf-8")
    for key in (
        "source_of_truth",
        "ai_tool",
        "jira_points_field",
        "jira_sprint_field",
        "hourly_rate",
        "ai_input_rate",
        "ai_output_rate",
        "test_commands",
        "build_commands",
    ):
        assert key in content, key


def test_artifact_excludes_planning_repo_and_build_internals(tmp_path):
    names = names_of(build_zip(tmp_path))
    for name in names:
        assert not name.startswith("_bmad"), name
        assert not name.startswith("prompts/"), name
        assert not name.startswith("tests/"), name
        assert not name.startswith("docs/"), name
        assert "build-release" not in name, name  # the packager never ships itself
        assert "__pycache__" not in name, name
        assert not name.endswith(".pyc"), name


def test_version_is_baked_into_the_filename(tmp_path):
    artifact = build_zip(tmp_path, version="v9.9.9")
    assert artifact.name == "ai-metrics-capture-v9.9.9.zip"
    assert artifact.is_file()


def test_entries_are_sorted_for_reproducibility(tmp_path):
    names = names_of(build_zip(tmp_path))
    tools_entries = [n for n in names if n.startswith("tools/")]
    assert tools_entries == sorted(tools_entries)


def test_rebuild_overwrites_cleanly(tmp_path):
    first = build_zip(tmp_path)
    second = build_zip(tmp_path)
    assert first == second
    assert names_of(first) == names_of(second)


def test_missing_input_fails_visibly(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(build_release, "INSTALL", tmp_path / "nonexistent-INSTALL.md")
    exit_code = build_release.main(["--version", "v0", "--out-dir", str(tmp_path)])
    assert exit_code == 2
    assert "error:" in capsys.readouterr().err
