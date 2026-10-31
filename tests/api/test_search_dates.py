import pytest

from feedly_cli.api.search_dates import (
    filter_search_dates,
    parse_search_date,
    validate_search_dates,
)
from feedly_cli.errors import FeedlyError


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-10-01", 1790812800000),
        ("2026-11-01", 1793491200000),
        ("2026-10-01T00:00:00Z", 1790812800000),
        ("2026-10-01T02:00:00+02:00", 1790812800000),
        ("2026-09-30T19:00:00-05:00", 1790812800000),
        ("2026-10-01T00:00:00.123Z", 1790812800123),
        ("2024-02-29", 1709164800000),
    ],
)
def test_search_date_parsing(value, expected):
    assert parse_search_date(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "2026-10",
        "2026-02-29",
        "2026-13-01",
        "20261001",
        "2026-10-01T00:00:00",
        "2026-10-01T00:00:00.000001Z",
        "2026-10-01 00:00:00Z",
        "2026-10-01T24:00:00Z",
        "not-a-date",
    ],
)
def test_invalid_search_dates(value):
    with pytest.raises(FeedlyError, match="Search dates must be"):
        parse_search_date(value)


@pytest.mark.parametrize(("since", "before"), [(2, 1), (1, 1)])
def test_invalid_date_order(since, before):
    with pytest.raises(FeedlyError, match="earlier"):
        validate_search_dates(since, before)


@pytest.mark.parametrize(("since", "before"), [(None, None), (1, None), (None, 2), (1, 2)])
def test_open_date_bounds(since, before):
    validate_search_dates(since, before)


def test_filter_exact_boundaries_preserves_envelope_and_input():
    page = {
        "items": [{"id": str(n), "published": n} for n in (9, 10, 19, 20)],
        "continuation": "next",
        "other": {"metadata": True},
    }
    result = filter_search_dates(page, 10, 20)
    assert [item["id"] for item in result["items"]] == ["10", "19"]
    assert len(page["items"]) == 4
    assert result["continuation"] == "next"
    assert result["other"] == page["other"]


@pytest.mark.parametrize("published", [None, "1790812800000", True, 1.5, {}])
def test_filter_missing_or_invalid_publication_dates_fails_explicitly(published):
    with pytest.raises(FeedlyError, match="no valid published"):
        filter_search_dates({"items": [{"published": published}]}, 10, 20)


@pytest.mark.parametrize("page", [None, [], {}, {"items": None}])
def test_filter_invalid_envelope_fails(page):
    with pytest.raises(FeedlyError, match="invalid page"):
        filter_search_dates(page, 10, 20)


def test_filter_empty_page_retains_continuation():
    assert filter_search_dates({"items": [{"published": 1}], "continuation": "next"}, 10, 20) == {
        "items": [],
        "continuation": "next",
    }
