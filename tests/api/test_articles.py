from __future__ import annotations

import pytest
import responses

from feedly_cli.api.articles import ArticleAPI
from feedly_cli.errors import FeedlyError


def test_entry_uses_encoded_id(client, api_http, add_api_response):
    add_api_response(api_http, responses.GET, "/v3/entries/a%2Fb%3Fc", {"id": "a/b?c"})
    assert client.entry("a/b?c")["id"] == "a/b?c"


def test_article_resource_uses_injected_transport(client, api_http, add_api_response):
    add_api_response(api_http, responses.GET, "/v3/entries/article", {"id": "article"})
    resource = ArticleAPI(client._transport)
    assert resource.entry("article")["id"] == "article"


def test_entries_posts_json_id_list(client, api_http, add_api_response, decode_request_json):
    add_api_response(api_http, responses.POST, "/v3/entries/.mget", [{"id": "a"}, {"id": "b"}])
    assert [entry["id"] for entry in client.entries(["a", "b"])] == ["a", "b"]
    assert decode_request_json(api_http.calls[0]) == ["a", "b"]


def test_fetch_search_result_batches_at_100_and_preserves_order(
    client, api_http, add_api_response, decode_request_json
):
    items = [{"id": str(i)} for i in range(101)]
    add_api_response(api_http, responses.POST, "/v3/entries/.mget", list(reversed(items[:100])))
    add_api_response(api_http, responses.POST, "/v3/entries/.mget", items[100:])
    result = client.fetch_search_result({"items": items, "continuation": "next"})
    assert [item["id"] for item in result["items"]] == [str(i) for i in range(101)]
    assert result["continuation"] == "next"
    assert [len(decode_request_json(call)) for call in api_http.calls] == [100, 1]


def test_fetch_fails_when_any_full_metadata_is_missing(client, api_http, add_api_response):
    add_api_response(api_http, responses.POST, "/v3/entries/.mget", [{"id": "a"}])
    with pytest.raises(FeedlyError) as caught:
        client.fetch_search_result({"items": [{"id": "a"}, {"id": "b"}]})
    assert caught.value.code == "api_error"
    assert caught.value.details["missingIds"] == ["b"]


def test_entries_enforce_batch_limit_before_request(client, api_http):
    with pytest.raises(FeedlyError):
        client.entries([])
    assert not api_http.calls
