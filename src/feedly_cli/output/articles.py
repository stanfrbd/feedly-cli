"""Articles presentation helpers for Feedly responses."""

from __future__ import annotations

import sys
from typing import Any

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .article_data import article_url, board_labels, source_name
from .common import (
    clean_line,
    clean_text,
    create_console,
    format_date,
    literal,
    pick,
    render_detail,
)
from .markdown import article_markdown


def render_articles(
    items: list[dict[str, Any]], stream: Any = None, *, include_body: bool = False
) -> None:
    console = create_console(stream)
    table = Table(title="Articles", show_lines=True, expand=True, box=None)
    for title in ("#", "Date", "Title", "Source", "Boards / tags"):
        table.add_column(title, overflow="fold", no_wrap=False)
    for index, item in enumerate(items, start=1):
        table.add_row(
            literal(index),
            literal(format_date(pick(item, "published", "publishedDate", "crawled", "updated"))),
            literal(pick(item, "title", "headline") or "Untitled"),
            literal(source_name(item)),
            literal(board_labels(item)),
        )
    if console.width >= 72:
        console.print(table)
    else:
        for index, item in enumerate(items, start=1):
            render_detail(
                f"Article {index}",
                {
                    "Title": pick(item, "title", "headline") or "Untitled",
                    "Date": format_date(pick(item, "published", "publishedDate", "crawled")),
                    "Source": source_name(item),
                    "Boards": board_labels(item),
                },
                stream,
            )
    target = stream if stream is not None else sys.stdout
    for index, item in enumerate(items, start=1):
        url = article_url(item)
        entry_id = pick(item, "id", "entryId")
        if url:
            target.write(f"Article {index} URL: {clean_line(url)}\n")
        if entry_id:
            target.write(f"Article {index} Entry ID: {clean_line(entry_id)}\n")
        if include_body:
            body, fmt = article_markdown(item)
            if body:
                title = pick(item, "title", "headline") or f"Article {index}"
                console.print(
                    Panel(
                        literal(body),
                        title=literal(f"Content: {clean_text(title)} ({fmt})"),
                        expand=True,
                    )
                )


def render_article_summary(value: Any, items: list[dict[str, Any]], stream: Any = None) -> None:
    if not isinstance(value, dict):
        return
    summary: list[str] = [f"Results: {len(items)}"]
    pages = value.get("pages")
    if pages is not None:
        summary.append(f"Pages: {clean_text(pages)}")
    continuation = value.get("continuation")
    if continuation:
        summary.append("More results are available.")
    console = create_console(stream)
    console.print(literal("  |  ".join(summary)))
    if continuation:
        console.print(Text.assemble(("Continuation: ", "bold"), literal(continuation)))
        console.print(literal("Use this value with --continuation to fetch the next page."))
