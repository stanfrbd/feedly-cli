"""Feedly content search and continuation handling."""

from __future__ import annotations

from typing import Any

from feedly_cli.errors import FeedlyError

from .articles import ArticleAPI
from .discovery import DiscoveryAPI
from .search_dates import filter_search_dates, validate_search_dates
from .transport import APITransport


class SearchAPI:
    def __init__(
        self,
        transport: APITransport,
        articles: ArticleAPI,
        discovery: DiscoveryAPI,
    ) -> None:
        self.transport = transport
        self.articles = articles
        self.discovery = discovery

    def search(
        self,
        query: str | dict[str, Any],
        count: int = 20,
        continuation: str | None = None,
        *,
        stream_id: str | None = None,
        salience: str = "mention",
        since: int | None = None,
        before: int | None = None,
    ) -> Any:
        validate_search_dates(since, before)
        params: dict[str, Any] = {"count": count}
        if continuation is not None:
            params["continuation"] = continuation
        if isinstance(query, dict):
            body = query
        else:
            body = {
                "layers": [
                    {
                        "type": "matches",
                        "salience": salience,
                        "parts": [{"type": "customKeyword", "text": query}],
                    }
                ]
            }
            source_stream = stream_id or self.discovery.default_enterprise_stream()
            if source_stream:
                body["source"] = {"items": [{"type": "stream", "id": source_stream}]}
        result = self.transport.request(
            "/v3/search/contents", method="post", params=params, data=body
        )
        if since is not None or before is not None:
            return filter_search_dates(result, since, before)
        return result

    def search_all(
        self,
        query: str | dict[str, Any],
        count: int = 100,
        max_pages: int = 100,
        stream_id: str | None = None,
        fetch: bool = False,
        salience: str = "mention",
        *,
        since: int | None = None,
        before: int | None = None,
    ) -> Any:
        validate_search_dates(since, before)
        if not 1 <= count <= 100:
            raise FeedlyError("bad_request", "Search count must be between 1 and 100.")
        if not 1 <= max_pages <= 100:
            raise FeedlyError("bad_request", "Search max_pages must be between 1 and 100.")
        continuation = None
        seen_continuations: set[str] = set()
        seen_ids: set[str] = set()
        items: list[Any] = []
        envelope: dict[str, Any] | None = None
        pages = 0
        while True:
            page = self.search(
                query,
                count=count,
                continuation=continuation,
                stream_id=stream_id,
                salience=salience,
                since=since,
                before=before,
            )
            pages += 1
            if not isinstance(page, dict):
                raise FeedlyError("api_error", "Feedly search returned an invalid page envelope.")
            if envelope is None:
                envelope = dict(page)
            for item in page.get("items", []):
                if not isinstance(item, dict) or not item.get("id"):
                    items.append(item)
                    continue
                item_id = item["id"]
                if item_id not in seen_ids:
                    seen_ids.add(item_id)
                    items.append(item)
            next_continuation = page.get("continuation")
            if not next_continuation:
                break
            if next_continuation in seen_continuations:
                raise FeedlyError(
                    "api_error",
                    "Feedly repeated a search continuation token; refusing to loop indefinitely.",
                    details={"pages": pages},
                )
            if pages >= max_pages:
                raise FeedlyError(
                    "api_error",
                    "Search reached max_pages while more results remain.",
                    details={"pages": pages, "continuation": next_continuation},
                )
            seen_continuations.add(next_continuation)
            continuation = next_continuation
        if envelope is None:
            envelope = {}
        envelope["items"] = self.articles.hydrate_items(items) if fetch else items
        envelope.pop("continuation", None)
        envelope["pages"] = pages
        return envelope
