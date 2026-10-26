# Contributing

## Development setup

```sh
python -m pip install -e '.[dev]'
pre-commit install
python -m pytest
pre-commit run --all-files
```

Tests do not require a Feedly account or `FEEDLY_TOKEN`. The shared test fixture removes the token from the test environment and blocks socket connections. Mock every external request.

## Code layout

The package uses a `src` layout with three separate layers:

| Location | Responsibility |
| --- | --- |
| `src/feedly_cli/client.py` | Public client facade and resource composition |
| `src/feedly_cli/api/` | SDK transport, API resources and article workflows |
| `src/feedly_cli/cli/` | Global parser, output selection, errors and process lifecycle |
| `src/feedly_cli/commands/` | Per-command argument registration and execution |
| `src/feedly_cli/output/` | Human-readable views, Markdown conversion and response field extraction |
| `tests/api/` | Mocked HTTP contracts, transport errors and workflow tests |
| `tests/cli/` | Command parsing and execution with mocked clients |
| `tests/output/` | Deterministic rendering and Markdown tests using synthetic data |

The transport owns authentication, timeouts, SDK calls and HTTP error normalization. Resource modules implement one API area each. `FeedlyClient` composes those resources and preserves its public methods through explicit delegation.

Command modules register their own arguments and handlers. The application entry point owns parsing, client cleanup and exit status; it should not contain endpoint-specific workflows. Output modules only render supplied data and must never issue API requests.

The request path is `command handler -> FeedlyClient -> API resource -> APITransport -> official SDK`. Results return to the presentation layer. The API package does not import commands or output modules.

Keep changes with the responsibility they belong to. Prefer a direct function or a small resource class over a general framework, dynamic method forwarding or inheritance used only to distribute methods across files.

## Adding an API operation

1. Verify the endpoint, request fields and permissions in the [official Feedly reference](https://developers.feedly.com/reference/introduction).
2. Implement it in the matching resource module, reusing the shared transport. Add an explicit client facade method if the operation should be public.
3. Add or extend the matching command handler and its argument registration.
4. Add human output in the appropriate presentation module. Preserve the raw response for `--json`.
5. Add tests next to the affected API, command and rendering areas.

## Mock tests

Follow the same HTTP mocking approach as Cyberbro: register synthetic responses with `responses`, execute the real SDK-backed client, and assert the outgoing URL, method, headers and JSON payload. Exercise successful responses, relevant error statuses and pagination boundaries. Use `unittest.mock` for command clients, time, and other external collaborators.

For example:

```python
import responses

from feedly_cli.client import FeedlyClient


@responses.activate
def test_list_boards():
    responses.add(
        responses.GET,
        "https://api.feedly.com/v3/enterprise/tags",
        json=[{"id": "enterprise/example/tag/research", "label": "Research"}],
        status=200,
    )
    with FeedlyClient(token="test-token") as client:
        assert client.boards()[0]["label"] == "Research"
    assert responses.calls[0].request.headers["Authorization"] == "Bearer test-token"
```

Use synthetic tokens and article data. Never save live API responses or account identifiers in fixtures. Avoid tests that only repeat an internal delegation; test the request contract or externally visible result.

`scripts/smoke.py` is a separate, optional live diagnostic. It needs a real token, consumes API quota, and is not run by pytest or CI.
