import json

from feedly_cli import cli
from feedly_cli.errors import FeedlyError


def test_missing_token(monkeypatch, capsys):
    monkeypatch.delenv("FEEDLY_TOKEN", raising=False)
    assert cli.main(["--json", "profile"]) == 3
    captured = capsys.readouterr()
    assert not captured.out
    assert json.loads(captured.err)["error"]["code"] == "missing_token"


def test_human_missing_token(monkeypatch, capsys):
    monkeypatch.delenv("FEEDLY_TOKEN", raising=False)
    assert cli.main(["profile"]) == 3
    captured = capsys.readouterr()
    assert "FEEDLY_TOKEN" in captured.err and not captured.out
    assert not captured.err.startswith("{")


def test_error_redacts_token(monkeypatch, run_cli, client):
    monkeypatch.setenv("FEEDLY_TOKEN", "test-secret-do-not-print")
    client.profile.side_effect = RuntimeError("failed test-secret-do-not-print")
    code, out, err = run_cli(["profile"])
    assert code == 7 and not out
    assert "test-secret-do-not-print" not in err
    assert "[redacted]" in json.loads(err)["error"]["message"]


def test_error_details_nested_token_redacted(monkeypatch, run_cli, client):
    monkeypatch.setenv("FEEDLY_TOKEN", "mock-secret")
    client.profile.side_effect = FeedlyError(
        "permission_denied", "denied", status=403, details={"nested": ["mock-secret"]}
    )
    code, out, err = run_cli(["profile"])
    assert code == 3 and not out
    assert "mock-secret" not in err
    assert json.loads(err)["error"]["code"] == "permission_denied"


def test_unicode_output_is_ascii_json(run_cli, client):
    client.profile.return_value = {"label": "日本語"}
    code, out, err = run_cli(["profile"])
    assert code == 0 and not err
    out.encode("ascii")
    assert json.loads(out) == {"label": "日本語"}


def test_client_closes_after_success(run_cli, client):
    client.profile.return_value = {"id": "example"}
    code, _, _ = run_cli(["profile"])
    assert code == 0
    client.close.assert_called_once_with()
