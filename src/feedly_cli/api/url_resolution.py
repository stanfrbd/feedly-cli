"""Read-only, bounded exact publisher-URL lookup in an indexed stream."""

from __future__ import annotations

from typing import Any

from feedly_cli.errors import FeedlyError

from .streams import StreamAPI


def resolve_url(
    streams: StreamAPI,
    stream_id: str,
    url: str,
    *,
    count: int = 100,
    max_pages: int = 10,
    continuation: str | None = None,
) -> dict[str, Any]:
    if not 1 <= count <= 100 or not 1 <= max_pages <= 100:
        raise FeedlyError(
            "bad_request", "URL scan count and max_pages must each be between 1 and 100."
        )
    seen: set[str] = {continuation} if continuation else set()
    for pages_scanned in range(1, max_pages + 1):
        page = streams.contents(stream_id, count=count, continuation=continuation)
        if (
            not isinstance(page, dict)
            or not isinstance(page.get("items"), list)
            or any(not isinstance(item, dict) for item in page["items"])
            or (page.get("continuation") is not None and not isinstance(page["continuation"], str))
        ):
            raise FeedlyError("api_error", "Feedly returned an invalid URL scan page.")
        for item in page["items"]:
            if entry_matches_url(item, url):
                entry_id = item.get("id")
                if not isinstance(entry_id, str) or not entry_id:
                    raise FeedlyError(
                        "api_error", "An exact URL match has no valid Feedly entry ID."
                    )
                return {
                    "entryId": entry_id,
                    "url": url,
                    "streamId": stream_id,
                    "pagesScanned": pages_scanned,
                }
        continuation = page.get("continuation")
        details = {"url": url, "streamId": stream_id, "pagesScanned": pages_scanned}
        if not continuation:
            raise FeedlyError(
                "not_found",
                "No exact URL match was found before the selected Feedly stream was exhausted. "
                "This does not establish global absence from Feedly.",
                status=404,
                details=details,
            )
        details["continuation"] = continuation
        if continuation in seen:
            raise FeedlyError(
                "api_error", "Feedly repeated a URL scan continuation token.", details=details
            )
        seen.add(continuation)
    raise FeedlyError(
        "api_error",
        "URL scan reached max_pages while more entries remain; resolution is incomplete. "
        "Resume with --continuation and the same source stream and URL.",
        details=details,
    )


def entry_matches_url(item: dict[str, Any], url: str) -> bool:
    candidates = [item.get("canonicalUrl"), item.get("url")]
    alternates = item.get("alternate")
    if isinstance(alternates, dict):
        candidates.append(alternates.get("href"))
    elif isinstance(alternates, list):
        candidates.extend(value.get("href") for value in alternates if isinstance(value, dict))
    return url in candidates
