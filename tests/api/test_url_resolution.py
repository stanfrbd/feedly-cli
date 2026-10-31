import pytest
import responses

from feedly_cli.errors import FeedlyError

URL = "https://example.test/article"


@pytest.mark.parametrize(
    "links",
    [
        {"canonicalUrl": URL},
        {"url": URL},
        {"alternate": [{"href": URL}]},
        {"alternate": {"href": URL}},
    ],
)
def test_resolve_url_exact_links_no_writes(
    client, api_http, add_api_response, request_query_params, links
):
    add_api_response(
        api_http,
        responses.GET,
        "/v3/streams/contents",
        {"items": [{"id": "entry", **links}]},
    )
    result = client.resolve_article_url(URL, stream_id="source", continuation="prior", count=2)
    assert result == {"entryId": "entry", "url": URL, "streamId": "source", "pagesScanned": 1}
    assert request_query_params(api_http.calls[0])["continuation"] == "prior"
    assert request_query_params(api_http.calls[0])["count"] == "2"
    assert all(call.request.method == "GET" for call in api_http.calls)


def test_resolver_uses_default_enterprise_stream(client, api_http, add_api_response):
    add_api_response(api_http, responses.GET, "/v3/profile", {"enterpriseName": "example"})
    add_api_response(
        api_http,
        responses.GET,
        "/v3/streams/contents",
        {"items": [{"id": "entry", "canonicalUrl": URL}]},
    )
    assert client.resolve_article_url(URL)["streamId"] == "enterprise/example/category/global.all"


def test_resolver_requires_source_when_no_enterprise_default(client, api_http, add_api_response):
    add_api_response(api_http, responses.GET, "/v3/profile", {})
    with pytest.raises(FeedlyError, match="source-stream"):
        client.resolve_article_url(URL)
    assert len(api_http.calls) == 1


def test_resolve_paginates_and_does_not_normalize_url(client, api_http, add_api_response):
    add_api_response(
        api_http,
        responses.GET,
        "/v3/streams/contents",
        {"items": [{"id": "wrong", "canonicalUrl": URL + "/"}], "continuation": "next"},
    )
    add_api_response(
        api_http,
        responses.GET,
        "/v3/streams/contents",
        {"items": [{"id": "right", "alternate": [{"href": URL}]}]},
    )
    assert client.resolve_article_url(URL, stream_id="source")["pagesScanned"] == 2


def test_exhausted_stream_no_match_is_not_found(client, api_http, add_api_response):
    add_api_response(api_http, responses.GET, "/v3/streams/contents", {"items": []})
    with pytest.raises(FeedlyError) as caught:
        client.resolve_article_url(URL, stream_id="source")
    assert caught.value.code == "not_found" and caught.value.status == 404
    assert caught.value.details["pagesScanned"] == 1
    assert "exhausted" in str(caught.value) and "global absence" in str(caught.value)


@pytest.mark.parametrize("board", [False, True])
def test_limit_is_incomplete_not_not_found_and_never_writes(
    client, api_http, add_api_response, board
):
    add_api_response(
        api_http,
        responses.GET,
        "/v3/streams/contents",
        {"items": [], "continuation": "resume-token"},
    )
    with pytest.raises(FeedlyError) as caught:
        if board:
            client.add_url_to_board("board", URL, stream_id="source", max_pages=1)
        else:
            client.resolve_article_url(URL, stream_id="source", max_pages=1)
    assert caught.value.code == "api_error"
    assert caught.value.details["continuation"] == "resume-token"
    assert "incomplete" in str(caught.value)
    assert len(api_http.calls) == 1 and api_http.calls[0].request.method == "GET"


@pytest.mark.parametrize(
    "page",
    [
        [],
        {},
        {"items": None},
        {"items": ["bad"]},
        {"items": [], "continuation": 3},
        {"items": [{"canonicalUrl": URL}]},
    ],
)
@pytest.mark.parametrize("board", [False, True])
def test_malformed_pages_and_matching_id_fail_without_writes(
    client, api_http, add_api_response, page, board
):
    add_api_response(api_http, responses.GET, "/v3/streams/contents", page)
    with pytest.raises(FeedlyError) as caught:
        if board:
            client.add_url_to_board("board", URL, stream_id="source")
        else:
            client.resolve_article_url(URL, stream_id="source")
    assert caught.value.code == "api_error"
    assert all(call.request.method == "GET" for call in api_http.calls)


def test_repeated_continuation_fails(client, api_http, add_api_response):
    add_api_response(
        api_http,
        responses.GET,
        "/v3/streams/contents",
        {"items": [], "continuation": "same"},
    )
    with pytest.raises(FeedlyError, match="repeated"):
        client.resolve_article_url(URL, stream_id="source", continuation="same")


@pytest.mark.parametrize(("count", "max_pages"), [(0, 1), (101, 1), (1, 0), (1, 101)])
def test_resolver_invalid_limits_no_scan(client, api_http, count, max_pages):
    with pytest.raises(FeedlyError, match="between 1 and 100"):
        client.resolve_article_url(URL, stream_id="source", count=count, max_pages=max_pages)
    assert not api_http.calls
