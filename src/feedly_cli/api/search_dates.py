"""UTC publication-date bounds for article search."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from feedly_cli.errors import FeedlyError


def parse_search_date(value: str) -> int:
    """Accept a calendar date or timezone-aware ISO timestamp; return epoch milliseconds."""
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            parsed = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", value):
                raise ValueError
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ValueError
        if parsed.microsecond % 1000:
            raise ValueError
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        delta = parsed.astimezone(timezone.utc) - epoch
        return (delta.days * 86400 + delta.seconds) * 1000 + delta.microseconds // 1000
    except (ValueError, OverflowError) as exc:
        raise FeedlyError(
            "bad_request",
            "Search dates must be YYYY-MM-DD (UTC midnight) or ISO 8601 timestamps "
            "with a timezone and at most millisecond precision.",
        ) from exc


def validate_search_dates(since: int | None, before: int | None) -> None:
    if since is not None and before is not None and since >= before:
        raise FeedlyError("bad_request", "--since must be earlier than --before.")


def filter_search_dates(page: Any, since: int | None, before: int | None) -> dict[str, Any]:
    """Apply inclusive/exclusive bounds to Feedly's published epoch milliseconds."""
    if not isinstance(page, dict) or not isinstance(page.get("items"), list):
        raise FeedlyError("api_error", "Feedly search returned an invalid page envelope.")
    items = []
    for item in page["items"]:
        published = item.get("published") if isinstance(item, dict) else None
        if isinstance(published, bool) or not isinstance(published, int):
            raise FeedlyError(
                "api_error",
                "Cannot apply search dates: an article has no valid published "
                "epoch-millisecond timestamp. Use an unfiltered search to inspect it.",
            )
        if (since is None or published >= since) and (before is None or published < before):
            items.append(item)
    return {**page, "items": items}
