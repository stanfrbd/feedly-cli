from __future__ import annotations

import pytest
import responses

from feedly_cli.api.boards import BoardAPI
from feedly_cli.errors import FeedlyError


def test_board_stream_and_add_entry_use_encoded_team_board(
    client, api_http, add_api_response, decode_request_json
):
    add_api_response(api_http, responses.GET, "/v3/streams/contents", {"items": []})
    add_api_response(api_http, responses.PUT, "/v3/tags/enterprise%2Fa%2Ftag%2Fb", None)
    client.board_stream("enterprise/a/tag/b")
    client.add_entry_to_board("enterprise/a/tag/b", "article")
    assert api_http.calls[1].request.method == "PUT"
    assert decode_request_json(api_http.calls[1]) == {"entryId": "article"}


def test_board_resource_posts_add_entry(client, api_http, add_api_response, decode_request_json):
    add_api_response(api_http, responses.PUT, "/v3/tags/board", None)
    resource = BoardAPI(client._transport, client._stream_api, client._discovery_api)
    resource.add_entry("board", "entry")
    assert decode_request_json(api_http.calls[0]) == {"entryId": "entry"}


def test_board_watch_drains_all_pages(client, api_http, add_api_response):
    add_api_response(
        api_http,
        responses.GET,
        "/v3/streams/contents",
        {"id": "board", "items": [{"id": "a"}], "continuation": "next"},
    )
    add_api_response(
        api_http, responses.GET, "/v3/streams/contents", {"id": "board", "items": [{"id": "b"}]}
    )
    result = client.board_watch("board", count=1, max_pages=2)
    assert [item["id"] for item in result["items"]] == ["a", "b"]
    assert result["pages"] == 2
    assert result["id"] == "board"


def test_board_watch_fails_without_partial_output_when_bound_reached(
    client, api_http, add_api_response
):
    add_api_response(
        api_http,
        responses.GET,
        "/v3/streams/contents",
        {"items": [{"id": "a"}], "continuation": "next"},
    )
    with pytest.raises(FeedlyError) as caught:
        client.board_watch("board", max_pages=1)
    assert caught.value.code == "api_error"
    assert len(api_http.calls) == 1


def test_add_url_scans_exact_url_and_dry_run_skips_write(client, api_http, add_api_response):
    url = "https://example.test/article"
    add_api_response(
        api_http,
        responses.GET,
        "/v3/streams/contents",
        {"items": [{"id": "wrong", "canonicalUrl": url + "/no"}], "continuation": "next"},
    )
    add_api_response(
        api_http,
        responses.GET,
        "/v3/streams/contents",
        {"items": [{"id": "right", "alternate": [{"href": url}]}]},
    )
    result = client.add_url_to_board("enterprise/a/tag/b", url, stream_id="source", dry_run=True)
    assert result == {
        "boardId": "enterprise/a/tag/b",
        "entryId": "right",
        "url": url,
        "dryRun": True,
    }
    assert len(api_http.calls) == 2
    assert all(call.request.method == "GET" for call in api_http.calls)


def test_add_url_scans_then_puts_once(client, api_http, add_api_response, decode_request_json):
    url = "https://example.test/article"
    add_api_response(
        api_http,
        responses.GET,
        "/v3/streams/contents",
        {"items": [{"id": "article", "canonicalUrl": url}]},
    )
    add_api_response(api_http, responses.PUT, "/v3/tags/enterprise%2Fa%2Ftag%2Fb", None)
    client.add_url_to_board("enterprise/a/tag/b", url, stream_id="source")
    assert len(api_http.calls) == 2
    assert api_http.calls[1].request.method == "PUT"
    assert decode_request_json(api_http.calls[1]) == {"entryId": "article"}


def test_add_url_missing_exact_match_never_writes(client, api_http, add_api_response):
    add_api_response(
        api_http,
        responses.GET,
        "/v3/streams/contents",
        {"items": [{"id": "wrong", "canonicalUrl": "https://example.test/no"}]},
    )
    with pytest.raises(FeedlyError) as caught:
        client.add_url_to_board(
            "enterprise/a/tag/b", "https://example.test/wanted", stream_id="source"
        )
    assert caught.value.code == "not_found"
    assert all(call.request.method == "GET" for call in api_http.calls)
