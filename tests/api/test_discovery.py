import responses

from feedly_cli.api.discovery import DiscoveryAPI


def test_profile_caches_enterprise_global_stream(client, api_http, add_api_response):
    add_api_response(api_http, responses.GET, "/v3/profile", {"enterpriseName": "example"})
    assert (
        client._discovery_api.default_enterprise_stream()
        == "enterprise/example/category/global.all"
    )
    assert len(api_http.calls) == 1


def test_discovery_collections_use_documented_endpoints(client, api_http, add_api_response):
    add_api_response(api_http, responses.GET, "/v3/enterprise/tags", [{"id": "board"}])
    add_api_response(api_http, responses.GET, "/v3/enterprise/collections", [{"id": "folder"}])
    add_api_response(api_http, responses.GET, "/v3/alerts", [{"id": "alert"}])
    assert client.boards() == [{"id": "board"}]
    assert client.folders() == [{"id": "folder"}]
    assert client.feeds() == [{"id": "alert"}]
    assert len(api_http.calls) == 3


def test_discovery_resource_works_with_shared_transport(client, api_http, add_api_response):
    add_api_response(api_http, responses.GET, "/v3/profile", {"id": "user"})
    resource = DiscoveryAPI(client._transport)
    assert resource.profile() == {"id": "user"}
