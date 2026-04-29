from app.detection.attack_classifier import AttackClassifier


def test_detects_phishing_incident() -> None:
    classifier = AttackClassifier()
    result = classifier.classify(
        "Acme Corp attacked in phishing campaign",
        "Attackers targeted Acme Corp and stole credentials from employee inboxes.",
    )
    assert result.is_attack
    assert result.attack_type == "phishing"


def test_rejects_awareness_article() -> None:
    classifier = AttackClassifier()
    result = classifier.classify(
        "How to prevent phishing at your company",
        "This awareness webinar covers best practices and product announcement details.",
    )
    assert not result.is_attack
