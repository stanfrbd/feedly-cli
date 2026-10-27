import pytest

from feedly_cli.output.vulnerabilities import cvss_text

from .helpers import human


def test_actual_trending_memes_shape():
    text = human(
        {
            "language": "en",
            "memes": [
                {
                    "label": "CVE-2026-1234",
                    "id": "topic/unfriendly-uuid",
                    "score": 13.27,
                    "vulnerabilitiesMetadata": {"cvss": 9.8, "hasExploit": True},
                    "summary": ["Example issue"],
                }
            ],
            "version": 1,
        },
        "cves",
        "trending",
    )
    assert "CVE-2026-1234" in text
    assert "9.8" in text and "exploit" in text and "Example issue" in text
    assert "13.27" not in text and '["' not in text


CVE_ENTITY = {
    "cveid": "CVE-2026-1234",
    "id": "vulnerability/m/entity/CVE-2026-1234",
    "hasSalience": True,
    "cvssV3": {"baseScore": 9.8, "vectorString": "CVSS:3.1/AV:N"},
    "cvssV4": {"baseScore": 9.2},
    "cvssCategoryEstimate": "HIGH",
    "epssScore": "0.99",
    "patched": True,
    "exploits": ["https://example.com/poc"],
    "cweIds": [{"cweID": "CWE-416", "name": "Use After Free"}],
    "affectedProductsEstimate": [{"vendor": "php", "products": [{"name": "php"}]}],
    "publishedDate": "2026-10-21T14:00:00+00:00",
    "whatSoWhat": {"what": "Memory bug", "soWhat": "Exploited in the wild"},
    "description": "Long description",
}


@pytest.mark.parametrize("command", ["cve", "cves"])
def test_cve_entity_is_a_readable_summary_not_a_raw_dump(command):
    value = CVE_ENTITY if command == "cve" else [CVE_ENTITY]
    text = human(value, command, None if command == "cve" else "get")
    assert text.startswith("CVE-2026-1234\n")
    for expected in (
        "CVSS: v3 9.8, v4 9.2 (HIGH)",
        "EPSS: 0.99",
        "Flags: exploit, patched",
        "Weakness: CWE-416",
        "Vendors / products: php (php)",
        "Public exploits: 1",
        "So what: Exploited in the wild",
    ):
        assert expected in text
    assert "Cvssv3" not in text and "vectorString" not in text


def test_cvss_text_without_scores_is_empty():
    assert cvss_text({}) == ""
