"""Authentication, HTTP transport, and shared error normalization."""

from __future__ import annotations

import logging
import os
from typing import Any

from feedly_cli.errors import FeedlyError

DEFAULT_API_BASE = "https://api.feedly.com"
DEFAULT_TIMEOUT = 15


class APITransport:
    """Own a Feedly SDK session and issue normalized API requests."""

    def __init__(
        self,
        token: str | None = None,
        *,
        session: Any = None,
        api_base: str = DEFAULT_API_BASE,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.timeout = timeout
        self.api_base = api_base.rstrip("/")
        self._token: str | None = None
        if session is None:
            token = token if token is not None else os.environ.get("FEEDLY_TOKEN")
            if not token:
                raise FeedlyError(
                    "configuration_error",
                    "Feedly API token is required; set FEEDLY_TOKEN or pass token=.",
                )
            try:
                from feedly.api_client.session import FeedlySession
            except ImportError as exc:
                raise FeedlyError(
                    "configuration_error",
                    "The official feedly-client package is required. "
                    "Install the project dependencies.",
                ) from exc

            authorization = token.strip()
            self._token = (
                authorization[7:] if authorization[:7].lower() == "bearer " else authorization
            )
            if not authorization.lower().startswith("bearer "):
                authorization = f"Bearer {authorization}"
            session = FeedlySession(
                auth=authorization,
                api_host=self.api_base,
                client_name="feedly-cli",
            )
        self.session = session
        if hasattr(session, "timeout"):
            session.timeout = timeout
        self._last_response: Any = None
        transport_session = getattr(session, "session", None)
        if transport_session is not None and hasattr(transport_session, "request"):
            original_request = transport_session.request

            def capture_response(*args: Any, **kwargs: Any) -> Any:
                response = original_request(*args, **kwargs)
                self._last_response = response
                return response

            transport_session.request = capture_response
        self._sdk_logger = logging.getLogger("feedly.api_client.session")

    def request(
        self,
        path: str,
        *,
        method: str = "get",
        params: dict[str, Any] | None = None,
        data: Any = None,
    ) -> Any:
        """Send one request. SDK retries are disabled to protect writes."""
        self._last_response = None
        prior_disabled = self._sdk_logger.disabled
        self._sdk_logger.disabled = True
        try:
            return self.session.do_api_request(
                path,
                method=method,
                params=params,
                data=data,
                timeout=self.timeout,
                max_tries=1,
            )
        except FeedlyError:
            raise
        except Exception as exc:
            response = getattr(exc, "response", None)
            if response is None:
                response = self._last_response
            status = getattr(response, "status_code", None)
            details = _redact(_response_details(response), self._token)
            code, default_message = _error_kind(status)
            message = _error_message(details) or default_message
            if status is None:
                code = "network_error"
                message = "Unable to reach the Feedly API."
            raise FeedlyError(code, message, status=status, details=details) from exc
        finally:
            self._sdk_logger.disabled = prior_disabled

    def close(self) -> None:
        close = getattr(self.session, "close", None)
        if callable(close):
            close()


def _response_details(response: Any) -> Any:
    if response is None:
        return None
    try:
        return response.json()
    except ValueError:
        body = getattr(response, "text", "")
        return {"body": body[:1000]} if body else None


def _error_message(details: Any) -> str | None:
    if isinstance(details, dict):
        for key in ("errorMessage", "message", "error"):
            value = details.get(key)
            if isinstance(value, str) and value:
                return value[:1000]
    return None


def _error_kind(status: int | None) -> tuple[str, str]:
    if status == 400:
        return "bad_request", "Feedly rejected the request."
    if status == 401:
        return "authentication_error", "Feedly rejected the API token."
    if status == 403:
        return "permission_denied", "The API token does not have permission for this operation."
    if status == 404:
        return "not_found", "Feedly could not find the requested resource."
    if status == 429:
        return "rate_limited", "Feedly API rate limit exceeded."
    if status is not None and status >= 500:
        return "server_error", "Feedly API server error."
    return "api_error", "Feedly API request failed."


def _redact(value: Any, secret: str | None) -> Any:
    if not secret:
        return value
    if isinstance(value, str):
        return value.replace(secret, "[redacted]")
    if isinstance(value, list):
        return [_redact(item, secret) for item in value]
    if isinstance(value, dict):
        return {key: _redact(item, secret) for key, item in value.items()}
    return value
