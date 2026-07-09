"""Tests for the source-of-truth config resolver (Story 1.2, AC 1-2)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "adapters" / "resolve.py"
_spec = importlib.util.spec_from_file_location("adapters_resolve", SCRIPT)
resolve = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(resolve)

ACK_KEYS = {"ok", "source_of_truth", "declared", "implemented", "config"}


def run(repo_root: Path) -> int:
    return resolve.main(["--repo-root", str(repo_root)])


def write_config(repo_root: Path, text: str) -> Path:
    path = repo_root / ".story-config.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def read_ack(capsys) -> dict:
    out_lines = capsys.readouterr().out.strip().splitlines()
    assert len(out_lines) == 1
    return json.loads(out_lines[0])


def test_no_config_file_defaults_to_docs_only(tmp_path, capsys):
    exit_code = run(tmp_path)

    assert exit_code == 0
    ack = read_ack(capsys)
    assert ack["source_of_truth"] == "docs-only"
    assert ack["declared"] is False
    assert ack["config"] is None


def test_config_without_the_key_defaults_to_docs_only(tmp_path, capsys):
    write_config(tmp_path, "some_other_key: value\n")

    exit_code = run(tmp_path)

    assert exit_code == 0
    ack = read_ack(capsys)
    assert ack["source_of_truth"] == "docs-only"
    assert ack["declared"] is False


def test_declared_docs_only_is_resolved_and_implemented(tmp_path, capsys):
    config = write_config(tmp_path, "source_of_truth: docs-only\n")

    exit_code = run(tmp_path)

    assert exit_code == 0
    ack = read_ack(capsys)
    assert ack["source_of_truth"] == "docs-only"
    assert ack["declared"] is True
    assert ack["implemented"] is True
    assert Path(ack["config"]) == config.resolve()


def test_declared_jira_is_resolved_but_not_implemented(tmp_path, capsys):
    write_config(tmp_path, "source_of_truth: jira\n")

    exit_code = run(tmp_path)

    assert exit_code == 0
    ack = read_ack(capsys)
    assert ack["source_of_truth"] == "jira"
    assert ack["declared"] is True
    assert ack["implemented"] is False


def test_declared_confluence_is_resolved_but_not_implemented(tmp_path, capsys):
    write_config(tmp_path, "source_of_truth: confluence\n")

    exit_code = run(tmp_path)

    assert exit_code == 0
    ack = read_ack(capsys)
    assert ack["source_of_truth"] == "confluence"
    assert ack["implemented"] is False


def test_json_quoted_value_is_accepted(tmp_path, capsys):
    write_config(tmp_path, 'source_of_truth: "jira"\n')

    run(tmp_path)

    assert read_ack(capsys)["source_of_truth"] == "jira"


def test_comments_blanks_whitespace_and_unrelated_keys_are_tolerated(tmp_path, capsys):
    write_config(
        tmp_path,
        "# team config\n\n  source_of_truth:   confluence  \nai_tool: claude-code\n",
    )

    exit_code = run(tmp_path)

    assert exit_code == 0
    assert read_ack(capsys)["source_of_truth"] == "confluence"


def test_inline_comment_on_bare_value_is_stripped(tmp_path, capsys):
    write_config(tmp_path, "source_of_truth: jira  # use jira backend\n")

    exit_code = run(tmp_path)

    assert exit_code == 0
    assert read_ack(capsys)["source_of_truth"] == "jira"


def test_single_quoted_value_is_accepted(tmp_path, capsys):
    write_config(tmp_path, "source_of_truth: 'confluence'\n")

    run(tmp_path)

    assert read_ack(capsys)["source_of_truth"] == "confluence"


def test_quoted_value_followed_by_comment_is_accepted(tmp_path, capsys):
    write_config(tmp_path, 'source_of_truth: "docs-only"  # default anyway\n')

    run(tmp_path)

    ack = read_ack(capsys)
    assert ack["source_of_truth"] == "docs-only"
    assert ack["declared"] is True


def test_value_that_is_only_a_comment_exits_2(tmp_path, capsys):
    write_config(tmp_path, "source_of_truth: # pick one later\n")

    exit_code = run(tmp_path)

    assert exit_code == 2
    assert capsys.readouterr().out == ""


def test_utf8_bom_config_is_parsed(tmp_path, capsys):
    (tmp_path / ".story-config.yaml").write_bytes(b"\xef\xbb\xbfsource_of_truth: jira\n")

    exit_code = run(tmp_path)

    assert exit_code == 0
    ack = read_ack(capsys)
    assert ack["source_of_truth"] == "jira"
    assert ack["declared"] is True


def test_invalid_value_exits_2_naming_legal_values(tmp_path, capsys):
    write_config(tmp_path, "source_of_truth: gitlab\n")

    exit_code = run(tmp_path)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "gitlab" in captured.err
    for legal in ("jira", "confluence", "docs-only"):
        assert legal in captured.err


def test_empty_value_exits_2(tmp_path, capsys):
    write_config(tmp_path, "source_of_truth:\n")

    exit_code = run(tmp_path)

    assert exit_code == 2
    assert capsys.readouterr().out == ""


def test_missing_repo_root_exits_2(tmp_path):
    exit_code = run(tmp_path / "does-not-exist")

    assert exit_code == 2


def test_ack_has_exactly_the_contract_keys(tmp_path, capsys):
    run(tmp_path)

    assert set(read_ack(capsys).keys()) == ACK_KEYS


def test_resolver_writes_nothing(tmp_path):
    run(tmp_path)

    assert list(tmp_path.iterdir()) == []
