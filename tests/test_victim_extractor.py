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


def test_extracts_hospital_victim() -> None:
    extractor = VictimExtractor()
    result = extractor.extract(
        "Attackers breached Riverside Hospital",
        "The phishing attack targeted Riverside Hospital IT staff.",
    )
    assert result.victim_name is not None
    assert "Riverside Hospital" in result.victim_name
    assert result.victim_category == "hospital"
