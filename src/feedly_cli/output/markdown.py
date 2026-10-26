"""Markdown presentation helpers for Feedly responses."""

from __future__ import annotations

import copy
import sys
from typing import Any
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from markdownify import markdownify

from .article_data import article_items, article_url, articles_from_response, source_name
from .common import clean_text, format_date, pick


def _content_text(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("content") or value.get("text") or ""
    if not isinstance(value, str):
        return ""
    return value.strip()


def _markdown_for_article(article: dict[str, Any]) -> tuple[str, str]:
    full = _content_text(article.get("fullContent"))
    content = _content_text(article.get("content"))
    summary = _content_text(article.get("summary"))
    if full:
        return full, "content"
    if content:
        return content, "content"
    if summary:
        return summary, "summary"
    return "", "unavailable"


def _safe_html(source: str) -> str:
    soup = BeautifulSoup(clean_text(source), "html.parser")
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            if attr.lower().startswith("on"):
                del tag.attrs[attr]
        for attr in ("href", "src"):
            target = tag.attrs.get(attr)
            if isinstance(target, str):
                scheme = urlsplit(target.strip()).scheme.lower()
                if scheme and scheme not in {"http", "https", "mailto"}:
                    del tag.attrs[attr]
    return soup.decode_contents()


def add_markdown(value: Any) -> Any:
    """Return a deep copy with Markdown content fields added to article(s).

    Each article gets ``contentMarkdown`` and ``contentFormat``. Content is
    selected in this order: fullContent, content.content, summary.content.
    Existing response fields and nested objects are preserved unchanged.
    """
    result = copy.deepcopy(value)
    articles, wrapper = articles_from_response(result)
    for article in articles:
        markdown, fmt = article_markdown(article)
        article["contentMarkdown"] = markdown
        article["contentFormat"] = fmt
    if wrapper is not None:
        result[wrapper] = articles
    return result


def article_markdown(article: dict[str, Any]) -> tuple[str, str]:
    source, fmt = _markdown_for_article(article)
    if not source:
        return "", fmt
    return (
        markdownify(_safe_html(source), heading_style="ATX", bullets="-", code_language="").strip(),
        fmt,
    )


def write_markdown(value: Any, stream: Any = None) -> None:
    """Write one or more articles as Markdown, retaining lists and links."""
    if stream is None:
        stream = sys.stdout
    items = article_items(value)
    if (
        not items
        and isinstance(value, dict)
        and not any(isinstance(value.get(key), list) for key in ("items", "results", "entries"))
    ):
        items = [value]
    if not items:
        stream.write("No articles found.\n")
        if isinstance(value, dict) and value.get("continuation"):
            stream.write(
                f"\nMore results are available. Continuation: {clean_text(value['continuation'])}\n"
            )
            stream.write("Use this value with --continuation to fetch the next page.\n")
        return
    documents = []
    for article in items:
        title = clean_text(pick(article, "title", "headline") or "Untitled")
        content_md, fmt = article_markdown(article)
        entry_id = clean_text(pick(article, "id", "entryId"))
        url = clean_text(article_url(article))
        published = clean_text(format_date(pick(article, "published", "publishedDate", "crawled")))
        source = clean_text(source_name(article))
        metadata = [f"- Content source: {fmt}"]
        if source:
            metadata.append(f"- Source: {source}")
        if entry_id:
            metadata.append(f"- Entry ID: {entry_id}")
        if url:
            metadata.append(f"- URL: {url}")
        if published:
            metadata.append(f"- Published: {published}")
        body = content_md or "_(No Feedly content available.)_"
        documents.append(f"# {title}\n\n" + "\n".join(metadata) + f"\n\n{body}")
    stream.write("\n\n---\n\n".join(documents).rstrip() + "\n")
    if isinstance(value, dict) and value.get("pages") is not None:
        stream.write(f"\nPages fetched: {clean_text(value['pages'])}\n")
    if isinstance(value, dict) and value.get("continuation"):
        stream.write(
            f"\nMore results are available. Continuation: {clean_text(value['continuation'])}\n"
        )
        stream.write("Use this value with --continuation to fetch the next page.\n")
