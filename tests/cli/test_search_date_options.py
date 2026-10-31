import pytest

from feedly_cli import cli


@pytest.mark.parametrize(
    "argv",
    [
        ["search", "x", "--since", "2026-02-29"],
        ["search", "x", "--since", "2026-10-01T00:00:00"],
        ["search", "x", "--since", "2026-11-01", "--before", "2026-10-01"],
        ["search", "x", "--since", "2026-10-01", "--before", "2026-10-01"],
    ],
)
def test_invalid_dates_rejected_before_authentication(monkeypatch, client, argv):
    monkeypatch.delenv("FEEDLY_TOKEN", raising=False)
    assert cli.main(argv) == 2
    client.search.assert_not_called()


def test_search_dates_forwarded_for_single_page_and_all(run_cli, client):
    client.search.return_value = {"items": []}
    client.search_all.return_value = {"items": [], "pages": 1}
    for mode in ([], ["--all"]):
        code, _, err = run_cli(
            ["search", "php2shell", "--since", "2026-10-01", "--before", "2026-11-01", *mode]
        )
        assert code == 0 and not err
    assert client.search.call_args.kwargs["since"] == 1790812800000
    assert client.search.call_args.kwargs["before"] == 1793491200000
    assert client.search_all.call_args.kwargs["since"] == 1790812800000
    assert client.search_all.call_args.kwargs["before"] == 1793491200000


def test_date_flags_with_raw_query_file_preserve_payload(run_cli, client, tmp_path):
    query = tmp_path / "request.json"
    query.write_text('{"layers": []}', encoding="utf-8")
    client.search.return_value = {"items": []}
    code, _, err = run_cli(["search", "--query-file", str(query), "--since", "2026-10-01"])
    assert code == 0 and not err
    assert client.search.call_args.args == ({"layers": []},)
    assert client.search.call_args.kwargs["since"] == 1790812800000


def test_empty_dated_page_human_output_shows_continuation(monkeypatch, client, capsys):
    client.search.return_value = {"items": [], "continuation": "next"}
    monkeypatch.setattr(cli.app, "create_client", lambda: client)
    assert cli.main(["search", "php2shell", "--since", "2026-10-01"]) == 0
    captured = capsys.readouterr()
    assert "No articles found." in captured.out
    assert "Results: 0" in captured.out
    assert "More results: --continuation next" in captured.out
    assert not captured.err
