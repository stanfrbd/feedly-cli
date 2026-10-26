import pytest
import responses

from feedly_cli.api.vulnerabilities import VulnerabilityAPI
from feedly_cli.errors import FeedlyError


def test_cve_get_batch_trending_and_dashboard_search(
    client, api_http, add_api_response, decode_request_json, request_query_params
):
    add_api_response(
        api_http, responses.GET, "/v3/entities/CVE-2021-44228", {"cveid": "CVE-2021-44228"}
    )
    add_api_response(api_http, responses.POST, "/v3/entities/.mget", [{"cveid": "CVE-2021-44228"}])
    add_api_response(api_http, responses.GET, "/v3/memes/vulnerabilities/en", {"memes": []})
    add_api_response(
        api_http, responses.POST, "/v3/trends/vulnerability-dashboard", {"vulnerabilities": []}
    )
    assert client.cve("CVE-2021-44228")["cveid"] == "CVE-2021-44228"
    client.cves(["CVE-2021-44228"], with_stats=True)
    assert decode_request_json(api_http.calls[1]) == ["CVE-2021-44228"]
    assert request_query_params(api_http.calls[1]) == {"withStats": "true"}
    client.cve_trending(25)
    client.cve_search({"layers": []}, count=20, continuation="next")
    assert decode_request_json(api_http.calls[3]) == {
        "layers": [],
        "count": 20,
        "continuation": "next",
    }


def test_vulnerability_resource_uses_injected_transport(client, api_http, add_api_response):
    add_api_response(
        api_http, responses.GET, "/v3/entities/CVE-2021-44228", {"cveid": "CVE-2021-44228"}
    )
    resource = VulnerabilityAPI(client._transport)
    assert resource.cve("CVE-2021-44228")["cveid"] == "CVE-2021-44228"


@pytest.mark.parametrize(("method", "arg"), [("cves", []), ("cve_trending", 26)])
def test_cve_limits_fail_before_request(client, api_http, method, arg):
    with pytest.raises(FeedlyError):
        getattr(client, method)(arg)
    assert not api_http.calls
