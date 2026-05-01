from app.detection.attack_classifier import AttackClassifier


def test_detects_phishing_incident() -> None:
    classifier = AttackClassifier()
    result = classifier.classify(
        "Acme Corp attacked in phishing campaign",
        "Attackers targeted Acme Corp and stole credentials from employee inboxes.",
    )
    assert result.article_type == "incident"
    assert result.is_attack
    assert result.attack_type == "phishing"
    assert result.attack_confidence > 0.5
    assert result.incident_confidence > 0.5


def test_classifies_press_release() -> None:
    classifier = AttackClassifier()
    result = classifier.classify(
        "Sublime Security Launches Channel Partner Program",
        "PRNewswire press release announced the company launch and partner strategy.",
    )
    assert result.article_type == "press_release"
    assert not result.is_attack


def test_flags_out_of_taxonomy_incident() -> None:
    classifier = AttackClassifier()
    result = classifier.classify(
        "Stryker hit by data-wiping attack",
        "Investigators confirmed a wiper incident that disrupted operations at Stryker.",
    )
    assert result.article_type == "incident"
    assert result.attack_type is None
    assert "out-of-taxonomy" in result.reasons
