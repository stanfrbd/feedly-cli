"""Exercise the installed CLI against Feedly without modifying account data.

Run with FEEDLY_TOKEN set: python scripts/smoke.py
Only command names and result counts are printed; account data stays in memory.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys


def run(
    *args: str,
    lines: bool = False,
    payload: dict | None = None,
    allow_unavailable: bool = False,
    text_output: bool = False,
):
    output_args = [] if text_output else ["--json"]
    result = subprocess.run(
        [sys.executable, "-m", "feedly_cli", *output_args, *args],
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        input=json.dumps(payload) if payload is not None else None,
        timeout=180,
    )
    if result.returncode:
        # Error messages may contain account identifiers; report only the code.
        try:
            code = json.loads(result.stderr)["error"]["code"]
        except (ValueError, KeyError, TypeError):
            code = "invalid_error_output"
        if allow_unavailable and result.returncode == 3 and code == "permission_denied":
            print(f"UNAVAILABLE {' '.join(args[:2])}: account entitlement denied (403)")
            return None
        raise RuntimeError(f"{args[0]}: exit {result.returncode} ({code})")
    if result.stderr:
        raise RuntimeError(f"{args[0]}: unexpected stderr")
    if text_output:
        if not result.stdout.strip() or "\x1b" in result.stdout:
            raise RuntimeError(f"{args[0]}: empty or terminal-encoded text output")
        print(f"PASS {' '.join(args[:2])} (text)")
        return result.stdout
    value = (
        [json.loads(line) for line in result.stdout.splitlines()]
        if lines
        else json.loads(result.stdout)
    )
    print(f"PASS {' '.join(args[:2]) if len(args) > 1 else args[0]}")
    return value


def main() -> int:
    if not os.environ.get("FEEDLY_TOKEN"):
        print("FEEDLY_TOKEN is required", file=sys.stderr)
        return 2
    run("profile")
    boards = run("boards", "list")
    run("folders", "list")
    run("feeds", "list")
    run("cve", "CVE-2021-44228")
    run("cves", "get", "CVE-2021-44228", "CVE-2024-3094")
    run("cves", "trending", "--count", "1")
    run("search", "ransomware")
    run("search", "PHP2Shell", "--all", "--fetch")
    listing = run("search", "PHP2Shell", "--count", "1", text_output=True)
    if "Entry ID:" not in listing:
        raise RuntimeError("search: default text output is missing the entry ID")
    found = run("search", "PHP2Shell", "--count", "3", "--salience", "about", "--brief")
    if not found.get("items") or any("id" not in article for article in found["items"]):
        raise RuntimeError("search: brief JSON output is missing article IDs")
    run("articles", "get", found["items"][0]["id"], "--markdown", "--brief", text_output=True)
    run("search", "PHP2Shell", "--count", "1", "--fetch", "--markdown", text_output=True)
    converted = run("search", "PHP2Shell", "--count", "1", "--fetch", "--markdown")
    if any("contentMarkdown" not in article for article in converted.get("items", [])):
        raise RuntimeError("search: Markdown field missing from JSON output")
    run(
        "cves",
        "search",
        "--query-file",
        "-",
        "--count",
        "1",
        payload={"layers": [{"filters": [{"field": "period", "value": {"type": "Last7Days"}}]}]},
        allow_unavailable=True,
    )
    if boards:
        board = boards[0]["id"]
        page = run("boards", "read", board, "--count", "1")
        run("streams", "read", board, "--count", "1")
        if page.get("continuation"):
            run("boards", "read", board, "--count", "1", "--continuation", page["continuation"])
        # Monitor just one poll: no sleeps or long-running processes.
        run("boards", "watch", board, "--iterations", "1", lines=True)
        if page.get("items"):
            entry = page["items"][0]
            run("articles", "get", entry["id"])
            url = entry.get("canonicalUrl") or next(
                (link["href"] for link in entry.get("alternate", []) if link.get("href")),
                None,
            )
            if url:
                run("boards", "add-url", board, url, "--stream-id", board, "--dry-run")
    else:
        print("SKIP board-dependent checks: account has no boards")
    print("Read-only live checks completed; any entitlement denials are listed above.")
    print("Board writes are covered offline.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1) from None
