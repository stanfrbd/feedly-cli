from unittest.mock import create_autospec

import pytest

from feedly_cli import cli
from feedly_cli.client import FeedlyClient


@pytest.fixture
def client():
    mock_client = create_autospec(FeedlyClient, instance=True)
    for name in (
        "profile",
        "stream_contents",
        "entry",
        "boards",
        "folders",
        "feeds",
        "board_stream",
        "add_entry_to_board",
        "board_watch",
        "add_url_to_board",
        "search",
        "search_all",
        "fetch_search_result",
        "cve",
        "cves",
        "cve_trending",
        "cve_search",
        "close",
    ):
        getattr(mock_client, name).return_value = None
    return mock_client


@pytest.fixture
def run_cli(monkeypatch, capsys, client):
    def run(argv):
        monkeypatch.setattr(cli.app, "create_client", lambda: client)
        code = cli.main(["--json", *argv])
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    return run
