"""Article retrieval and stream-reading commands."""

from __future__ import annotations

import argparse
from typing import Any

from ..cli.arguments import bounded_positive_int, http_url, positive_int
from ..client import FeedlyClient


def _get_article(args: argparse.Namespace, client: FeedlyClient) -> Any:
    return client.entry(args.id)


def _resolve_url(args: argparse.Namespace, client: FeedlyClient) -> Any:
    return client.resolve_article_url(
        args.url,
        stream_id=args.source_stream,
        count=args.count,
        max_pages=args.max_pages,
        continuation=args.continuation,
    )


def _read_stream(args: argparse.Namespace, client: FeedlyClient) -> Any:
    return client.stream_contents(
        args.id,
        count=args.count,
        continuation=args.continuation,
        unread_only=args.unread_only,
    )


def register(commands: argparse._SubParsersAction) -> None:
    articles = commands.add_parser("articles", help="retrieve articles or resolve publisher URLs")
    article_actions = articles.add_subparsers(
        dest="articles_command", required=True, parser_class=type(articles)
    )
    article_get = article_actions.add_parser("get", help="retrieve an article by ID")
    article_get.add_argument("id", help="Feedly article ID")
    article_get.set_defaults(handler=_get_article, supports_markdown=True)
    article_resolve = article_actions.add_parser(
        "resolve-url", help="resolve an indexed publisher URL without changing account data"
    )
    article_resolve.add_argument("url", type=http_url, help="exact publisher URL to resolve")
    article_resolve.add_argument(
        "--source-stream",
        "--stream-id",
        dest="source_stream",
        help="indexed stream to scan (default: enterprise global stream)",
    )
    article_resolve.add_argument(
        "--count",
        type=bounded_positive_int(100),
        default=100,
        help="entries per source page, up to 100 (default: 100)",
    )
    article_resolve.add_argument(
        "--max-pages",
        type=bounded_positive_int(100),
        default=10,
        help="maximum source pages to scan, up to 100 (default: 10)",
    )
    article_resolve.add_argument("--continuation", help="resume an incomplete scan")
    article_resolve.set_defaults(handler=_resolve_url)

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
