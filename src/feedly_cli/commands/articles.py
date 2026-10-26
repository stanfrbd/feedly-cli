"""Article retrieval and stream-reading commands."""

from __future__ import annotations

import argparse
from typing import Any

from ..cli.arguments import positive_int
from ..client import FeedlyClient


def _get_article(args: argparse.Namespace, client: FeedlyClient) -> Any:
    return client.entry(args.id)


def _read_stream(args: argparse.Namespace, client: FeedlyClient) -> Any:
    return client.stream_contents(
        args.id,
        count=args.count,
        continuation=args.continuation,
        unread_only=args.unread_only,
    )


def register(commands: argparse._SubParsersAction) -> None:
    articles = commands.add_parser("articles", help="retrieve a Feedly article")
    article_actions = articles.add_subparsers(
        dest="articles_command", required=True, parser_class=type(articles)
    )
    article_get = article_actions.add_parser("get", help="retrieve an article by ID")
    article_get.add_argument("id", help="Feedly article ID")
    article_get.set_defaults(handler=_get_article, supports_markdown=True)

    streams = commands.add_parser("streams", help="read a Feedly stream")
    stream_actions = streams.add_subparsers(
        dest="streams_command", required=True, parser_class=type(streams)
    )
    stream_read = stream_actions.add_parser("read", help="read entries from a stream ID")
    stream_read.add_argument("id", help="Feedly stream ID")
    stream_read.add_argument(
        "--count", type=positive_int, default=20, help="maximum entries (default: 20)"
    )
    stream_read.add_argument("--continuation", help="continuation token from a prior response")
    stream_read.add_argument(
        "--unread-only", action="store_true", help="return unread entries only"
    )
    stream_read.set_defaults(handler=_read_stream, supports_markdown=True)
