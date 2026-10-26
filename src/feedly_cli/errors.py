"""Typed errors raised by the Feedly API client."""

from __future__ import annotations

from typing import Any, ClassVar


class FeedlyError(Exception):
    """Normalized Feedly API, transport, or configuration error."""

    _EXIT_CODES: ClassVar[dict[str, int]] = {
        "configuration_error": 2,
        "bad_request": 2,
        "authentication_error": 3,
        "permission_denied": 3,
        "not_found": 4,
        "rate_limited": 5,
        "server_error": 6,
        "api_error": 6,
        "network_error": 6,
    }

    def __init__(
        self,
        code: str,
        message: str,
        status: int | None = None,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details

    @property
    def exit_code(self) -> int:
        return self._EXIT_CODES.get(self.code, 1)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe error object, omitting unavailable fields."""
        result: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.status is not None:
            result["status"] = self.status
        if self.details is not None:
            result["details"] = self.details
        return result
