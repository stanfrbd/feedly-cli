"""CLI-local validation, exit codes, and structured error output."""

from __future__ import annotations

import json
import sys
from typing import Any

from .. import output

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_AUTH = 3
EXIT_NOT_FOUND = 4
EXIT_RATE_LIMIT = 5
EXIT_API = 6
EXIT_UNEXPECTED = 7


class InputError(Exception):
    """A validly parsed command has invalid local input or options."""


class UsageError(InputError):
    """An argparse usage error that should be returned as JSON when requested."""


class MissingTokenError(Exception):
    """The CLI cannot create a Feedly client without FEEDLY_TOKEN."""


def write_json(value: Any, *, stream: Any = None) -> None:
    target = stream if stream is not None else sys.stdout
    target.write(json.dumps(value, ensure_ascii=True, separators=(",", ":")) + "\n")
    target.flush()


def write_error(
    code: str,
    category: str,
    message: str,
    exit_code: int,
    details: Any = None,
    *,
    json_output: bool = False,
) -> int:
    error = {"code": code, "category": category, "message": message}
    if details is not None:
        error["details"] = details
    if json_output:
        write_json({"error": error}, stream=sys.stderr)
    else:
        output.render_error(code, message, stream=sys.stderr)
    return exit_code


def error_details(exc: Exception) -> tuple[str, str, int, str]:
    name = type(exc).__name__.lower()
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    message = str(exc) or type(exc).__name__
    if hasattr(exc, "exit_code") and hasattr(exc, "code"):
        code = str(exc.code)
        exit_code = int(exc.exit_code)
        category = {
            "configuration_error": "configuration",
            "authentication_error": "authentication",
            "permission_denied": "permission",
            "not_found": "not_found",
            "bad_request": "bad_request",
            "rate_limited": "rate_limit",
            "server_error": "api",
            "api_error": "api",
            "network_error": "network",
        }.get(code, "internal")
        if category == "internal":
            exit_code = EXIT_UNEXPECTED
        return code, category, exit_code, message
    if status in (401, 403) or "auth" in name or "token" in name or "unauthorized" in name:
        return "authentication_error", "authentication", EXIT_AUTH, message
    if status == 404 or "notfound" in name or "not_found" in name:
        return "not_found", "not_found", EXIT_NOT_FOUND, message
    if status == 429 or "ratelimit" in name or "rate_limit" in name:
        return "rate_limited", "rate_limit", EXIT_RATE_LIMIT, message
    if (
        isinstance(exc, (TimeoutError, ConnectionError, OSError))
        or "network" in name
        or "http" in name
    ):
        return "api_error", "api", EXIT_API, message
    if status is not None or "feedly" in name or "apierror" in name:
        return "api_error", "api", EXIT_API, message
    return "internal_error", "internal", EXIT_UNEXPECTED, message


def redact(value: Any, secret: str) -> Any:
    if isinstance(value, str):
        return value.replace(secret, "[redacted]")
    if isinstance(value, list):
        return [redact(item, secret) for item in value]
    if isinstance(value, dict):
        return {key: redact(item, secret) for key, item in value.items()}
    return value
