"""Read-only, bounded exact publisher-URL lookup in an indexed stream."""

from __future__ import annotations

import ipaddress
import re
import unicodedata
from typing import Any
from urllib.parse import urlsplit

from feedly_cli.errors import FeedlyError

from .streams import StreamAPI


def validate_url(url: str) -> None:
    """Validate an absolute HTTP(S) URI/IRI without changing its exact spelling."""
    message = (
        "Provide an absolute HTTP(S) URL with a valid host, port and percent escapes, "
        "without credentials, whitespace or control characters."
    )
    try:
        if (
            not isinstance(url, str)
            or not url
            or any(
                char.isspace()
                or unicodedata.category(char) in {"Cc", "Cf", "Cs"}
                or char in '\\<>"{}|^`'
                for char in url
            )
            or re.search(r"%(?![0-9A-Fa-f]{2})", url)
        ):
            raise ValueError
        parsed = urlsplit(url)
        host = parsed.hostname
        if parsed.scheme.lower() not in {"http", "https"} or not host or "@" in parsed.netloc:
            raise ValueError
        if "%" in host or parsed.netloc.endswith(":"):
            raise ValueError
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError
        if ":" in host:
            ipaddress.IPv6Address(host)
            suffix = parsed.netloc[parsed.netloc.index("]") + 1 :]
            if suffix and not re.fullmatch(r":[0-9]+", suffix):
                raise ValueError
        else:
            ascii_host = host.encode("idna").decode("ascii").rstrip(".")
            if (
                not ascii_host
                or len(ascii_host) > 253
                or any(
                    not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
                    for label in ascii_host.split(".")
                )
            ):
                raise ValueError
            if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+", ascii_host):
                ipaddress.IPv4Address(ascii_host)
        if any(char in parsed.path + parsed.query + parsed.fragment for char in "[]"):
            raise ValueError
    except (ValueError, UnicodeError) as exc:
        raise FeedlyError("bad_request", message) from exc


def resolve_url(
    streams: StreamAPI,
    stream_id: str,
    url: str,
    *,
    count: int = 100,
    max_pages: int = 10,
    continuation: str | None = None,
) -> dict[str, Any]:
    validate_url(url)
    if any(
        isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 100
        for value in (count, max_pages)
    ):
        raise FeedlyError(
            "bad_request", "URL scan count and max_pages must each be between 1 and 100."
        )
    if continuation is not None and (not isinstance(continuation, str) or not continuation.strip()):
        raise FeedlyError("bad_request", "A continuation must be a nonempty opaque string.")
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
        matching_ids: set[str] = set()
        for item in page["items"]:
            entry_id = item.get("id")
            if (
                not isinstance(entry_id, str)
                or not entry_id
                or any(
                    char.isspace() or unicodedata.category(char) in {"Cc", "Cf", "Cs"}
                    for char in entry_id
                )
            ):
                raise FeedlyError("api_error", "A URL scan article has no valid Feedly entry ID.")
            if entry_matches_url(item, url):
                matching_ids.add(entry_id)
        if len(matching_ids) > 1:
            raise FeedlyError(
                "api_error",
                "Multiple Feedly entry IDs match the exact URL on this page; "
                "resolution is ambiguous. Select a narrower source stream.",
                details={"pagesScanned": pages_scanned, "matchingEntries": len(matching_ids)},
            )
        if matching_ids:
            return {
                "entryId": next(iter(matching_ids)),
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
