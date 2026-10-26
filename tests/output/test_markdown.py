import copy
from io import StringIO

import pytest

from feedly_cli import output


def test_markdown_content_priority_nonmutating_envelope():
    raw = {
        "items": [
            {
                "id": "a",
                "fullContent": {
                    "content": '<h2>Full</h2><p><a href="https://example.test">link</a></p><pre><code>print(1)</code></pre>'
                },
                "summary": {"content": "summary"},
            }
        ],
        "continuation": "next",
    }
    original = copy.deepcopy(raw)
    result = output.add_markdown(raw)
    assert raw == original
    assert result["continuation"] == "next"
    item = result["items"][0]
    assert item["contentFormat"] == "content"
    assert "## Full" in item["contentMarkdown"]
    assert "[link](https://example.test)" in item["contentMarkdown"]
    assert "print(1)" in item["contentMarkdown"]
    assert "```" in item["contentMarkdown"]


@pytest.mark.parametrize(
    ("article", "expected"),
    [
        ({"content": {"content": "<p>body</p>"}}, "content"),
        ({"summary": {"content": "<p>brief</p>"}}, "summary"),
        ({"id": "a"}, "unavailable"),
    ],
)
def test_markdown_content_format_fallback(article, expected):
    assert output.add_markdown([article])[0]["contentFormat"] == expected


def test_markdown_empty_envelope_is_not_phantom_article():
    stream = StringIO()
    output.write_markdown({"items": []}, stream)
    assert "Untitled" not in stream.getvalue()
    assert "No articles found" in stream.getvalue()


def test_markdown_alternate_link_source_and_continuation():
    stream = StringIO()
    output.write_markdown(
        {
            "items": [
                {
                    "id": "a",
                    "title": "Article",
                    "alternate": [{"href": "https://example.test/a"}],
                    "origin": {"title": "Example News"},
                    "summary": {"content": "<ul><li>brief</li></ul>"},
                }
            ],
            "continuation": "next-page",
        },
        stream,
    )
    text = stream.getvalue()
    assert "https://example.test/a" in text
    assert "Example News" in text
    assert "next-page" in text
    assert "summary" in text
    assert "- brief" in text
