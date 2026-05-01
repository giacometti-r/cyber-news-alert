from app.detection.victim_extractor import VictimExtractor


def test_extracts_company_victim() -> None:
    extractor = VictimExtractor()
    result = extractor.extract(
        "Northwind Inc was targeted in a BEC attack",
        "Investigators said Northwind Inc was compromised after an impersonation campaign.",
    )
    assert result.victim_name is not None
    assert "Northwind" in result.victim_name
    assert result.victim_category == "company"
    assert result.confidence >= 0.65


def test_extracts_hospital_victim() -> None:
    extractor = VictimExtractor()
    result = extractor.extract(
        "Attackers breached Riverside Hospital",
        "The phishing attack targeted Riverside Hospital IT staff.",
    )
    assert result.victim_name is not None
    assert "Riverside Hospital" in result.victim_name
    assert result.victim_category == "hospital"
    assert result.confidence >= 0.65


def test_extracts_targeting_pattern_from_title() -> None:
    extractor = VictimExtractor()
    result = extractor.extract(
        "Signal phishing attack targeting University of Cambridge",
        "Officials said attackers sent malicious messages.",
    )
    assert result.victim_name == "University of Cambridge"
    assert result.reason == "matched_title"


def test_rejects_noisy_google_news_style_victim_candidate() -> None:
    extractor = VictimExtractor()
    result = extractor.extract(
        "German prosecutors investigate Signal phishing attack",
        (
            "News Search Thoughts About Write English English Українська 日本語 30 apr 2026 "
            "German prosecutors investigate Signal phishing attack that targeted government officials."
        ),
    )
    assert result.victim_name is None
    assert result.victim_category is None
    assert result.confidence == 0.0
    assert result.reason in {"generic_entity", "noisy_candidate", "no_named_org"}
