from __future__ import annotations

import pytest
import responses

from feedly_cli.api.search import SearchAPI
from feedly_cli.errors import FeedlyError


def test_search_raw_dict_is_forwarded_and_query_params_are_preserved(
    client, api_http, add_api_response, decode_request_json, request_query_params
):
    payload = {"layers": [], "source": {"items": []}}
    add_api_response(api_http, responses.POST, "/v3/search/contents", {"items": []})
    client.search(payload, count=7, continuation="next")
    assert decode_request_json(api_http.calls[0]) == payload
    assert request_query_params(api_http.calls[0]) == {"count": "7", "continuation": "next"}


def test_search_resource_posts_raw_query(client, api_http, add_api_response, decode_request_json):
    payload = {"layers": [{"type": "security"}]}
    add_api_response(api_http, responses.POST, "/v3/search/contents", {"items": []})
    resource = SearchAPI(client._transport, client._article_api, client._discovery_api)
    assert resource.search(payload)["items"] == []
    assert decode_request_json(api_http.calls[0]) == payload


def test_text_search_salience_is_sent_in_layer(
    client, api_http, add_api_response, decode_request_json
):
    add_api_response(api_http, responses.GET, "/v3/profile", {"enterpriseName": "example"})
    add_api_response(api_http, responses.POST, "/v3/search/contents", {"items": []})
    client.search("php2shell", salience="about")
    assert decode_request_json(api_http.calls[1])["layers"][0]["salience"] == "about"


def test_text_search_derives_enterprise_global_stream(
    client, api_http, add_api_response, decode_request_json
):
    add_api_response(api_http, responses.GET, "/v3/profile", {"enterpriseName": "example"})
    add_api_response(api_http, responses.POST, "/v3/search/contents", {"items": []})
    client.search("security")
    assert decode_request_json(api_http.calls[1])["source"] == {
        "items": [{"type": "stream", "id": "enterprise/example/category/global.all"}]
    }


def test_search_all_drains_deduplicates_and_fetches_full_metadata(
    client, api_http, add_api_response, decode_request_json
):
    add_api_response(
        api_http,
        responses.POST,
        "/v3/search/contents",
        {"items": [{"id": "a"}, {"id": "b"}], "continuation": "next"},
    )
    add_api_response(
        api_http, responses.POST, "/v3/search/contents", {"items": [{"id": "b"}, {"id": "c"}]}
    )
    add_api_response(
        api_http,
        responses.POST,
        "/v3/entries/.mget",
        [
            {"id": "a", "content": {"content": "full"}},
            {"id": "b", "title": "b"},
            {"id": "c", "title": "c"},
        ],
    )
    result = client.search_all({"layers": []}, count=2, fetch=True)
    assert [item["id"] for item in result["items"]] == ["a", "b", "c"]
    assert result["items"][0]["content"]["content"] == "full"
    assert result["pages"] == 2
    assert "continuation" not in result
    assert decode_request_json(api_http.calls[2]) == ["a", "b", "c"]


@pytest.mark.parametrize("continuations", [["same", "same"], ["one", "two"]])
def test_search_all_fails_on_repeat_or_remaining_pages(
    client, api_http, add_api_response, continuations
):
    for index, continuation in enumerate(continuations):
        add_api_response(
            api_http,
            responses.POST,
            "/v3/search/contents",
            {"items": [{"id": str(index)}], "continuation": continuation},
        )
    with pytest.raises(FeedlyError) as caught:
        client.search_all({"layers": []}, max_pages=len(continuations))
    assert caught.value.code == "api_error"
    assert len(api_http.calls) == len(continuations)


def test_search_all_validates_pagination_limits_before_request(client, api_http):
    with pytest.raises(FeedlyError):
        client.search_all({"layers": []}, count=101)
    with pytest.raises(FeedlyError):
        client.search_all({"layers": []}, max_pages=0)
    assert not api_http.calls
