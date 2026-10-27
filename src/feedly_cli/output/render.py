"""Render presentation helpers for Feedly responses."""

from __future__ import annotations

import sys
from typing import Any

from rich.text import Text

from .article_data import article_items
from .articles import render_article_summary, render_articles
from .common import clean_text, create_console, literal, render_detail
from .discovery import listing_items, render_listing, render_mutation
from .vulnerabilities import render_cve_details, render_vulnerabilities


def render(
    value: Any,
    *,
    command: str,
    action: str | None = None,
    context: dict[str, Any] | None = None,
    stream: Any = None,
) -> None:
    """Render a Feedly JSON response for a human in a terminal."""
    context = context or {}
    if action in {"add-url", "add-entry"} and render_mutation(value, context, action, stream):
        return
    if command.lower() == "profile" and isinstance(value, dict):
        render_detail("Profile", value, stream)
        return
    items = article_items(value)
    lowered = command.lower()
    if lowered in {"boards", "folders", "feeds"} and action == "list":
        render_listing(listing_items(value, lowered), lowered, stream)
        return
    if "cve" in lowered:
        if isinstance(value, dict) and "cveid" in value:
            render_cve_details([value], stream)
            return
        if items and all("cveid" in item for item in items):
            render_cve_details(items, stream)
            return
        if isinstance(value, dict) and isinstance(value.get("memes"), list):
            render_vulnerabilities(
                [item for item in value["memes"] if isinstance(item, dict)], stream
            )
            return
        if isinstance(value, dict) and not any(
            isinstance(value.get(key), list) for key in ("items", "results", "entries", "memes")
        ):
            render_detail("Vulnerability", value, stream)
            return
        if items:
            render_vulnerabilities(items, stream)
            return
    if items and (
        lowered not in {"folders", "feeds", "boards"}
        or (lowered == "boards" and action in {"read", "watch"})
    ):
        render_articles(
            items,
            stream,
            include_body=(lowered == "articles" and action == "get"),
            details=bool(context.get("details")),
        )
        render_article_summary(value, items, stream)
        return
    if (
        isinstance(value, list)
        and not value
        and (
            lowered in {"articles", "boards", "search", "streams", "cve", "cves"}
            or action in {"read", "watch", "get", "search"}
        )
    ):
        create_console(stream).print(literal("No articles found."))
        return
    if isinstance(value, dict):
        render_detail(command.replace("_", " ").title(), value, stream)
        return
    if isinstance(value, list):
        render_listing(items, command, stream)
        return
    create_console(stream).print(literal(value))


def render_error(code: str, message: str, stream: Any = None) -> None:
    """Render a readable literal error without interpreting terminal markup."""
    console = create_console(stream if stream is not None else sys.stderr)
    console.print(Text.assemble((f"Error [{clean_text(code)}]: ", "bold"), literal(message)))
