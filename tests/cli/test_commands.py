import json
from unittest.mock import Mock

import pytest

from feedly_cli import cli
from feedly_cli.commands import boards


def test_profile_json_and_handler(run_cli, client):
    client.profile.return_value = {"id": "example"}
    code, out, err = run_cli(["profile"])
    assert code == 0
    assert json.loads(out) == {"id": "example"}
    assert err == ""
    client.profile.assert_called_once_with()


def test_stream_pagination_forwarded(run_cli, client):
    client.stream_contents.return_value = {"items": [], "continuation": "next"}
    code, out, err = run_cli(
        [
            "streams",
            "read",
            "enterprise/acme/tag/one",
            "--count",
            "3",
            "--continuation",
            "opaque",
            "--unread-only",
        ]
    )
    assert code == 0 and not err
    assert json.loads(out)["continuation"] == "next"
    client.stream_contents.assert_called_once_with(
        "enterprise/acme/tag/one", count=3, continuation="opaque", unread_only=True
    )


def test_board_watch_deduplicates_and_stops_after_final_poll(monkeypatch, capsys, client):
    client.board_watch.side_effect = [
        {"items": [{"id": "a"}, {"id": "b"}]},
        {"items": [{"id": "b"}, {"id": "c"}]},
    ]
    sleep = Mock()
    monkeypatch.setattr(boards.time, "sleep", sleep)
    monkeypatch.setattr(cli.app, "create_client", lambda: client)
    code = cli.main(
        ["--json", "boards", "watch", "board", "--iterations", "2", "--interval", "0.01"]
    )
    captured = capsys.readouterr()
    assert code == 0 and not captured.err
    pages = [json.loads(line) for line in captured.out.splitlines()]
    assert [item["id"] for item in pages[0]["items"]] == ["a", "b"]
    assert [item["id"] for item in pages[1]["items"]] == ["c"]
    sleep.assert_called_once_with(0.01)


def test_search_options_forwarded(run_cli, client):
    client.search.return_value = {"items": []}
    code, _, err = run_cli(
        ["search", "security", "--count", "3", "--continuation", "next", "--stream-id", "source"]
    )
    assert code == 0 and not err
    client.search.assert_called_once_with(
        "security", count=3, continuation="next", stream_id="source"
    )


def test_search_all_fetch_cli_dispatch(run_cli, client):
    client.search_all.return_value = {"items": [{"id": "a"}], "pages": 2}
    code, out, err = run_cli(["search", "PHP2Shell", "--all", "--fetch", "--count", "1"])
    assert code == 0 and not err
    assert json.loads(out)["pages"] == 2
    client.search_all.assert_called_once_with(
        "PHP2Shell", count=1, max_pages=100, stream_id=None, fetch=True
    )


def test_human_search_default_includes_copyable_metadata(monkeypatch, capsys, client):
    client.search.return_value = {
        "items": [
            {
                "id": "entry/unique-id",
                "title": "PHP2Shell research",
                "canonicalUrl": "https://example.com/php2shell",
                "origin": {"title": "Security News"},
                "tags": [{"id": "enterprise/acme/tag/r", "label": "Research"}],
            }
        ],
        "continuation": "next-page-token",
    }
    monkeypatch.setattr(cli.app, "create_client", lambda: client)
    assert cli.main(["search", "PHP2Shell"]) == 0
    captured = capsys.readouterr()
    for value in (
        "PHP2Shell research",
        "entry/unique-id",
        "https://example.com/php2shell",
        "Security News",
        "Research",
        "next-page-token",
    ):
        assert value in captured.out
    assert not captured.err
    client.profile.assert_not_called()


def test_vulnerability_search_raw_body_and_pagination(run_cli, client, tmp_path):
    query = tmp_path / "query.json"
    query.write_text('{"layers": []}', encoding="utf-8")
    client.cve_search.return_value = {"items": []}
    code, _, err = run_cli(
        ["cves", "search", "--query-file", str(query), "--count", "4", "--continuation", "next"]
    )
    assert code == 0 and not err
    client.cve_search.assert_called_once_with({"layers": []}, count=4, continuation="next")


def test_article_get_markdown_modes(monkeypatch, capsys, client):
    article = {
        "id": "a",
        "title": "Research",
        "canonicalUrl": "https://example.com/a",
        "summary": {"content": "<p>Only a <strong>summary</strong>.</p>"},
    }
    client.entry.return_value = [article]
    monkeypatch.setattr(cli.app, "create_client", lambda: client)
    assert cli.main(["articles", "get", "a", "--markdown"]) == 0
    captured = capsys.readouterr()
    assert "# Research" in captured.out
    assert "**summary**" in captured.out
    assert "<p>" not in captured.out
    assert not captured.err
    assert cli.main(["--json", "articles", "get", "a", "--markdown"]) == 0
    augmented = json.loads(capsys.readouterr().out)[0]
    assert augmented["contentMarkdown"] == "Only a **summary**."
    assert augmented["contentFormat"] == "summary"
    assert "contentMarkdown" not in article


def test_watch_markdown_json_envelope(monkeypatch, capsys, client):
    client.board_watch.side_effect = [
        {"items": [{"id": "a", "summary": {"content": "<p>Hello</p>"}}]},
        {"items": [{"id": "a", "summary": {"content": "<p>Hello</p>"}}]},
    ]
    monkeypatch.setattr(cli.app, "create_client", lambda: client)
    monkeypatch.setattr(boards.time, "sleep", Mock())
    assert cli.main(["boards", "watch", "board", "--iterations", "2", "--json", "--markdown"]) == 0
    captured = capsys.readouterr()
    polls = [json.loads(line) for line in captured.out.splitlines()]
    assert len(polls) == 2
    assert polls[0]["items"][0]["contentMarkdown"] == "Hello"
    assert polls[1]["items"] == []
    assert not captured.err


@pytest.mark.parametrize(
    ("argv", "method", "expected"),
    [
        (["folders", "list"], "folders", ()),
        (["feeds", "list"], "feeds", ()),
        (["boards", "list"], "boards", ()),
        (["cve", "CVE-2024-12345"], "cve", ("CVE-2024-12345",)),
        (
            ["cves", "get", "CVE-2024-12345", "CVE-2024-23456"],
            "cves",
            (["CVE-2024-12345", "CVE-2024-23456"],),
        ),
        (["boards", "read", "board", "--count", "3"], "board_stream", ("board",)),
        (["boards", "add-entry", "board", "entry"], "add_entry_to_board", ("board", "entry")),
    ],
)
def test_command_handlers_call_client_method(run_cli, client, argv, method, expected):
    code, _, err = run_cli(argv)
    assert code == 0 and not err
    called = getattr(client, method)
    called.assert_called_once()
    assert called.call_args.args == expected
