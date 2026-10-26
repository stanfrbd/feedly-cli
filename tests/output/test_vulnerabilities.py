from .helpers import human


def test_actual_trending_memes_shape():
    text = human(
        {
            "language": "en",
            "memes": [
                {
                    "label": "CVE-2026-1234",
                    "id": "topic/unfriendly-uuid",
                    "vulnerabilitiesMetadata": {"cvss": 9.8},
                    "summary": ["Example issue"],
                }
            ],
            "version": 1,
        },
        "cves",
        "trending",
    )
    assert "CVE-2026-1234" in text
