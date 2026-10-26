"""Construct the argparse tree from independently registered command groups."""

from __future__ import annotations

import argparse
from typing import Any

from .. import __version__
from ..commands import articles, boards, discovery, search, vulnerabilities
from .errors import UsageError


class Parser(argparse.ArgumentParser):
    """Expose output flags at every level and convert parse errors to CLI errors."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.add_argument(
            "--json",
            action="store_true",
            default=argparse.SUPPRESS,
            help="write machine-readable JSON (JSON Lines for board watch)",
        )
        self.add_argument(
            "--markdown",
            action="store_true",
            default=argparse.SUPPRESS,
            help="convert article content to Markdown; combine with --json to add contentMarkdown",
        )

    def error(self, message: str) -> None:
        raise UsageError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(
        prog="feedly",
        description="Read Feedly articles, boards and CVE intelligence. Use --json for automation.",
    )
    parser.add_argument("--version", action="version", version=f"feedly-cli {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, parser_class=Parser)
    discovery.register(commands)
    articles.register(commands)
    boards.register(commands)
    search.register(commands)
    vulnerabilities.register(commands)
    return parser
