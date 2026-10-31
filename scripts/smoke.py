"""Exercise the installed CLI against Feedly without modifying account data.

Run with FEEDLY_TOKEN set: python scripts/smoke.py
Only command names and result counts are printed; account data stays in memory.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from io import StringIO

from feedly_cli import output
from feedly_cli.output.article_data import article_url


def check_article_presentations(page: dict) -> None:
    """Check complete live identifiers in every text mode without printing them."""
    items = page.get("items", [])
    if not items:
        raise RuntimeError("search: no articles available to verify presentation")
    statuses = {"contains": 0, "empty": 0, "unknown": 0}
    expected_statuses = []
    for item in items:
        metadata = item.get("indicatorsOfCompromise")
        mentions = metadata.get("mentions") if isinstance(metadata, dict) else None
        if not isinstance(mentions, list) or any(
            not isinstance(mention, dict) or not mention for mention in mentions
        ):
            statuses["unknown"] += 1
            expected_statuses.append("Unknown (Feedly IoC metadata unavailable)")
        elif mentions:
            statuses["contains"] += 1
            noun = "mention" if len(mentions) == 1 else "mentions"
            expected_statuses.append(f"Contains IoC (Feedly: {len(mentions)} extracted {noun})")
        else:
            statuses["empty"] += 1
            expected_statuses.append("No IoCs reported by Feedly (not proof of absence)")
    expected_machine_states = [
        "present"
        if status.startswith("Contains IoC")
        else "not_reported"
        if status.startswith("No IoCs")
        else "unknown"
        for status in expected_statuses
    ]
    records = output.brief(page)["items"]
    if [record.get("iocStatus") for record in records] != expected_machine_states:
        raise RuntimeError("search: brief JSON IoC state does not match Feedly metadata")
    for details in (False, True):
        stream = StringIO()
        output.render(page, command="search", context={"details": details}, stream=stream)
        text = stream.getvalue()
        for item in items:
            if not item.get("id") or not article_url(item):
                raise RuntimeError("search: live article is missing an ID or publisher URL")
            if item["id"] not in text or article_url(item) not in text:
                raise RuntimeError("search: terminal output truncated an ID or publisher URL")
        actual_statuses = [
            line.removeprefix("  Indicators: ")
            for line in text.splitlines()
            if line.startswith("  Indicators: ")
        ]
        if actual_statuses != expected_statuses:
            raise RuntimeError("search: terminal IoC status does not match Feedly metadata")
    for include_content in (False, True):
        stream = StringIO()
        output.write_markdown(page, stream, include_content=include_content)
        text = stream.getvalue()
        for item in items:
            if item["id"] not in text or article_url(item) not in text:
                raise RuntimeError("search: Markdown output lost an ID or publisher URL")
        actual_statuses = [
            line.removeprefix("- Indicators: ")
            for line in text.splitlines()
            if line.startswith("- Indicators: ")
        ]
        if actual_statuses != expected_statuses:
            raise RuntimeError("search: Markdown IoC status does not match Feedly metadata")
    print(
        f"PASS live article presentation: {len(items)} articles, "
        "default/details/Markdown/brief JSON states"
    )
    print(
        f"Feedly IoC metadata: {statuses['contains']} contains, "
        f"{statuses['empty']} empty, {statuses['unknown']} unavailable"
    )


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
    hydrated = run("search", "PHP2Shell", "--all", "--fetch")
    check_article_presentations(hydrated)
    listing = run("search", "PHP2Shell", "--count", "1", text_output=True)
    if any(field not in listing for field in ("Entry ID:", "URL:", "Indicators:")):
        raise RuntimeError("search: default text output is missing ID, URL or IoC status")
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
