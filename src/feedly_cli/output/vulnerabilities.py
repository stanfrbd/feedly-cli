"""Vulnerabilities presentation helpers for Feedly responses."""

from __future__ import annotations

from typing import Any

from rich.table import Table

from .common import create_console, format_date, literal, pick


def render_vulnerabilities(items: list[dict[str, Any]], stream: Any = None) -> None:
    table = Table(title="Vulnerabilities", show_lines=True, expand=True, box=None)
    for title in ("CVE", "Score / severity", "Published", "Title"):
        table.add_column(title, overflow="fold", no_wrap=False)
    for item in items:
        metadata = item.get("vulnerabilitiesMetadata")
        if not isinstance(metadata, dict):
            metadata = {}
        published = pick(item, "published", "publishedDate", "created") or pick(
            metadata, "publishedDate", "published"
        )
        table.add_row(
            literal(pick(item, "cve", "cveId", "label", "name", "id")),
            literal(
                pick(item, "severity", "cvssSeverity", "risk")
                or pick(item, "cvss", "score")
                or pick(metadata, "cvss", "severity", "cvssSeverity")
            ),
            literal(format_date(published)),
            literal(pick(item, "title", "summary", "description")),
        )
    create_console(stream).print(table)
