"""CVE entity lookup and vulnerability search commands."""

from __future__ import annotations

import argparse
from typing import Any

from ..cli.arguments import positive_int, read_query_file
from ..cli.errors import InputError
from ..client import FeedlyClient


def _get_cve(args: argparse.Namespace, client: FeedlyClient) -> Any:
    return client.cve(args.id)


def _get_cves(args: argparse.Namespace, client: FeedlyClient) -> Any:
    return client.cves(args.ids)


def _trending(args: argparse.Namespace, client: FeedlyClient) -> Any:
    return client.cve_trending(count=args.count)


def _search(args: argparse.Namespace, client: FeedlyClient) -> Any:
    return client.cve_search(
        args.query_payload,
        count=args.count,
        continuation=args.continuation,
    )


def _validate_trending(args: argparse.Namespace) -> None:
    if args.count > 25:
        raise InputError("--count must be at most 25")


def _validate_search(args: argparse.Namespace) -> None:
    args.query_payload = read_query_file(args.query_file)


def register(commands: argparse._SubParsersAction) -> None:
    cve = commands.add_parser("cve", help="look up a CVE identifier")
    cve.add_argument("id", help="CVE identifier, such as CVE-2024-12345")
    cve.set_defaults(handler=_get_cve)

    cves = commands.add_parser("cves", help="query Feedly vulnerability intelligence")
    actions = cves.add_subparsers(dest="cves_command", required=True, parser_class=type(cves))
    get = actions.add_parser("get", help="look up one or more CVE identifiers")
    get.add_argument("ids", nargs="+", help="one or more CVE identifiers")
    get.set_defaults(handler=_get_cves)

    trending = actions.add_parser("trending", help="list trending vulnerabilities")
    trending.add_argument(
        "--count", type=positive_int, default=10, help="maximum results, up to 25 (default: 10)"
    )
    trending.set_defaults(handler=_trending, validate=_validate_trending)

    search = actions.add_parser("search", help="search vulnerability intelligence")
    search.add_argument(
        "--query-file",
        required=True,
        help="JSON request body file, or - to read JSON from stdin",
    )
    search.add_argument(
        "--count", type=positive_int, default=20, help="maximum results (default: 20)"
    )
    search.add_argument("--continuation", help="continuation token from a prior response")
    search.set_defaults(handler=_search, validate=_validate_search)
