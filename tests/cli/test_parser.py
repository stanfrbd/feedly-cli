import json
from unittest.mock import Mock

import pytest

from feedly_cli import cli


@pytest.mark.parametrize(
    "argv",
    [
        ["--json", "boards", "list"],
        ["boards", "--json", "list"],
        ["boards", "list", "--json"],
    ],
)
def test_json_flag_at_every_command_level(monkeypatch, capsys, client, argv):
    data = [{"id": "enterprise/acme/tag/a", "label": "Research"}]
    client.boards.return_value = data
    monkeypatch.setattr(cli.app, "create_client", lambda: client)
    assert cli.main(argv) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == data
    assert not captured.err


def test_usage_error_is_json_without_auth(monkeypatch, capsys):
    monkeypatch.delenv("FEEDLY_TOKEN", raising=False)
    assert cli.main(["--json", "streams", "read", "id", "--count", "0"]) == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert json.loads(captured.err)["error"]["code"] == "usage_error"


def test_human_usage_error_can_select_json_at_end(monkeypatch, capsys):
    monkeypatch.delenv("FEEDLY_TOKEN", raising=False)
    assert cli.main(["search", "--unknown", "--json"]) == 2
    captured = capsys.readouterr()
    assert json.loads(captured.err)["error"]["code"] == "usage_error"
    assert not captured.out


def test_search_all_rejects_starting_continuation_before_client(monkeypatch, capsys):
    make_client = Mock()
    monkeypatch.setattr(cli.app, "create_client", make_client)
    assert cli.main(["--json", "search", "PHP2Shell", "--all", "--continuation", "next"]) == 2
    assert json.loads(capsys.readouterr().err)["error"]["code"] == "invalid_input"
    make_client.assert_not_called()


def test_query_file_stream_conflict_rejected_before_client(monkeypatch, capsys, tmp_path):
    query = tmp_path / "query.json"
    query.write_text('{"layers": []}', encoding="utf-8")
    make_client = Mock()
    monkeypatch.setattr(cli.app, "create_client", make_client)
    assert cli.main(["--json", "search", "--query-file", str(query), "--stream-id", "source"]) == 2
    assert json.loads(capsys.readouterr().err)["error"]["code"] == "invalid_input"
    make_client.assert_not_called()


def test_raw_query_file_is_validated_before_auth(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("FEEDLY_TOKEN", raising=False)
    query = tmp_path / "query.json"
    query.write_text("[]", encoding="utf-8")
    assert cli.main(["--json", "search", "--query-file", str(query)]) == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert json.loads(captured.err)["error"]["code"] == "invalid_input"


def test_markdown_rejected_for_boards_list_before_network(monkeypatch, capsys):
    make_client = Mock()
    monkeypatch.setattr(cli.app, "create_client", make_client)
    assert cli.main(["boards", "list", "--markdown", "--json"]) == 2
    assert json.loads(capsys.readouterr().err)["error"]["code"] == "invalid_input"
    make_client.assert_not_called()
