"""Article streams such as feeds, folders, and boards."""

from __future__ import annotations

from typing import Any

from .transport import APITransport


class StreamAPI:
    def __init__(self, transport: APITransport) -> None:
        self.transport = transport

    def contents(
        self,
        stream_id: str,
        count: int = 20,
        continuation: str | None = None,
        unread_only: bool = False,
    ) -> Any:
        params: dict[str, Any] = {"streamID": stream_id, "count": count}
        if continuation is not None:
            params["continuation"] = continuation
        if unread_only:
            params["unreadOnly"] = "true"
        return self.transport.request("/v3/streams/contents", params=params)
