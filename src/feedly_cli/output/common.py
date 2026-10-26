"""Common presentation helpers for Feedly responses."""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

_ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")


def clean_text(value: Any) -> str:
    """Turn untrusted values into literal, control-free terminal text."""
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        raw = json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    else:
        raw = str(value)
    raw = _ANSI.sub("", raw)
    return "".join(
        char
        for char in raw
        if unicodedata.category(char) not in {"Cc", "Cf"} or char in "\n\t\u200d"
    )


def clean_line(value: Any) -> str:
    return " ".join(clean_text(value).split())


def pick(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def format_date(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        if isinstance(value, (int, float)):
            timestamp = value / 1000 if value > 100_000_000_000 else value
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        text = str(value)
        # Feedly dates are commonly epoch milliseconds or ISO strings.
        if text.isdigit():
            number = int(text)
            timestamp = number / 1000 if number > 100_000_000_000 else number
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (OverflowError, OSError, ValueError):
        return str(value)


def create_console(stream: Any = None) -> Console:
    return Console(
        file=stream or sys.stdout,
        force_terminal=False,
        color_system=None,
        no_color=True,
        highlight=False,
    )


def literal(value: Any) -> Text:
    return Text(clean_text(value), no_wrap=False, overflow="fold")


def render_detail(title: str, value: dict[str, Any], stream: Any = None) -> None:
    lines = []
    for key, item in value.items():
        if key.startswith("_") or key in {"items", "results", "entries"}:
            continue
        if isinstance(item, dict):
            text = pick(item, "content", "title", "name", "label", "href", "url")
            if text is None:
                text = json.dumps(item, ensure_ascii=True, separators=(",", ":"))
        elif isinstance(item, list):
            text = ", ".join(
                clean_text(pick(child, "label", "name", "id") if isinstance(child, dict) else child)
                for child in item
            )
        else:
            text = item
        lines.append((key.replace("_", " ").title(), clean_text(text)))
    table = Table.grid(padding=(0, 1))
    table.add_column(style="bold", no_wrap=False)
    table.add_column(overflow="fold", no_wrap=False)
    for key, val in lines:
        table.add_row(literal(key), literal(val))
    create_console(stream).print(Panel(table, title=literal(title), expand=True))
