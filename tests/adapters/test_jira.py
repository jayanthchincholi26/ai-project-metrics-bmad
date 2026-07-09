"""Tests for the JIRA fetch adapter (Story 1.3, AC 1-2). All HTTP is mocked — never a real API call."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "adapters" / "jira" / "main.py"
_spec = importlib.util.spec_from_file_location("jira_main", SCRIPT)
jira = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(jira)

BASE_URL = "https://demo.atlassian.net"
EMAIL = "dev@example.com"
TOKEN = "tok-SECRET-123"
POINTS_FIELD = "customfield_10016"
SPRINT_FIELD = "customfield_10020"


class FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def payload(summary="Ship the demo", description="Longer text", points=5, sprint=None):
    fields = {"summary": summary, "description": description, POINTS_FIELD: points}
    if sprint is not None:
        fields[SPRINT_FIELD] = sprint
    return {"fields": fields}


def run(tmp_path, monkeypatch, body=None, exc=None, requests_seen=None, env=True, issue="PROJ-123"):
    if env:
        monkeypatch.setenv("JIRA_BASE_URL", BASE_URL)
        monkeypatch.setenv("JIRA_EMAIL", EMAIL)
        monkeypatch.setenv("JIRA_API_TOKEN", TOKEN)

    def fake_urlopen(req, timeout=None):
        if requests_seen is not None:
            requests_seen.append(req)
        if exc is not None:
            raise exc
        raw = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        return FakeResponse(raw)

    monkeypatch.setattr(jira.request, "urlopen", fake_urlopen)
    return jira.main(["--repo-root", str(tmp_path), "--issue", issue])


def read_ack(capsys) -> dict:
    out_lines = capsys.readouterr().out.strip().splitlines()
    assert len(out_lines) == 1
    return json.loads(out_lines[0])


def test_success_ack_contains_the_normalized_shape(tmp_path, monkeypatch, capsys):
    exit_code = run(
        tmp_path, monkeypatch, body=payload(sprint=[{"name": "Sprint 9", "state": "active"}])
    )

    assert exit_code == 0
    ack = read_ack(capsys)
    assert ack == {
        "ok": True,
        "points": 5,
        "goal": "Ship the demo",
        "sprint": "Sprint 9",
        "description": "Longer text",
    }


def test_request_carries_basic_auth_and_field_list(tmp_path, monkeypatch, capsys):
    seen = []
    run(tmp_path, monkeypatch, body=payload(), requests_seen=seen)

    req = seen[0]
    assert req.full_url.startswith(f"{BASE_URL}/rest/api/2/issue/PROJ-123?fields=")
    assert POINTS_FIELD in req.full_url and SPRINT_FIELD in req.full_url
    auth = req.get_header("Authorization")
    assert auth is not None and auth.startswith("Basic ")


def test_issue_key_is_url_encoded(tmp_path, monkeypatch, capsys):
    seen = []
    run(tmp_path, monkeypatch, body=payload(), requests_seen=seen, issue="PROJ 123/../x")

    assert "PROJ%20123%2F..%2Fx" in seen[0].full_url
    assert "PROJ 123" not in seen[0].full_url


def test_absent_points_yield_null(tmp_path, monkeypatch, capsys):
    exit_code = run(tmp_path, monkeypatch, body=payload(points=None))

    assert exit_code == 0
    assert read_ack(capsys)["points"] is None


def test_integral_float_points_become_int(tmp_path, monkeypatch, capsys):
    run(tmp_path, monkeypatch, body=payload(points=5.0))

    ack = read_ack(capsys)
    assert ack["points"] == 5
    assert isinstance(ack["points"], int)


def test_sprint_active_object_wins_over_closed(tmp_path, monkeypatch, capsys):
    sprint = [{"name": "Sprint 8", "state": "closed"}, {"name": "Sprint 9", "state": "active"}]
    run(tmp_path, monkeypatch, body=payload(sprint=sprint))

    assert read_ack(capsys)["sprint"] == "Sprint 9"


def test_sprint_falls_back_to_last_when_none_active(tmp_path, monkeypatch, capsys):
    sprint = [{"name": "Sprint 8", "state": "closed"}, {"name": "Sprint 10", "state": "future"}]
    run(tmp_path, monkeypatch, body=payload(sprint=sprint))

    assert read_ack(capsys)["sprint"] == "Sprint 10"


def test_sprint_legacy_greenhopper_string_is_parsed(tmp_path, monkeypatch, capsys):
    legacy = [
        "com.atlassian.greenhopper.service.sprint.Sprint@6d[id=5,state=ACTIVE,name=Sprint 7,startDate=2026-07-01]"
    ]
    run(tmp_path, monkeypatch, body=payload(sprint=legacy))

    assert read_ack(capsys)["sprint"] == "Sprint 7"


def test_sprint_absent_yields_null(tmp_path, monkeypatch, capsys):
    run(tmp_path, monkeypatch, body=payload())

    assert read_ack(capsys)["sprint"] is None


def test_missing_env_vars_exit_2_naming_them(tmp_path, monkeypatch, capsys):
    for name in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"):
        monkeypatch.delenv(name, raising=False)

    exit_code = run(tmp_path, monkeypatch, body=payload(), env=False)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    for name in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"):
        assert name in captured.err


def test_http_401_exits_2_with_credential_hint(tmp_path, monkeypatch, capsys):
    exc = jira.error.HTTPError("url", 401, "Unauthorized", None, None)
    exit_code = run(tmp_path, monkeypatch, exc=exc)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "JIRA_EMAIL" in captured.err or "credential" in captured.err.lower()


def test_http_404_exits_2_issue_not_found(tmp_path, monkeypatch, capsys):
    exc = jira.error.HTTPError("url", 404, "Not Found", None, None)
    exit_code = run(tmp_path, monkeypatch, exc=exc)

    assert exit_code == 2
    assert "not found" in capsys.readouterr().err.lower()


def test_network_error_exits_2(tmp_path, monkeypatch, capsys):
    exit_code = run(tmp_path, monkeypatch, exc=jira.error.URLError("dns failure"))

    assert exit_code == 2
    assert capsys.readouterr().out == ""


def test_malformed_body_exits_2(tmp_path, monkeypatch, capsys):
    exit_code = run(tmp_path, monkeypatch, body=b"<html>gateway error</html>")

    assert exit_code == 2
    assert capsys.readouterr().out == ""


def test_missing_summary_exits_2(tmp_path, monkeypatch, capsys):
    exit_code = run(tmp_path, monkeypatch, body={"fields": {}})

    assert exit_code == 2


def test_token_never_appears_in_output_on_any_path(tmp_path, monkeypatch, capsys):
    run(tmp_path, monkeypatch, body=payload())
    success_out = capsys.readouterr()
    assert TOKEN not in success_out.out + success_out.err

    exc = jira.error.HTTPError("url", 403, "Forbidden", None, None)
    run(tmp_path, monkeypatch, exc=exc)
    failure_out = capsys.readouterr()
    assert TOKEN not in failure_out.out + failure_out.err


def test_adapter_writes_no_files(tmp_path, monkeypatch, capsys):
    run(tmp_path, monkeypatch, body=payload())

    assert list(tmp_path.iterdir()) == []


def test_config_overrides_points_field(tmp_path, monkeypatch, capsys):
    (tmp_path / ".story-config.yaml").write_text(
        "source_of_truth: jira\njira_points_field: customfield_99999\n", encoding="utf-8"
    )
    body = {"fields": {"summary": "S", "description": None, "customfield_99999": 8}}
    exit_code = run(tmp_path, monkeypatch, body=body)

    assert exit_code == 0
    assert read_ack(capsys)["points"] == 8
