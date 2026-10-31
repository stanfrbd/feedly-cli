import copy
from io import StringIO

import pytest

from feedly_cli import output

from .helpers import human

CISA_ARTICLE = {
    "id": "entry-cisa",
    "title": "CISA confirms PHP2Shell exploitation",
    "canonicalUrl": "https://example.com/cisa",
    "published": 1793016000000,
    "origin": {"title": "BleepingComputer"},
    "entities": [
        {
            "id": "vulnerability/m/entity/CVE-2026-109618",
            "label": "CVE-2026-109618",
            "vulnerabilityInfo": {
                "cvssScore": 9.2,
                "cvssCategoryEstimate": "HIGH",
                "hasExploit": True,
                "hasPatch": True,
            },
        },
        {"id": "nlp/f/entity/gz:org:php", "label": "PHP", "type": "vendor"},
        {"id": "nlp/f/entity/gz:ta:x", "label": "Initial Access", "type": "mitreAttack"},
    ],
    "leoSummary": {"sentences": [{"text": "CISA added PHP2Shell to KEV."}]},
    "indicatorsOfCompromise": {"mentions": [{"type": "domain"}]},
    "fullContent": {"content": "<p>Large body</p>"},
}


@pytest.mark.parametrize("width", [80, 100, 120])
def test_default_search_shows_entry_id_url_iocs_and_cves_without_body(monkeypatch, width):
    monkeypatch.setenv("COLUMNS", str(width))
    text = human({"items": [CISA_ARTICLE]})
    assert "Entry ID: entry-cisa" in text
    assert "CISA confirms PHP2Shell exploitation" in text
    assert "BleepingComputer" in text and "2026-10-26" in text
    assert "CVE-2026-109618 (CVSS 9.2 HIGH, exploit, patch)" in text
    assert "URL: https://example.com/cisa" in text
    assert "Indicators: Contains IoC (Feedly: 1 extracted mention)" in text
    assert "Summary:" not in text and "Large body" not in text


def test_details_add_threat_intel():
    text = human({"items": [CISA_ARTICLE]}, context={"details": True})
    assert "URL: https://example.com/cisa" in text
    assert "ATT&CK: Initial Access" in text
    assert "Summary: CISA added PHP2Shell to KEV." in text
    assert "Indicators: Contains IoC (Feedly: 1 extracted mention)" in text
    assert text.count("Indicators:") == 1


def test_brief_keeps_envelope_and_only_identification_fields():
    result = output.brief({"items": [CISA_ARTICLE], "continuation": "next"})
    assert result["continuation"] == "next"
    assert result["items"] == [
        {
            "id": "entry-cisa",
            "title": "CISA confirms PHP2Shell exploitation",
            "url": "https://example.com/cisa",
            "source": "BleepingComputer",
            "published": 1793016000000,
            "publishedDate": "2026-10-26 12:00 UTC",
            "cves": [
                {
                    "id": "CVE-2026-109618",
                    "cvss": 9.2,
                    "severity": "HIGH",
                    "hasExploit": True,
                    "hasPatch": True,
                }
            ],
            "techniques": ["Initial Access"],
            "summary": "CISA added PHP2Shell to KEV.",
            "iocCount": 1,
        }
    ]
    assert output.brief(CISA_ARTICLE)["id"] == "entry-cisa"


def test_markdown_brief_has_threat_facts_without_body():
    stream = StringIO()
    output.write_markdown({"items": [CISA_ARTICLE]}, stream, include_content=False)
    text = stream.getvalue()
    assert "Entry ID: entry-cisa" in text and "CVE-2026-109618" in text
    assert "URL: https://example.com/cisa" in text
    assert "Indicators: Contains IoC (Feedly: 1 extracted mention)" in text
    assert "Large body" not in text and "Content source" not in text


def test_detail_identifiers_stay_with_their_article():
    text = human(
        {
            "items": [
                {
                    "id": "entry-one",
                    "title": "First article",
                    "canonicalUrl": "https://example.com/one",
                },
                {
                    "id": "entry-two",
                    "title": "Second article",
                    "canonicalUrl": "https://example.com/two",
                },
            ]
        },
        context={"details": True},
    )
    assert text.index("First article") < text.index("entry-one") < text.index("Second article")
    assert text.index("Second article") < text.index("entry-two")


def test_narrow_terminal_uses_article_details_and_complete_identifiers(monkeypatch):
    monkeypatch.setenv("COLUMNS", "40")
    entry_id = "entry/" + "abcdef" * 25
    url = "https://example.com/" + "path/" * 30
    text = human(
        {"items": [{"id": entry_id, "title": "Research", "canonicalUrl": url}]},
    )
    assert "Article 1" in text
    assert "Research" in text
    assert entry_id in text
    assert url in text


