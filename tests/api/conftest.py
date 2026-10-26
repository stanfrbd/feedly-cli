"""Reusable responses-backed Feedly SDK fixtures for API resource tests."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
import responses

from feedly_cli.client import FeedlyClient

API_BASE = "https://api.feedly.com"
TEST_TOKEN = "api-test-token"


@pytest.fixture
def api_http():
    with responses.RequestsMock() as mocked:
        yield mocked


@pytest.fixture
def client(api_http):
    instance = FeedlyClient(token=TEST_TOKEN, timeout=9)
    yield instance
    instance.close()


@pytest.fixture
def add_api_response():
    return add_json


@pytest.fixture
def add_text_response():
    return add_text


@pytest.fixture
def decode_request_json():
    return request_json


def add_json(
    mocked: responses.RequestsMock,
    method: str,
    path: str,
    payload: Any,
    status: int = 200,
) -> None:
    mocked.add(
        method,
        f"{API_BASE}{path}",
        json=payload,
        status=status,
        content_type="application/json",
    )


def add_text(
    mocked: responses.RequestsMock,
    method: str,
    path: str,
    body: str,
    status: int,
) -> None:
    mocked.add(method, f"{API_BASE}{path}", body=body, status=status, content_type="text/html")


def request_json(call: responses.Call) -> Any:
    body = call.request.body
    if isinstance(body, bytes):
        body = body.decode()
    return json.loads(body) if body else None


@pytest.fixture
def request_query_params():
    def decode(call: responses.Call) -> dict[str, str]:
        params = parse_qs(urlparse(call.request.url).query)
        return {key: values[-1] for key, values in params.items() if key != "client"}

    return decode
