import pytest

from .helpers import human


@pytest.mark.parametrize("width", [80, 100, 120])
def test_compact_search_prioritizes_titles_without_identifier_dump(monkeypatch, width):
    monkeypatch.setenv("COLUMNS", str(width))
    title = "Hackers Weaponize Public PHP2Shell Exploit Code to Target Universities"
    text = human(
        {
            "items": [
                {
                    "id": "entry/long-id",
                    "title": title,
                    "published": 1793016000000,
                    "origin": {"title": "Security News"},
                    "canonicalUrl": "https://example.com/a",
                }
            ]
        }
    )
    assert "Article" in text and "Published" in text
    assert "2026-10-26" in text
    assert "UTC" not in text
    assert "Boards / tags" not in text
    assert "entry/long-id" not in text and "https://example.com/a" not in text
    assert "PHP2Shell" in text and "Universities" in text


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
