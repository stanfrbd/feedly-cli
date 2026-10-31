"""Board listing, reading, watching, and update commands."""

from __future__ import annotations

import argparse
import time
from typing import Any

from ..cli.arguments import http_url, nonnegative_int, positive_float, positive_int
from ..cli.display import StreamedOutput, display
from ..client import FeedlyClient


def _list_boards(args: argparse.Namespace, client: FeedlyClient) -> Any:
    del args
    return client.boards()


def _read_board(args: argparse.Namespace, client: FeedlyClient) -> Any:
    return client.board_stream(args.id, count=args.count, continuation=args.continuation)


def _add_url(args: argparse.Namespace, client: FeedlyClient) -> Any:
    return client.add_url_to_board(
        args.id,
        args.url,
        dry_run=args.dry_run,
        stream_id=args.source_stream,
        max_pages=args.max_pages,
        count=args.count,
    )


def _add_entry(args: argparse.Namespace, client: FeedlyClient) -> Any:
    return client.add_entry_to_board(args.id, args.entry_id)


def _watch(args: argparse.Namespace, client: FeedlyClient) -> StreamedOutput:
    """Poll and display board updates as one JSON value per poll when requested."""
    completed = 0
    seen: set[str] = set()
    try:
        while args.iterations == 0 or completed < args.iterations:
            result = client.board_watch(args.id, count=args.count, max_pages=args.max_pages)
            if isinstance(result, dict) and isinstance(result.get("items"), list):
                fresh = []
                for item in result["items"]:
                    key = item.get("id") if isinstance(item, dict) else None
                    if key is None or key not in seen:
                        fresh.append(item)
                        if key is not None:
                            seen.add(key)
                result = dict(result)
                result["items"] = fresh
            display(result, args)
            completed += 1
            if args.iterations == 0 or completed < args.iterations:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        return StreamedOutput()
    return StreamedOutput()


def register(commands: argparse._SubParsersAction) -> None:
    boards = commands.add_parser("boards", help="list, read, watch or update boards")
    actions = boards.add_subparsers(dest="boards_command", required=True, parser_class=type(boards))
    board_list = actions.add_parser("list", help="list boards")
    board_list.set_defaults(handler=_list_boards)

    board_read = actions.add_parser("read", help="read entries in a board")
    board_read.add_argument("id", help="board ID")
    board_read.add_argument(
        "--count", type=positive_int, default=20, help="maximum entries (default: 20)"
    )
    board_read.add_argument("--continuation", help="continuation token from a prior response")
    board_read.set_defaults(handler=_read_board, supports_markdown=True)

    board_watch = actions.add_parser("watch", help="poll a board for new articles")
    board_watch.add_argument("id", help="board ID")
    board_watch.add_argument(
        "--interval", type=positive_float, default=60.0, help="seconds between polls (default: 60)"
    )
    board_watch.add_argument(
        "--iterations", type=nonnegative_int, default=0, help="poll count; 0 runs until interrupted"
    )
    board_watch.add_argument(
        "--count", type=positive_int, default=100, help="entries per page (default: 100)"
    )
    board_watch.add_argument(
        "--max-pages", type=positive_int, default=10, help="maximum pages per poll (default: 10)"
    )
    board_watch.set_defaults(handler=_watch, supports_markdown=True)

    board_add = actions.add_parser("add-url", help="add a URL to a board")
    board_add.add_argument("id", help="board ID")
    board_add.add_argument("url", type=http_url, help="article URL to add")
    board_add.add_argument(
        "--source-stream",
        "--stream-id",
        dest="source_stream",
        help="stream to search when resolving the URL",
    )
    board_add.add_argument(
        "--max-pages",
        type=positive_int,
        default=10,
        help="maximum source pages to scan (default: 10)",
    )
    board_add.add_argument(
        "--count", type=positive_int, default=100, help="entries per source page (default: 100)"
    )
    board_add.add_argument(
        "--dry-run", action="store_true", help="resolve the article without adding it"
    )
    board_add.set_defaults(handler=_add_url)

    board_entry = actions.add_parser("add-entry", help="add an existing Feedly entry to a board")
    board_entry.add_argument("id", help="board ID")
    board_entry.add_argument("entry_id", help="Feedly article ID")
    board_entry.set_defaults(handler=_add_entry)
