from .helpers import human


def test_human_profile_is_detail_not_article():
    text = human(
        {"id": "user", "email": "person@example.test", "enterpriseName": "Example"}, "profile"
    )
    assert "person@example.test" in text
    assert "Example" in text
    assert "Articles" not in text


def test_actual_feed_alerts_scope_shape():
    text = human(
        {
            "enterpriseAlerts": [{"id": "enterprise-feed", "label": "Team feed"}],
            "userAlerts": [{"id": "user-feed", "label": "Personal feed"}],
        },
        "feeds",
        "list",
    )
    for part in ["enterprise-feed", "Team feed", "user-feed", "Personal feed"]:
        assert part in text
    assert "enterprise" in text.lower() and "user" in text.lower()


def test_mutation_confirmation_uses_cli_context():
    text = human(
        None, "boards", "add-url", context={"id": "board-id", "url": "https://example.test/article"}
    )
    assert "board-id" in text
    assert "https://example.test/article" in text
    assert "Added" in text
