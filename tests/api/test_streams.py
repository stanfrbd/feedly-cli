import responses

from feedly_cli.api.streams import StreamAPI


def test_stream_contents_builds_query_and_unread_flag(
    client, api_http, add_api_response, request_query_params
):
    add_api_response(api_http, responses.GET, "/v3/streams/contents", {"items": []})
    client.stream_contents("enterprise/a/tag/b", 3, "opaque", True)
    params = request_query_params(api_http.calls[0])
    assert params == {
        "streamID": "enterprise/a/tag/b",
        "count": "3",
        "continuation": "opaque",
        "unreadOnly": "true",
    }


def test_stream_resource_uses_injected_transport(client, api_http, add_api_response):
    add_api_response(api_http, responses.GET, "/v3/streams/contents", {"items": []})
    resource = StreamAPI(client._transport)
    assert resource.contents("stream")["items"] == []
