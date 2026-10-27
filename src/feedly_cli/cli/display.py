"""Output mode selection shared by command handlers and the app."""

from __future__ import annotations

import argparse
from typing import Any

from .. import output
from .errors import write_json


class StreamedOutput:
    """Signal that a handler already emitted one or more output records."""

    def __init__(self, exit_code: int = 0) -> None:
        self.exit_code = exit_code


def display(value: Any, args: argparse.Namespace) -> None:
    if args.json:
        if args.brief:
            write_json(output.brief(value))
        else:
            write_json(output.add_markdown(value) if args.markdown else value)
    elif args.markdown:
        output.write_markdown(value, include_content=not args.brief)
    else:
        action = next(
            (
                getattr(args, key)
                for key in (
                    "articles_command",
                    "boards_command",
                    "folders_command",
                    "feeds_command",
                    "cves_command",
                )
                if hasattr(args, key)
            ),
            None,
        )
        output.render(value, command=args.command, action=action, context=vars(args))