@pytest.mark.parametrize("action", ["read", "watch"])
def test_board_article_output_complete_untrusted_metadata(action):
    entry_id = "entry/" + "abc123" * 30
    url = "https://example.test/" + "long-path/" * 25
    text = human(
        {
            "items": [
                {
                    "id": entry_id,
                    "title": "[bold]Literal[/bold]\x1b[31m",
                    "alternate": [{"href": url}],
                }
            ],
            "continuation": "next-page-token",
        },
        "boards",
        action,
    )
    assert entry_id in text
    assert url in text
    assert "[bold]Literal[/bold]" in text
    assert "\x1b" not in text
    assert "next-page-token" in text


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        ({}, "Unknown (Feedly IoC metadata unavailable)"),
        ({"indicatorsOfCompromise": None}, "Unknown (Feedly IoC metadata unavailable)"),
        ({"indicatorsOfCompromise": []}, "Unknown (Feedly IoC metadata unavailable)"),
        (
            {"indicatorsOfCompromise": {"exports": [{"url": "https://example.test/iocs"}]}},
            "Unknown (Feedly IoC metadata unavailable)",
        ),
        (
            {"indicatorsOfCompromise": {"mentions": "https://example.test"}},
            "Unknown (Feedly IoC metadata unavailable)",
        ),
        (
            {"indicatorsOfCompromise": {"mentions": [None]}},
            "Unknown (Feedly IoC metadata unavailable)",
        ),
        (
            {"indicatorsOfCompromise": {"mentions": [{}]}},
            "Unknown (Feedly IoC metadata unavailable)",
        ),
        (
            {"indicatorsOfCompromise": {"mentions": [{"type": "domain"}, "bad"]}},
            "Unknown (Feedly IoC metadata unavailable)",
        ),
        (
            {"indicatorsOfCompromise": {"mentions": []}},
            "No IoCs reported by Feedly (not proof of absence)",
        ),
        (
            {
                "indicatorsOfCompromise": {
                    "mentions": [],
                    "sigmaRules": {"count": 1, "url": "https://example.test/rule.yaml"},
                }
            },
            "No IoCs reported by Feedly (not proof of absence)",
        ),
        (
            {"indicatorsOfCompromise": {"mentions": [{"type": "domain"}, {"type": "hash"}]}},
            "Contains IoC (Feedly: 2 extracted mentions)",
        ),
    ],
)
def test_ioc_status_consistent_in_terminal_and_markdown_without_inference(metadata, expected):
    article = {
        "id": "entry/ioc",
        "title": "IoCs in research",
        "canonicalUrl": "https://example.test/article",
        "content": {"content": "<p>IoC: https://example.test/reference 192.0.2.1</p>"},
        **metadata,
    }
    original = copy.deepcopy(article)
    for details in (False, True):
        text = human({"items": [article]}, context={"details": details})
        assert f"Indicators: {expected}" in text
    for include_content in (False, True):
        stream = StringIO()
        output.write_markdown({"items": [article]}, stream, include_content=include_content)
        assert f"- Indicators: {expected}" in stream.getvalue()
    assert article == original


@pytest.mark.parametrize(
    ("command", "action"),
    [
        ("search", None),
        ("streams", "read"),
        ("boards", "read"),
        ("boards", "watch"),
        ("articles", "get"),
    ],
)
def test_article_surfaces_always_include_id_url_and_ioc_status(command, action):
    text = human({"items": [CISA_ARTICLE]}, command, action)
    assert "Entry ID: entry-cisa" in text
    assert "URL: https://example.com/cisa" in text
    assert "Indicators: Contains IoC (Feedly: 1 extracted mention)" in text


@pytest.mark.parametrize(
    "links",
    [
        {"canonicalUrl": "https://example.test/article", "alternate": [{"href": "other"}]},
        {"url": "https://example.test/article"},
        {"alternateUrl": "https://example.test/article"},
        {"originalUrl": "https://example.test/article"},
        {"alternate": [{}, {"href": "https://example.test/article", "type": "text/html"}]},
        {"alternate": {"href": "https://example.test/article"}},
    ],
)
def test_default_url_fallbacks(links):
    article = {"entryId": "fallback/id", "title": "Article", **links}
    assert "URL: https://example.test/article" in human([article])
    assert "Entry ID: fallback/id" in human([article])
    stream = StringIO()
    output.write_markdown([article], stream)
    assert "URL: https://example.test/article" in stream.getvalue()


def test_missing_identifiers_are_explicit_and_not_replaced_by_feed_links():
    article = {"title": "Article", "origin": {"htmlUrl": "https://example.test/feed-home"}}
    text = human([article])
    assert "Entry ID: Unavailable (not provided by Feedly)" in text
    assert "URL: Unavailable (not provided by Feedly)" in text
    stream = StringIO()
    output.write_markdown([article], stream)
    assert "Entry ID: Unavailable (not provided by Feedly)" in stream.getvalue()
    assert "URL: Unavailable (not provided by Feedly)" in stream.getvalue()


def test_article_get_contains_body_but_lists_stay_brief():
    article = {"id": "a", "title": "Title", "content": {"content": "<p>Distinct body content</p>"}}
    assert "Distinct body content" in human([article], "articles", "get")
    assert "Distinct body content" not in human({"items": [article]})
