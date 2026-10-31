"""Threat-intelligence facts Feedly attaches to articles, shared by every output format."""

from __future__ import annotations

import copy
from typing import Any

from .article_data import article_url, articles_from_response, source_name
from .common import clean_text, format_date, pick

_ENTITY_GROUPS = {
    "malware": "malware",
    "threatActor": "threatActors",
    "mitreAttack": "techniques",
}


def _entities(item: dict[str, Any]) -> list[dict[str, Any]]:
    entities = item.get("entities")
    if not isinstance(entities, list):
        return []
    return [entity for entity in entities if isinstance(entity, dict)]


def _cve(entity: dict[str, Any]) -> dict[str, Any]:
    info = entity.get("vulnerabilityInfo")
    info = info if isinstance(info, dict) else {}
    return {
        key: value
        for key, value in {
            "id": entity.get("label") or str(entity["id"]).rsplit("/", 1)[-1],
            "cvss": info.get("cvssScore"),
            "severity": info.get("cvssCategoryEstimate"),
            "hasExploit": info.get("hasExploit"),
            "hasPatch": info.get("hasPatch"),
        }.items()
        if value is not None
    }


def threat_intel(item: dict[str, Any]) -> dict[str, Any]:
    """Collect CVEs, malware, actors, techniques and the Leo summary of one article."""
    groups: dict[str, list[str]] = {name: [] for name in _ENTITY_GROUPS.values()}
    cves: list[dict[str, Any]] = []
    seen_cves: set[str] = set()
    for entity in _entities(item):
        identifier = str(entity.get("id") or "")
        label = entity.get("label")
        if identifier.startswith("vulnerability/"):
            cve = _cve({**entity, "id": identifier})
            if cve["id"] not in seen_cves:
                seen_cves.add(cve["id"])
                cves.append(cve)
        elif label and entity.get("type") in _ENTITY_GROUPS:
            group = groups[_ENTITY_GROUPS[entity["type"]]]
            if label not in group:
                group.append(label)
    summary = item.get("leoSummary")
    sentences = summary.get("sentences") if isinstance(summary, dict) else None
    ioc = item.get("indicatorsOfCompromise")
    mentions = ioc.get("mentions") if isinstance(ioc, dict) else None
    navigator = item.get("attackNavigator")
    return {
        "cves": cves,
        **groups,
        "summary": " ".join(
            sentence["text"]
            for sentence in sentences or []
            if isinstance(sentence, dict) and sentence.get("text")
        ),
        "iocCount": len(mentions) if isinstance(mentions, list) else 0,
        "ttpCount": navigator.get("ttpCount") if isinstance(navigator, dict) else None,
    }


def describe_cve(cve: dict[str, Any]) -> str:
    """One-line CVE label such as ``CVE-2026-1 (CVSS 9.8 HIGH, exploit, patch)``."""
    facts = []
    score = " ".join(
        clean_text(part)
        for part in (cve.get("cvss") and f"CVSS {cve['cvss']}", cve.get("severity"))
        if part
    )
    if score:
        facts.append(score)
    if cve.get("hasExploit"):
        facts.append("exploit")
    if cve.get("hasPatch"):
        facts.append("patch")
    label = clean_text(cve["id"])
    return f"{label} ({', '.join(facts)})" if facts else label


def describe_ioc(item: dict[str, Any]) -> str:
    """Describe Feedly's extraction metadata, never infer IoCs from article links."""
    metadata = item.get("indicatorsOfCompromise")
    mentions = metadata.get("mentions") if isinstance(metadata, dict) else None
    if not isinstance(mentions, list) or any(
        not isinstance(mention, dict) or not mention for mention in mentions
    ):
        return "Unknown (Feedly IoC metadata unavailable)"
    if mentions:
        noun = "mention" if len(mentions) == 1 else "mentions"
        return f"Contains IoC (Feedly: {len(mentions)} extracted {noun})"
    return "No IoCs reported by Feedly (not proof of absence)"


def brief_article(item: dict[str, Any]) -> dict[str, Any]:
    """Identification-only record of an article: IDs, links and threat facts, no body."""
    intel = threat_intel(item)
    record = {
        "id": pick(item, "id", "entryId"),
        "title": pick(item, "title", "headline"),
        "url": article_url(item),
        "source": source_name(item),
        "published": pick(item, "published", "publishedDate", "crawled"),
        "publishedDate": format_date(pick(item, "published", "publishedDate", "crawled")) or None,
    }
    record.update(intel)
    return {key: value for key, value in record.items() if value}


def brief(value: Any) -> Any:
    """Replace every article in a response with its brief record, keeping the envelope."""
    result = copy.deepcopy(value)
    articles, wrapper = articles_from_response(result)
    if wrapper is not None:
        result[wrapper] = [brief_article(article) for article in articles]
        return result
    if isinstance(result, list):
        return [brief_article(article) for article in articles]
    return brief_article(articles[0]) if articles else result
