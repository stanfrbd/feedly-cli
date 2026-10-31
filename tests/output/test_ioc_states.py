import copy
from io import StringIO

import pytest

from feedly_cli import output

from .helpers import human


@pytest.mark.parametrize(
    ("metadata", "state", "count"),
    [
        ({}, "unknown", None),
        ({"indicatorsOfCompromise": None}, "unknown", None),
        ({"indicatorsOfCompromise": []}, "unknown", None),
        ({"indicatorsOfCompromise": {}}, "unknown", None),
        ({"indicatorsOfCompromise": {"mentions": None}}, "unknown", None),
        ({"indicatorsOfCompromise": {"mentions": "domain"}}, "unknown", None),
        ({"indicatorsOfCompromise": {"mentions": []}}, "not_reported", None),
        ({"indicatorsOfCompromise": {"mentions": [{}]}}, "unknown", 1),
        ({"indicatorsOfCompromise": {"mentions": [None]}}, "unknown", 1),
        ({"indicatorsOfCompromise": {"mentions": [{"type": "domain"}, "bad"]}}, "unknown", 2),
        ({"indicatorsOfCompromise": {"mentions": [{"type": "domain"}]}}, "present", 1),
        (
            {"indicatorsOfCompromise": {"mentions": [{"type": "hash"}, {"type": "hash"}]}},
            "present",
            2,
        ),
        (
            {"indicatorsOfCompromise": {"exports": [{"url": "https://example.test/export"}]}},
            "unknown",
            None,
        ),
    ],
)
def test_brief_ioc_states_share_human_interpretation_and_preserve_legacy_count(
    metadata, state, count
):
    article = {
        "id": "entry/ioc",
        "title": "Research",
        "canonicalUrl": "https://example.test/article",
        "summary": {"content": "<p>IoC https://example.test 192.0.2.1</p>"},
        **metadata,
    }
    original = copy.deepcopy(article)
    brief = output.brief(article)
    assert brief["iocStatus"] == state
    assert brief.get("iocCount") == count
    assert brief["id"] == article["id"] and brief["url"] == article["canonicalUrl"]
    label = {
        "unknown": "Unknown (Feedly IoC metadata unavailable)",
        "not_reported": "No IoCs reported by Feedly (not proof of absence)",
        "present": "Contains IoC",
    }[state]
    assert label in human([article])
    stream = StringIO()
    output.write_markdown([article], stream, include_content=False)
    assert label in stream.getvalue()
    assert article == original
    assert "iocStatus" not in output.add_markdown(article)


@pytest.mark.parametrize("wrapper", ["items", "entries", "results"])
def test_brief_states_preserve_wrappers_and_continuation(wrapper):
    value = {
        wrapper: [
            {"id": "positive", "indicatorsOfCompromise": {"mentions": [{"type": "domain"}]}},
            {"id": "empty", "indicatorsOfCompromise": {"mentions": []}},
            {"id": "absent"},
        ],
        "continuation": "opaque",
        "pages": 2,
    }
    result = output.brief(value)
    assert [item["iocStatus"] for item in result[wrapper]] == ["present", "not_reported", "unknown"]
    assert result["continuation"] == "opaque" and result["pages"] == 2
    assert output.brief(value[wrapper]) == result[wrapper]
    assert output.brief({wrapper: []}) == {wrapper: []}
