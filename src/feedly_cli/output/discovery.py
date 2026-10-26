"""Discovery presentation helpers for Feedly responses."""

from __future__ import annotations

import sys
from typing import Any

from rich.table import Table

from .article_data import article_items
from .common import clean_line, create_console, literal, pick


def render_listing(items: list[dict[str, Any]], command: str, stream: Any = None) -> None:
    labels = {"boards": "Boards", "folders": "Folders", "feeds": "Feeds"}
    title = labels.get(command, command.title())
    table = Table(title=title, show_lines=True, expand=True, box=None)
    table.add_column("Name", overflow="fold", no_wrap=False)
    table.add_column("Description", overflow="fold", no_wrap=False)
    if command == "feeds":
        table.add_column("Scope", overflow="fold", no_wrap=False)
    for item in items:
        row = [
            literal(pick(item, "label", "name", "title") or ""),
            literal(pick(item, "description", "summary")),
        ]
        if command == "feeds":
            row.append(literal(item.get("scope")))
        table.add_row(*row)
    create_console(stream).print(table)
    target = stream if stream is not None else sys.stdout
    for index, item in enumerate(items, start=1):
        item_id = pick(item, "id", "streamId", "collectionId")
        if item_id:
            target.write(f"{title[:-1]} {index} ID: {clean_line(item_id)}\n")


def listing_items(value: Any, command: str) -> list[dict[str, Any]]:
    if command == "feeds" and isinstance(value, dict):
        combined: list[dict[str, Any]] = []
        for scope, key in (("enterprise", "enterpriseAlerts"), ("user", "userAlerts")):
            items = value.get(key)
            if isinstance(items, list):
                combined.extend(
                    {**item, "scope": scope}
                    if isinstance(item, dict)
                    else {"name": item, "scope": scope}
                    for item in items
                )
        return combined
    return article_items(value)


def render_mutation(value: Any, context: dict[str, Any], action: str, stream: Any = None) -> bool:
    if action not in {"add-url", "add-entry"}:
        return False
    result = value if isinstance(value, dict) else {}
    board_id = (
        context.get("board_id")
        or context.get("boardId")
        or context.get("id")
        or result.get("boardId")
    )
    entry_id = context.get("entry_id") or context.get("entryId") or result.get("entryId")
    url = context.get("url") or result.get("url")
    dry_run = bool(context.get("dry_run") or context.get("dryRun") or result.get("dryRun"))
    if dry_run:
        message = "Resolved article; no board change was made."
    elif action == "add-entry" or board_id or entry_id:
        message = "Added article to board."
    else:
        message = "Board updated."
    console = create_console(stream)
    console.print(literal(message))
    target = stream if stream is not None else sys.stdout
    if board_id is not None:
        target.write(f"Board ID: {clean_line(board_id)}\n")
    if entry_id is not None:
        target.write(f"Entry ID: {clean_line(entry_id)}\n")
    if url is not None:
        target.write(f"URL: {clean_line(url)}\n")
    return True
