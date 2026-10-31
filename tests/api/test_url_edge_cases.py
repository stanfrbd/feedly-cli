import pytest
import responses

from feedly_cli.api.url_resolution import entry_matches_url, validate_url
from feedly_cli.errors import FeedlyError

VALID_URLS = [
    "https://example.test/article?utm_source=mail&id=42",
    "https://example.test/article?id=42&id=43&blank=&flag",
    "https://example.test/article?b=2&a=1",
    "https://example.test/article?",
    "https://example.test/article#section",
    "https://example.test/article#",
    "https://example.test/a%2Fb?value=%26%3D%23",
    "https://example.test/%7euser",
    "https://example.test/Caf\u00e9",
    "https://b\u00fccher.example/article",
    "https://xn--bcher-kva.example/article",
    "HTTPS://EXAMPLE.TEST:443/Article/",
    "http://example.test:80/",
    "https://[2001:db8::1]:443/article",
    "https://127.0.0.1/article",
]

INVALID_URLS = [
    "",
    "/article",
    "//example.test/article",
    "example.test/article",
    "file:///article",
    "ftp://example.test/article",
    "mailto:user@example.test",
    "javascript:alert(1)",
    "https:///article",
    "https://",
    "https://user:password@example.test/article",
    "https://user@example.test/",
    " https://example.test/",
    "https://example.test/a b",
    "https://example.test/\n",
    "https://example.test/\x00",
    "https://example.test/\u202e",
    "https://example.test/%",
    "https://example.test/%GG",
    "https://example.test:bad/",
    "https://example.test:65536/",
    "https://example.test:0/",
    "https://example.test:/",
    "https://[bad]/",
    "https://[::1",
    "https://bad..host/",
    "https://-bad.test/",
    "https://example.test\\evil",
    "https://example.test/<script>",
    "https://example.test/\ud800",
    "https://%65xample.test/",
    "https://[fe80::1%25zone]/",
    "https://[::1]evil/",
    "https://999.999.999.999/article",
    "https://example.test/article?array[]=x",
]


@pytest.mark.parametrize("url", VALID_URLS)
def test_valid_url_spelling_is_preserved_and_exact(url):
    validate_url(url)
    assert entry_matches_url({"canonicalUrl": url}, url)
    assert entry_matches_url({"alternate": [{"href": url}]}, url)


@pytest.mark.parametrize("url", INVALID_URLS)
def test_invalid_url_raises_generic_error_without_echoing_input(url):
    with pytest.raises(FeedlyError) as caught:
        validate_url(url)
    assert caught.value.code == "bad_request"
    assert "password" not in str(caught.value) and "<script>" not in str(caught.value)


@pytest.mark.parametrize(
    ("stored", "requested"),
    [
        ("https://example.test/article", "https://example.test/article?utm_source=mail"),
        ("https://example.test/article?id=1", "https://example.test/article?id=2"),
        ("https://example.test/article?a=1&b=2", "https://example.test/article?b=2&a=1"),
        ("https://example.test/article?a=1&a=2", "https://example.test/article?a=2&a=1"),
        ("https://example.test/article?a=", "https://example.test/article?a"),
        ("https://example.test/article", "https://example.test/article?"),
        ("https://example.test/article", "https://example.test/article#section"),
        ("https://example.test/article", "https://example.test/article#"),
        ("https://example.test/a%2Fb", "https://example.test/a/b"),
        ("https://example.test/a%26b", "https://example.test/a&b"),
        ("https://example.test/%7Euser", "https://example.test/~user"),
        ("https://example.test/Caf%C3%A9", "https://example.test/Caf\u00e9"),
        ("https://xn--bcher-kva.example/article", "https://b\u00fccher.example/article"),
        ("https://example.test/article", "HTTPS://EXAMPLE.TEST/article"),
        ("https://example.test/article", "https://example.test:443/article"),
        ("https://example.test/Article", "https://example.test/article"),
        ("https://example.test/article", "https://example.test/article/"),
        ("http://example.test/article", "https://example.test/article"),
    ],
)
def test_variants_are_not_heuristically_equated(stored, requested):
    validate_url(stored)
    validate_url(requested)
    assert not entry_matches_url({"canonicalUrl": stored}, requested)


