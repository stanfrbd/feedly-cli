"""Vulnerability presentation helpers for Feedly responses."""

from __future__ import annotations

import sys
from typing import Any

from rich.table import Table

from .common import clean_line, clean_text, create_console, format_date, literal, pick

_SUMMARY_WIDTH = 160


def _metadata(item: dict[str, Any]) -> dict[str, Any]:
    metadata = item.get("vulnerabilitiesMetadata")
    return metadata if isinstance(metadata, dict) else {}


def _score(item: dict[str, Any], key: str) -> Any:
    value = item.get(key)
    return value.get("baseScore") if isinstance(value, dict) else None


def cvss_text(item: dict[str, Any]) -> str:
    """Describe the CVSS score of a CVE entity or trending entry, if Feedly provides one."""
    metadata = _metadata(item)
    v3, v4 = _score(item, "cvssV3"), _score(item, "cvssV4")
    scores = [f"v3 {v3}" if v3 is not None else "", f"v4 {v4}" if v4 is not None else ""]
    score = ", ".join(part for part in scores if part) or clean_text(
        pick(item, "cvss") or pick(metadata, "cvss")
    )
    severity = pick(item, "cvssCategoryEstimate", "severity", "cvssSeverity", "risk") or pick(
        metadata, "severity", "cvssSeverity"
    )
    return " ".join(
        part for part in (score, f"({clean_text(severity)})" if severity else "") if part
    )


def _text(value: Any) -> str:
    if isinstance(value, list):
        value = " ".join(clean_line(part) for part in value)
    return clean_line(value)


def _trim(text: str, width: int = _SUMMARY_WIDTH) -> str:
    return text if len(text) <= width else text[: width - 1].rstrip() + "…"


def _flags(item: dict[str, Any]) -> str:
    metadata = _metadata(item)
    exploit = item.get("hasExploit") or metadata.get("hasExploit") or item.get("exploits")
    flags = [
        ("trending", item.get("trending")),
        ("exploit", exploit),
        ("patched", item.get("patched")),
    ]
    return ", ".join(name for name, enabled in flags if enabled)


def render_vulnerabilities(items: list[dict[str, Any]], stream: Any = None) -> None:
    table = Table(title="Vulnerabilities", show_lines=True, expand=True, box=None)
    for title in ("CVE", "CVSS", "Flags", "Published", "Summary"):
        table.add_column(title, overflow="fold", no_wrap=False)
    for item in items:
        metadata = _metadata(item)
        published = pick(item, "published", "publishedDate", "created") or pick(
            metadata, "publishedDate", "published"
        )
        table.add_row(
            literal(pick(item, "cve", "cveId", "cveid", "label", "name", "id")),
            literal(cvss_text(item)),
            literal(_flags(item)),
            literal(format_date(published)),
            literal(_trim(_text(pick(item, "title", "summary", "description")))),
        )
    create_console(stream).print(table)


def _labels(values: Any, *keys: str) -> str:
    if not isinstance(values, list):
        return ""
    names = [
        clean_line(pick(value, *keys) if isinstance(value, dict) else value) for value in values
    ]
    return ", ".join(name for name in names if name)


def _vendors(item: dict[str, Any]) -> str:
    estimate = item.get("affectedProductsEstimate")
    parts = []
    for entry in estimate if isinstance(estimate, list) else []:
        if not isinstance(entry, dict):
            continue
        products = _labels(entry.get("products"), "name")
        vendor = clean_line(entry.get("vendor"))
        parts.append(f"{vendor} ({products})" if products else vendor)
    return ", ".join(part for part in parts if part)


def _count(value: Any) -> str:
    return str(len(value)) if isinstance(value, list) and value else ""


def cve_fields(item: dict[str, Any]) -> dict[str, str]:
    story = item.get("whatSoWhat")
    story = story if isinstance(story, dict) else {}
    executive = item.get("executiveSummary")
    executive = executive if isinstance(executive, dict) else {}
    return {
        "CVSS": cvss_text(item),
        "EPSS": clean_line(item.get("epssScore")),
        "Status": clean_line(item.get("cveStatus")),
        "Flags": _flags(item),
        "Published": format_date(item.get("publishedDate")),
        "Weakness": _labels(item.get("cweIds"), "cweID"),
        "Attack type": clean_line(executive.get("attack_type")),
        "Vendors / products": _vendors(item),
        "Public exploits": _count(item.get("exploits")),
        "Proofs of concept": _count(item.get("proofOfExploits")),
        "ATT&CK / CAPEC": _labels(item.get("idMapping"), "id"),
        "Patch": clean_line(executive.get("patch")),
        "Advisory": clean_line(item.get("advisoryUrl")),
        "What": clean_line(story.get("what")),
        "So what": clean_line(story.get("soWhat")),
        "Description": clean_line(item.get("description")),
    }


def render_cve_details(items: list[dict[str, Any]], stream: Any = None) -> None:
    """Write one readable block per CVE entity instead of dumping every raw field."""
    target = stream if stream is not None else sys.stdout
    for index, item in enumerate(items):
        if index:
            target.write("\n")
        target.write(f"{clean_line(pick(item, 'cveid', 'label', 'id'))}\n")
        for label, value in cve_fields(item).items():
            if value:
                target.write(f"  {label}: {value}\n")
