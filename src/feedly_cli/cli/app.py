"""Application lifecycle: parse, validate, run a registered handler, and render."""

from __future__ import annotations

import argparse
import os
import sys
from contextlib import suppress

from ..client import FeedlyClient
from .display import StreamedOutput, display
from .errors import (
    EXIT_AUTH,
    EXIT_OK,
    EXIT_USAGE,
    InputError,
    MissingTokenError,
    UsageError,
    error_details,
    redact,
    write_error,
)
from .parser import build_parser


def create_client() -> FeedlyClient:
    """Create the authenticated client; exposed as the app's test seam."""
    token = os.environ.get("FEEDLY_TOKEN")
    if not token:
        raise MissingTokenError("FEEDLY_TOKEN is not set")
    return FeedlyClient(token=token)


def _request_json(argv: list[str]) -> bool:
    option_tokens = argv[: argv.index("--")] if "--" in argv else argv
    return "--json" in option_tokens


def main(argv: list[str] | None = None) -> int:
    """Run the Feedly CLI and return its stable process exit code."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    argv = list(sys.argv[1:] if argv is None else argv)
    json_output = _request_json(argv)
    client: FeedlyClient | None = None
    try:
        args = build_parser().parse_args(
            argv,
            namespace=argparse.Namespace(json=False, markdown=False),
        )
        json_output = args.json
        if args.markdown and not getattr(args, "supports_markdown", False):
            raise InputError("--markdown is supported for article, search and stream results only")
        validator = getattr(args, "validate", None)
        if validator is not None:
            validator(args)
        client = create_client()
        result = args.handler(args, client)
        if isinstance(result, StreamedOutput):
            return result.exit_code
        display(result, args)
        return EXIT_OK
    except UsageError as exc:
        return write_error("usage_error", "usage", str(exc), EXIT_USAGE, json_output=json_output)
    except InputError as exc:
        return write_error("invalid_input", "usage", str(exc), EXIT_USAGE, json_output=json_output)
    except MissingTokenError as exc:
        return write_error(
            "missing_token",
            "authentication",
            str(exc),
            EXIT_AUTH,
            json_output=json_output,
        )
    except SystemExit as exc:
        return int(exc.code or 0)
    except Exception as exc:
        code, category, exit_code, message = error_details(exc)
        token = os.environ.get("FEEDLY_TOKEN")
        if token:
            message = message.replace(token, "[redacted]")
        details = None
        to_dict = getattr(exc, "to_dict", None)
        if callable(to_dict):
            details = to_dict().get("details")
        if token and details is not None:
            details = redact(details, token)
        return write_error(
            code,
            category,
            message,
            exit_code,
            details,
            json_output=json_output,
        )
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            with suppress(Exception):
                close()
