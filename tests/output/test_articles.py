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
def test_default_search_shows_entry_id_and_cves_but_not_url_or_body(monkeypatch, width):
    monkeypatch.setenv("COLUMNS", str(width))
    text = human({"items": [CISA_ARTICLE]})
    assert "Entry ID: entry-cisa" in text
    assert "CISA confirms PHP2Shell exploitation" in text
    assert "BleepingComputer" in text and "2026-10-26" in text
    assert "CVE-2026-109618 (CVSS 9.2 HIGH, exploit, patch)" in text
    assert "https://example.com/cisa" not in text
    assert "Summary:" not in text and "Large body" not in text


def test_details_add_url_and_threat_intel():
    text = human({"items": [CISA_ARTICLE]}, context={"details": True})
    assert "URL: https://example.com/cisa" in text
    assert "ATT&CK: Initial Access" in text
    assert "Summary: CISA added PHP2Shell to KEV." in text
    assert "Indicators: 1 extracted" in text


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
        context={"details": True},
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
        context={"details": True},
    )
    assert entry_id in text
    assert url in text
    assert "[bold]Literal[/bold]" in text
    assert "\x1b" not in text
    assert "next-page-token" in text


def test_article_get_contains_body_but_lists_stay_brief():
    article = {"id": "a", "title": "Title", "content": {"content": "<p>Distinct body content</p>"}}
    assert "Distinct body content" in human([article], "articles", "get")
    assert "Distinct body content" not in human({"items": [article]})
