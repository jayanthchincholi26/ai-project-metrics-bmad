"""Tests for the Confluence fetch adapter (Story 1.4, AC 1-2). All HTTP is mocked."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "adapters" / "confluence" / "main.py"
_spec = importlib.util.spec_from_file_location("confluence_main", SCRIPT)
confluence = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(confluence)

BASE_URL = "https://demo.atlassian.net/wiki"
EMAIL = "dev@example.com"
TOKEN = "tok-CONF-SECRET"


class FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def payload(title="Ship the demo", body_html="<p>Longer <b>text</b></p>", labels=()):
    page = {
        "title": title,
        "body": {"storage": {"value": body_html}},
        "metadata": {"labels": {"results": [{"name": name} for name in labels]}},
    }
    return page


def run(tmp_path, monkeypatch, body=None, exc=None, requests_seen=None, env=True, page="123456"):
    if env:
        monkeypatch.setenv("CONFLUENCE_BASE_URL", BASE_URL)
        monkeypatch.setenv("CONFLUENCE_EMAIL", EMAIL)
        monkeypatch.setenv("CONFLUENCE_API_TOKEN", TOKEN)

    def fake_urlopen(req, timeout=None):
        if requests_seen is not None:
            requests_seen.append(req)
        if exc is not None:
            raise exc
        raw = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        return FakeResponse(raw)

    monkeypatch.setattr(confluence.request, "urlopen", fake_urlopen)
    return confluence.main(["--repo-root", str(tmp_path), "--page", page])


def read_ack(capsys) -> dict:
    out_lines = capsys.readouterr().out.strip().splitlines()
    assert len(out_lines) == 1
    return json.loads(out_lines[0])


def test_success_ack_matches_the_jira_normalized_shape(tmp_path, monkeypatch, capsys):
    exit_code = run(tmp_path, monkeypatch, body=payload(labels=("points-5", "sprint-13")))

    assert exit_code == 0
    ack = read_ack(capsys)
    assert set(ack.keys()) == {"ok", "points", "goal", "sprint", "description"}
    assert ack["points"] == 5
    assert ack["goal"] == "Ship the demo"
    assert ack["sprint"] == "13"
    assert ack["description"] == "Longer text"


def test_request_carries_basic_auth_and_expansions(tmp_path, monkeypatch, capsys):
    seen = []
    run(tmp_path, monkeypatch, body=payload(), requests_seen=seen)

    req = seen[0]
    assert req.full_url.startswith(f"{BASE_URL}/rest/api/content/123456?expand=")
    assert "body.storage" in req.full_url and "metadata.labels" in req.full_url
    auth = req.get_header("Authorization")
    assert auth is not None and auth.startswith("Basic ")


def test_page_id_is_url_encoded(tmp_path, monkeypatch, capsys):
    seen = []
    run(tmp_path, monkeypatch, body=payload(), requests_seen=seen, page="12 34/x")

    assert "12%2034%2Fx" in seen[0].full_url


def test_missing_labels_yield_null_points_and_sprint(tmp_path, monkeypatch, capsys):
    run(tmp_path, monkeypatch, body=payload(labels=()))

    ack = read_ack(capsys)
    assert ack["points"] is None
    assert ack["sprint"] is None


def test_fractional_points_label_is_parsed(tmp_path, monkeypatch, capsys):
    run(tmp_path, monkeypatch, body=payload(labels=("points-1.5",)))

    assert read_ack(capsys)["points"] == 1.5


def test_malformed_points_label_yields_null(tmp_path, monkeypatch, capsys):
    run(tmp_path, monkeypatch, body=payload(labels=("points-lots",)))

    assert read_ack(capsys)["points"] is None


def test_sprint_label_remainder_taken_verbatim(tmp_path, monkeypatch, capsys):
    run(tmp_path, monkeypatch, body=payload(labels=("sprint-2026-Q3-S4",)))

    assert read_ack(capsys)["sprint"] == "2026-Q3-S4"


def test_description_is_html_stripped_and_unescaped(tmp_path, monkeypatch, capsys):
    html = "<h1>Head</h1><p>alpha &amp; <em>beta</em></p>"
    run(tmp_path, monkeypatch, body=payload(body_html=html))

    assert read_ack(capsys)["description"] == "Head alpha & beta"


def test_long_description_is_truncated_to_500_chars(tmp_path, monkeypatch, capsys):
    run(tmp_path, monkeypatch, body=payload(body_html="<p>" + "word " * 300 + "</p>"))

    assert len(read_ack(capsys)["description"]) <= 500


def test_empty_body_yields_null_description(tmp_path, monkeypatch, capsys):
    run(tmp_path, monkeypatch, body=payload(body_html="  <p> </p> "))

    assert read_ack(capsys)["description"] is None


def test_missing_env_vars_exit_2_naming_them(tmp_path, monkeypatch, capsys):
    for name in ("CONFLUENCE_BASE_URL", "CONFLUENCE_EMAIL", "CONFLUENCE_API_TOKEN"):
        monkeypatch.delenv(name, raising=False)

    exit_code = run(tmp_path, monkeypatch, body=payload(), env=False)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    for name in ("CONFLUENCE_BASE_URL", "CONFLUENCE_EMAIL", "CONFLUENCE_API_TOKEN"):
        assert name in captured.err


def test_http_401_exits_2_with_credential_hint(tmp_path, monkeypatch, capsys):
    exc = confluence.error.HTTPError("url", 401, "Unauthorized", None, None)
    exit_code = run(tmp_path, monkeypatch, exc=exc)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "CONFLUENCE_EMAIL" in captured.err or "credential" in captured.err.lower()


def test_http_404_exits_2_page_not_found(tmp_path, monkeypatch, capsys):
    exc = confluence.error.HTTPError("url", 404, "Not Found", None, None)
    exit_code = run(tmp_path, monkeypatch, exc=exc)

    assert exit_code == 2
    assert "not found" in capsys.readouterr().err.lower()


def test_network_error_and_malformed_body_exit_2(tmp_path, monkeypatch, capsys):
    assert run(tmp_path, monkeypatch, exc=confluence.error.URLError("dns failure")) == 2
    capsys.readouterr()
    assert run(tmp_path, monkeypatch, body=b"<html>gateway</html>") == 2


def test_missing_title_exits_2(tmp_path, monkeypatch, capsys):
    exit_code = run(tmp_path, monkeypatch, body={"body": {}})

    assert exit_code == 2


def test_token_never_appears_in_output_on_any_path(tmp_path, monkeypatch, capsys):
    run(tmp_path, monkeypatch, body=payload())
    success_out = capsys.readouterr()
    assert TOKEN not in success_out.out + success_out.err

    exc = confluence.error.HTTPError("url", 403, "Forbidden", None, None)
    run(tmp_path, monkeypatch, exc=exc)
    failure_out = capsys.readouterr()
    assert TOKEN not in failure_out.out + failure_out.err


def test_adapter_writes_no_files(tmp_path, monkeypatch, capsys):
    run(tmp_path, monkeypatch, body=payload())

    assert list(tmp_path.iterdir()) == []
