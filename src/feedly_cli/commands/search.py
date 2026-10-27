"""Feedly content-search commands."""

from __future__ import annotations

import argparse
from typing import Any

from ..cli.arguments import bounded_positive_int, read_query_file
from ..cli.errors import InputError
from ..client import FeedlyClient


def _validate(args: argparse.Namespace) -> None:
    if args.all and args.continuation:
        raise InputError("--continuation cannot be used with --all")
    if args.query_file and args.stream_id:
        raise InputError(
            "--stream-id cannot be used with --query-file; include the source in the JSON body"
        )
    if args.query_file and args.salience != "mention":
        raise InputError("--salience cannot be used with --query-file; set it in the JSON body")
    if args.query_file:
        args.query_payload = read_query_file(args.query_file)


def _search(args: argparse.Namespace, client: FeedlyClient) -> Any:
    query = args.query_payload if args.query_file else args.query
    if args.all:
        return client.search_all(
            query,
            count=args.count,
            max_pages=args.max_pages,
            stream_id=args.stream_id,
            fetch=args.fetch,
            salience=args.salience,
        )
    result = client.search(
        query,
        count=args.count,
        continuation=args.continuation,
        stream_id=args.stream_id,
        salience=args.salience,
    )
    return client.fetch_search_result(result) if args.fetch else result


def register(commands: argparse._SubParsersAction) -> None:
    search = commands.add_parser("search", help="search Feedly")
    search_input = search.add_mutually_exclusive_group(required=True)
    search_input.add_argument("query", nargs="?", help="search query")
    search_input.add_argument(
        "--query-file", help="JSON request body file, or - to read JSON from stdin"
    )
    search.add_argument(
        "--count",
        type=bounded_positive_int(100),
        default=100,
        help="results per page, up to 100 (default: 100)",
    )
    search.add_argument("--continuation", help="continuation token from a prior response")
    search.add_argument("--stream-id", help="source stream for a text query")
    search.add_argument(
        "--salience",
        choices=("mention", "about"),
        default="mention",
        help="'about' keeps only articles centred on the query, dropping passing mentions "
        "(default: mention)",
    )
    search.add_argument("--all", action="store_true", help="fetch every page up to --max-pages")
    search.add_argument(
        "--fetch", action="store_true", help="hydrate results with full Feedly metadata"
    )
    search.add_argument(
        "--max-pages",
        type=bounded_positive_int(100),
        default=100,
        help="page limit for --all, up to 100 (default: 100)",
    )
    search.set_defaults(handler=_search, validate=_validate, supports_markdown=True)
