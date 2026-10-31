"""Team board operations and bounded article URL resolution."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from feedly_cli.errors import FeedlyError

from .discovery import DiscoveryAPI
from .streams import StreamAPI
from .transport import APITransport
from .url_resolution import resolve_url


class BoardAPI:
    def __init__(
        self,
        transport: APITransport,
        streams: StreamAPI,
        discovery: DiscoveryAPI,
    ) -> None:
        self.transport = transport
        self.streams = streams
        self.discovery = discovery

    def stream(
        self,
        board_id: str,
        count: int = 20,
        continuation: str | None = None,
        unread_only: bool = False,
    ) -> Any:
        return self.streams.contents(board_id, count, continuation, unread_only)

    def add_entry(self, board_id: str, entry_id: str) -> Any:
        return self.transport.request(
            f"/v3/tags/{quote(board_id, safe='')}",
            method="put",
            data={"entryId": entry_id},
        )

    def watch(
        self,
        board_id: str,
        count: int = 100,
        max_pages: int = 10,
        continuation: str | None = None,
    ) -> Any:
        if not 1 <= count <= 100 or not 1 <= max_pages <= 100:
            raise FeedlyError(
                "bad_request", "Board watch count and max_pages must each be between 1 and 100."
            )
        items: list[Any] = []
        next_continuation = continuation
        pages = 0
        response_id: str | None = None
        while pages < max_pages:
            page = self.stream(board_id, count=count, continuation=next_continuation)
            pages += 1
            if not isinstance(page, dict):
                break
            response_id = response_id or page.get("id")
            items.extend(page.get("items", []))
            next_continuation = page.get("continuation")
            if not next_continuation:
                break
        if next_continuation:
            raise FeedlyError(
                "api_error",
                "Board watch reached max_pages while more entries remain.",
                details={"boardId": board_id, "pages": pages, "continuation": next_continuation},
            )
        result: dict[str, Any] = {"items": items, "pages": pages, "continuation": next_continuation}
        if response_id is not None:
            result["id"] = response_id
        return result

    def add_url(
        self,
        board_id: str,
        url: str,
        *,
        dry_run: bool = False,
        stream_id: str | None = None,
        max_pages: int = 10,
        count: int = 100,
    ) -> Any:
        source_stream = (
            stream_id
            or _global_stream_for_board(board_id)
            or self.discovery.default_enterprise_stream()
        )
        if source_stream is None:
            raise FeedlyError(
                "bad_request",
                "Pass an enterprise or personal board ID, or provide stream_id for URL resolution.",
            )
        resolved = resolve_url(self.streams, source_stream, url, count=count, max_pages=max_pages)
        entry_id = resolved["entryId"]
        if dry_run:
            return {"boardId": board_id, "entryId": entry_id, "url": url, "dryRun": True}
        return self.add_entry(board_id, entry_id)


def _global_stream_for_board(board_id: str) -> str | None:
    parts = board_id.split("/")
    if len(parts) >= 4 and parts[0] in {"enterprise", "user"} and parts[2] == "tag":
        return f"{parts[0]}/{parts[1]}/category/global.all"
    return None
