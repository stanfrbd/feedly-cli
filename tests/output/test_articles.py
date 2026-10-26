import pytest

from .helpers import human


def test_narrow_terminal_uses_article_details_and_complete_identifiers(monkeypatch):
    monkeypatch.setenv("COLUMNS", "40")
    entry_id = "entry/" + "abcdef" * 25
    url = "https://example.com/" + "path/" * 30
    text = human({"items": [{"id": entry_id, "title": "Research", "canonicalUrl": url}]})
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


def test_article_get_contains_body_but_lists_stay_brief():
    article = {"id": "a", "title": "Title", "content": {"content": "<p>Distinct body content</p>"}}
    assert "Distinct body content" in human([article], "articles", "get")
    assert "Distinct body content" not in human({"items": [article]})
