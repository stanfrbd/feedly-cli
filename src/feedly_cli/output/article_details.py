"""Keep each article's human-readable metadata together."""

from __future__ import annotations

import sys
from typing import Any

from rich.text import Text

from .article_data import article_url, board_labels, source_name
from .common import clean_line, create_console, format_date, literal, pick
from .markdown import article_markdown


def render_article_details(
    items: list[dict[str, Any]],
    stream: Any = None,
    *,
    identifiers: bool = True,
    include_body: bool = False,
) -> None:
    console = create_console(stream)
    target = stream if stream is not None else sys.stdout
    for index, item in enumerate(items, start=1):
        if index > 1:
            target.write("\n")
        title = pick(item, "title", "headline") or "Untitled"
        console.print(Text(f"Article {index}: ", style="bold") + literal(title))
        fields = {
            "Source": source_name(item),
            "Published": format_date(pick(item, "published", "publishedDate", "crawled")),
            "Boards / tags": board_labels(item),
        }
        if identifiers:
            fields.update({"URL": article_url(item), "Entry ID": pick(item, "id", "entryId")})
        for label, value in fields.items():
            if value:
                target.write(f"  {label}: {clean_line(value)}\n")
        if include_body:
            body, content_format = article_markdown(item)
            body = body or "No Feedly content available."
            target.write(f"  Content: {content_format}\n\n{body}\n")
