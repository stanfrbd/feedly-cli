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


def test_date_search_filters_publication_not_crawl_time_and_keeps_continuation(
    client, api_http, add_api_response, request_query_params
):
    add_api_response(
        api_http,
        responses.POST,
        "/v3/search/contents",
        {
            "items": [
                {"id": "before", "published": 9, "crawled": 15},
                {"id": "start", "published": 10, "crawled": 1},
                {"id": "inside", "published": 19},
                {"id": "end", "published": 20},
            ],
            "continuation": "next",
        },
    )
    result = client.search({"layers": []}, since=10, before=20, count=4)
    assert [item["id"] for item in result["items"]] == ["start", "inside"]
    assert result["continuation"] == "next"
    assert request_query_params(api_http.calls[0])["count"] == "4"


def test_dated_all_search_does_not_stop_at_empty_filtered_page_and_hydrates_matches_only(
    client, api_http, add_api_response, decode_request_json
):
    for page in (
        {"items": [{"id": "future", "published": 21}], "continuation": "next"},
        {"items": [{"id": "a", "published": 10}], "continuation": "last"},
        {"items": [{"id": "a", "published": 10}, {"id": "b", "published": 19}]},
    ):
        add_api_response(api_http, responses.POST, "/v3/search/contents", page)
    add_api_response(
        api_http,
        responses.POST,
        "/v3/entries/.mget",
        [{"id": "a", "published": 10}, {"id": "b", "published": 19}],
    )
    result = client.search_all({"layers": []}, since=10, before=20, fetch=True)
    assert [item["id"] for item in result["items"]] == ["a", "b"]
    assert result["pages"] == 3 and "continuation" not in result
    assert decode_request_json(api_http.calls[3]) == ["a", "b"]


def test_date_search_page_limit_fails_even_when_filtered_page_is_empty(
    client, api_http, add_api_response
):
    add_api_response(
        api_http,
        responses.POST,
        "/v3/search/contents",
        {"items": [{"id": "out", "published": 1}], "continuation": "next"},
    )
    with pytest.raises(FeedlyError, match="max_pages"):
        client.search_all({"layers": []}, since=10, before=20, max_pages=1)


def test_invalid_date_bounds_fail_before_any_api_request(client, api_http):
    for operation in (client.search, client.search_all):
        with pytest.raises(FeedlyError, match="earlier"):
            operation("x", since=20, before=10)
    assert not api_http.calls
