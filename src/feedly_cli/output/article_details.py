"""Keep each article's human-readable metadata together."""

from __future__ import annotations

import sys
from typing import Any

from rich.text import Text

from .article_data import article_url, board_labels, source_name
from .common import clean_line, create_console, format_date, literal, pick
from .markdown import article_markdown
from .threat import describe_cve, describe_ioc, threat_intel


def _threat_fields(item: dict[str, Any], *, full: bool) -> dict[str, str]:
    intel = threat_intel(item)
    fields = {
        "CVEs": ", ".join(describe_cve(cve) for cve in intel["cves"]),
        "Indicators": describe_ioc(item),
    }
    if not full:
        return fields
    fields.update(
        {
            "Malware": ", ".join(intel["malware"]),
            "Threat actors": ", ".join(intel["threatActors"]),
            "ATT&CK": ", ".join(intel["techniques"]),
            "Summary": intel["summary"],
        }
    )
    return fields


def render_article_details(
    items: list[dict[str, Any]],
    stream: Any = None,
    *,
    full: bool = False,
    include_body: bool = False,
) -> None:
    """Write copyable IDs, publisher URLs and Feedly IoC status for every article."""
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
            "Entry ID": pick(item, "id", "entryId") or "Unavailable (not provided by Feedly)",
            "URL": article_url(item) or "Unavailable (not provided by Feedly)",
        }
        if full:
            fields.update({"Boards / tags": board_labels(item)})
        fields.update(_threat_fields(item, full=full))
        for label, value in fields.items():
            if value:
                target.write(f"  {label}: {clean_line(value)}\n")
        if include_body:
            body, content_format = article_markdown(item)
            body = body or "No Feedly content available."
            target.write(f"  Content: {content_format}\n\n{body}\n")
