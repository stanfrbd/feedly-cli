"""Article data presentation helpers for Feedly responses."""

from __future__ import annotations

from typing import Any

from .common import clean_text, pick


def articles_from_response(value: Any) -> tuple[list[dict[str, Any]], str | None]:
    """Find article dicts in a raw response while retaining the wrapper key."""
    if isinstance(value, list):
        if all(isinstance(item, dict) for item in value):
            return value, None
        return [], None
    if not isinstance(value, dict):
        return [], None
    for key in ("items", "entries", "results"):
        items = value.get(key)
        if isinstance(items, list) and all(isinstance(item, dict) for item in items):
            return items, key
    if any(key in value for key in ("id", "title", "content", "summary", "fullContent")):
        return [value], None
    return [], None


def article_items(value: Any) -> list[dict[str, Any]]:
    items, _ = articles_from_response(value)
    return items


def source_name(item: dict[str, Any]) -> Any:
    origin = item.get("origin")
    if isinstance(origin, dict):
        return pick(origin, "title", "label", "streamId", "htmlUrl")
    source = item.get("source")
    if isinstance(source, dict):
        return pick(source, "title", "name", "label", "id")
    return source or item.get("originId")


def board_labels(item: dict[str, Any]) -> str:
    tags = item.get("tags") or item.get("boards") or []
    if isinstance(tags, str):
        return tags
    if not isinstance(tags, list):
        return clean_text(tags)
    values = []
    for tag in tags:
        if isinstance(tag, dict):
            values.append(pick(tag, "label", "name", "id") or "")
        else:
            values.append(tag)
    return ", ".join(clean_text(value) for value in values if value not in (None, ""))


def article_url(item: dict[str, Any]) -> Any:
    url = pick(item, "canonicalUrl", "url", "alternateUrl", "originalUrl")
    if url:
        return url
    alternate = item.get("alternate")
    if isinstance(alternate, list):
        for candidate in alternate:
            if isinstance(candidate, dict) and candidate.get("href"):
                return candidate["href"]
    if isinstance(alternate, dict):
        return alternate.get("href")
    return None
