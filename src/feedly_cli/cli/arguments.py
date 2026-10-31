"""CLI argument validators and pre-authentication input checks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ..api.url_resolution import validate_url
from ..errors import FeedlyError
from .errors import InputError


def http_url(value: str) -> str:
    try:
        validate_url(value)
    except FeedlyError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return value


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def nonnegative_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return number


def positive_float(value: str) -> float:
    import math

    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def bounded_positive_int(maximum: int):
    def parse(value: str) -> int:
        number = positive_int(value)
        if number > maximum:
            raise argparse.ArgumentTypeError(f"must be at most {maximum}")
        return number

    return parse


def read_query_file(filename: str) -> dict[str, Any]:
    try:
        raw = sys.stdin.read() if filename == "-" else Path(filename).read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"cannot read query file: {exc}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InputError(
            f"query file is not valid JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}"
        ) from exc
    if not isinstance(payload, dict):
        raise InputError("query file must contain a JSON object")
    return payload
