"""Article listings; every article shows its entry ID, ``--details`` adds the rest."""

from __future__ import annotations

import sys
from typing import Any

from .article_details import render_article_details
from .common import clean_line, create_console, literal


def render_articles(
    items: list[dict[str, Any]],
    stream: Any = None,
    *,
    include_body: bool = False,
    details: bool = False,
) -> None:
    render_article_details(
        items,
        stream,
        full=details or include_body,
        include_body=include_body,
    )


def render_article_summary(value: Any, items: list[dict[str, Any]], stream: Any = None) -> None:
    console = create_console(stream)
    summary = f"Results: {len(items)}"
    if isinstance(value, dict) and value.get("pages") is not None:
        summary += f" | Pages: {clean_line(value['pages'])}"
    console.print(literal(summary))
    if isinstance(value, dict) and value.get("continuation"):
        target = stream if stream is not None else sys.stdout
        target.write(f"More results: --continuation {clean_line(value['continuation'])}\n")
