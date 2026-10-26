"""Compact article listings with an optional complete detail view."""

from __future__ import annotations

import sys
from typing import Any

from rich.table import Table
from rich.text import Text

from .article_data import source_name
from .article_details import render_article_details
from .common import clean_line, create_console, format_date, literal, pick


def render_articles(
    items: list[dict[str, Any]],
    stream: Any = None,
    *,
    include_body: bool = False,
    details: bool = False,
) -> None:
    console = create_console(stream)
    if details or include_body or console.width < 72:
        render_article_details(
            items,
            stream,
            identifiers=details or include_body,
            include_body=include_body,
        )
        return
    table = Table(box=None, padding=(0, 1), pad_edge=False, expand=True)
    table.add_column("#", width=len(str(max(len(items), 1))), no_wrap=True)
    table.add_column("Article", ratio=3, min_width=30, overflow="fold")
    table.add_column("Source", width=min(24, console.width // 5), no_wrap=True, overflow="ellipsis")
    table.add_column("Published", width=10, no_wrap=True)
    for index, item in enumerate(items, start=1):
        published = format_date(pick(item, "published", "publishedDate", "crawled", "updated"))
        table.add_row(
            literal(index),
            literal(pick(item, "title", "headline") or "Untitled"),
            Text(clean_line(source_name(item)), no_wrap=True, overflow="ellipsis"),
            literal(published[:10]),
            end_section=True,
        )
    console.print(table)


def render_article_summary(value: Any, items: list[dict[str, Any]], stream: Any = None) -> None:
    console = create_console(stream)
    summary = f"Results: {len(items)}"
    if isinstance(value, dict) and value.get("pages") is not None:
        summary += f" | Pages: {clean_line(value['pages'])}"
    console.print(literal(summary))
    if isinstance(value, dict) and value.get("continuation"):
        target = stream if stream is not None else sys.stdout
        target.write(f"More results: --continuation {clean_line(value['continuation'])}\n")
