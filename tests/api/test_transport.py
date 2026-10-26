from __future__ import annotations

import logging
from unittest.mock import Mock

import pytest
import requests
import responses

from feedly_cli.errors import FeedlyError


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (400, "bad_request"),
        (401, "authentication_error"),
        (403, "permission_denied"),
        (404, "not_found"),
        (429, "rate_limited"),
        (500, "server_error"),
        (503, "server_error"),
    ],
)
def test_http_errors_keep_status_and_do_not_retry(client, api_http, add_api_response, status, code):
    add_api_response(api_http, responses.GET, "/v3/profile", {"message": "request failed"}, status)
    with pytest.raises(FeedlyError) as caught:
        client.profile()
    assert caught.value.code == code
    assert caught.value.status == status
    assert len(api_http.calls) == 1


def test_non_json_http_error_preserves_status_and_suppresses_sdk_stderr(
    client, api_http, add_text_response, capsys
):
    add_text_response(api_http, responses.GET, "/v3/profile", "<html>Forbidden</html>", 403)
    with pytest.raises(FeedlyError) as caught:
        client.profile()
    assert caught.value.code == "permission_denied"
    assert caught.value.status == 403
    assert capsys.readouterr().err == ""


def test_session_uses_bearer_token_and_api_host(client, api_http, add_api_response):
    add_api_response(api_http, responses.GET, "/v3/profile", {"id": "user"})
    assert client.profile() == {"id": "user"}
    call = api_http.calls[0]
    assert call.request.headers["Authorization"] == "Bearer api-test-token"
    assert call.request.url.startswith("https://api.feedly.com/v3/profile?")
    assert "client=feedly-cli" in call.request.url


def test_sdk_logger_configuration_is_restored(client, api_http, add_api_response):
    logger = logging.getLogger("feedly.api_client.session")
    prior = logger.disabled
    logger.disabled = False
    try:
        add_api_response(api_http, responses.GET, "/v3/profile", {"message": "forbidden"}, 403)
        with pytest.raises(FeedlyError):
            client.profile()
        assert logger.disabled is False
    finally:
        logger.disabled = prior


def test_public_client_keeps_session_attribute_and_composed_resources(client):
    assert client.session is client._transport.session


def test_sdk_receives_explicit_timeout(client, monkeypatch):
    response = requests.Response()
    response.status_code = 200
    response._content = b"{}"
    response.headers["Content-Type"] = "application/json"
    call = Mock(return_value=response)
    monkeypatch.setattr(requests.Session, "request", call)
    # The SDK session is created by the fixture; route capture bound its request
    # method during construction, so patch that original request seam directly.
    client.session.session.request = call
    client.profile()
    assert call.call_args.kwargs["timeout"] == 9


def test_public_timeout_changes_live_transport_timeout(client, monkeypatch):
    response = requests.Response()
    response.status_code = 200
    response._content = b"{}"
    response.headers["Content-Type"] = "application/json"
    call = Mock(return_value=response)
    monkeypatch.setattr(client.session.session, "request", call)
    client.timeout = 30
    client.profile()
    assert call.call_args.kwargs["timeout"] == 30


def test_connection_failure_is_normalized_once(monkeypatch):
    call = Mock(side_effect=requests.ConnectionError("offline"))
    monkeypatch.setattr(requests.Session, "request", call)
    from feedly_cli.client import FeedlyClient

    client = FeedlyClient(token="api-test-token")
    try:
        with pytest.raises(FeedlyError) as caught:
            client.profile()
        assert caught.value.code == "network_error"
        assert call.call_count == 1
    finally:
        client.close()


def test_injected_session_falsey_http_response_keeps_status():
    session = Mock(spec=["do_api_request"])
    response = requests.Response()
    response.status_code = 404
    response._content = b'{"message":"missing"}'
    session.do_api_request.side_effect = requests.HTTPError(response=response)
    from feedly_cli.client import FeedlyClient

    client = FeedlyClient(session=session)
    with pytest.raises(FeedlyError) as caught:
        client.profile()
    assert caught.value.status == 404
    assert caught.value.code == "not_found"


def test_close_releases_sdk_transport(client, monkeypatch):
    close = Mock()
    monkeypatch.setattr(client.session.session, "close", close)
    client.close()
    close.assert_called_once_with()
