import json

import pytest

from feedly_cli import cli
from feedly_cli.errors import FeedlyError


def test_resolver_cli_json_schema_and_options(run_cli, client):
    value = {
        "entryId": "entry",
        "url": "https://example.test/article",
        "streamId": "source",
        "pagesScanned": 2,
    }
    client.resolve_article_url.return_value = value
    code, out, err = run_cli(
        [
            "articles",
            "resolve-url",
            value["url"],
            "--source-stream",
            "source",
            "--max-pages",
            "4",
            "--count",
            "3",
            "--continuation",
            "prior",
        ]
    )
    assert code == 0 and not err and json.loads(out) == value
    client.resolve_article_url.assert_called_once_with(
        value["url"], stream_id="source", count=3, max_pages=4, continuation="prior"
    )
    client.add_url_to_board.assert_not_called()


def test_resolver_human_copyable_fields(monkeypatch, capsys, client):
    entry_id = "entry/" + "abcdef" * 30
    url = "https://example.test/" + "path/" * 30
    client.resolve_article_url.return_value = {
        "entryId": entry_id,
        "url": url,
        "streamId": "source",
        "pagesScanned": 1,
    }
    monkeypatch.setattr(cli.app, "create_client", lambda: client)
    monkeypatch.setenv("COLUMNS", "40")
    assert cli.main(["articles", "resolve-url", url]) == 0
    captured = capsys.readouterr()
    assert entry_id in captured.out and url in captured.out
    assert "Pages scanned: 1" in captured.out and not captured.err


@pytest.mark.parametrize("args", [["--count", "101"], ["--max-pages", "0"], ["--markdown"]])
def test_resolver_invalid_options_fail_before_auth(monkeypatch, client, args):
    monkeypatch.delenv("FEEDLY_TOKEN", raising=False)
    assert cli.main(["articles", "resolve-url", "https://example.test", *args]) == 2
    client.resolve_article_url.assert_not_called()


def test_resolver_incomplete_error_exposes_resume_in_json(run_cli, client):
    client.resolve_article_url.side_effect = FeedlyError(
        "api_error", "incomplete scan", details={"continuation": "next"}
    )
    code, out, err = run_cli(["articles", "resolve-url", "https://example.test"])
    assert code == 6 and not out
    assert json.loads(err)["error"]["details"]["continuation"] == "next"
