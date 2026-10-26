"""Profile and collection listing commands."""

from __future__ import annotations

import argparse
from typing import Any

from ..client import FeedlyClient


def _profile(args: argparse.Namespace, client: FeedlyClient) -> Any:
    del args
    return client.profile()


def _folders(args: argparse.Namespace, client: FeedlyClient) -> Any:
    del args
    return client.folders()


def _feeds(args: argparse.Namespace, client: FeedlyClient) -> Any:
    del args
    return client.feeds()


def register(commands: argparse._SubParsersAction) -> None:
    profile = commands.add_parser("profile", help="show the authenticated Feedly profile")
    profile.set_defaults(handler=_profile)

    folders = commands.add_parser("folders", help="list enterprise collections")
    folder_actions = folders.add_subparsers(
        dest="folders_command", required=True, parser_class=type(folders)
    )
    folder_list = folder_actions.add_parser("list", help="list folders")
    folder_list.set_defaults(handler=_folders)

    feeds = commands.add_parser("feeds", help="list enterprise searches")
    feed_actions = feeds.add_subparsers(
        dest="feeds_command", required=True, parser_class=type(feeds)
    )
    feed_list = feed_actions.add_parser("list", help="list feeds")
    feed_list.set_defaults(handler=_feeds)