@pytest.mark.parametrize("url", VALID_URLS)
@pytest.mark.parametrize("board", [False, True])
def test_real_parameter_shapes_shared_exact_resolution(
    client, api_http, add_api_response, url, board
):
    add_api_response(
        api_http,
        responses.GET,
        "/v3/streams/contents",
        {"items": [{"id": "entry", "canonicalUrl": url}]},
    )
    if board:
        result = client.add_url_to_board("board", url, stream_id="source", dry_run=True)
    else:
        result = client.resolve_article_url(url, stream_id="source")
    assert result["entryId"] == "entry" and result["url"] == url
    assert all(call.request.method == "GET" for call in api_http.calls)


@pytest.mark.parametrize("board", [False, True])
def test_ambiguous_same_page_ids_fail_never_write(client, api_http, add_api_response, board):
    url = "https://example.test/article?id=42"
    add_api_response(
        api_http,
        responses.GET,
        "/v3/streams/contents",
        {"items": [{"id": "one", "canonicalUrl": url}, {"id": "two", "url": url}]},
    )
    with pytest.raises(FeedlyError, match="ambiguous"):
        if board:
            client.add_url_to_board("board", url, stream_id="source")
        else:
            client.resolve_article_url(url, stream_id="source")
    assert all(call.request.method == "GET" for call in api_http.calls)


def test_duplicate_same_id_and_alternate_match_are_not_ambiguous(
    client, api_http, add_api_response
):
    url = "https://example.test/article?ref=mail"
    add_api_response(
        api_http,
        responses.GET,
        "/v3/streams/contents",
        {
            "items": [
                {
                    "id": "one",
                    "canonicalUrl": "https://example.test/preferred",
                    "alternate": [{"href": url}],
                },
                {"id": "one", "url": url},
            ]
        },
    )
    assert client.resolve_article_url(url, stream_id="source")["entryId"] == "one"


def test_empty_intermediate_page_and_continuation_cycle(client, api_http, add_api_response):
    url = "https://example.test/article"
    for continuation in ("one", "two", "one"):
        add_api_response(
            api_http,
            responses.GET,
            "/v3/streams/contents",
            {"items": [], "continuation": continuation},
        )
    with pytest.raises(FeedlyError, match="repeated"):
        client.resolve_article_url(url, stream_id="source", max_pages=5)
    assert len(api_http.calls) == 3


def test_empty_intermediate_page_then_match(client, api_http, add_api_response):
    url = "https://example.test/article"
    add_api_response(
        api_http, responses.GET, "/v3/streams/contents", {"items": [], "continuation": "one"}
    )
    add_api_response(
        api_http,
        responses.GET,
        "/v3/streams/contents",
        {"items": [{"id": "entry", "canonicalUrl": url}]},
    )
    assert client.resolve_article_url(url, stream_id="source")["pagesScanned"] == 2


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_service_errors_are_not_converted_to_no_match(client, api_http, add_api_response, status):
    add_api_response(
        api_http, responses.GET, "/v3/streams/contents", {"message": "denied"}, status=status
    )
    with pytest.raises(FeedlyError) as caught:
        client.resolve_article_url("https://example.test/article", stream_id="source")
    assert caught.value.status == status and caught.value.code != "not_found"


@pytest.mark.parametrize("entry_id", [None, "", " ", 3, [], "entry\nid"])
def test_invalid_article_ids_are_not_silently_skipped(client, api_http, add_api_response, entry_id):
    add_api_response(
        api_http,
        responses.GET,
        "/v3/streams/contents",
        {"items": [{"id": entry_id, "canonicalUrl": "https://example.test/unrelated"}]},
    )
    with pytest.raises(FeedlyError, match="no valid Feedly entry ID"):
        client.resolve_article_url("https://example.test/wanted", stream_id="source")


@pytest.mark.parametrize("continuation", [0, False, "", " "])
def test_invalid_initial_continuation_fails_without_request(client, api_http, continuation):
    with pytest.raises(FeedlyError, match="continuation"):
        client.resolve_article_url(
            "https://example.test/article", stream_id="source", continuation=continuation
        )
    assert not api_http.calls
