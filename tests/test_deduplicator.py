from app.dedup.deduplicator import build_fingerprint, build_incident_key, canonicalize_url


def test_canonicalize_url_removes_tracking() -> None:
    url = "https://example.com/path/?utm_source=x&id=10&utm_medium=y"
    assert canonicalize_url(url) == "https://example.com/path?id=10"


def test_fingerprint_is_stable_for_whitespace_changes() -> None:
    a = build_fingerprint("Title", "A lot of text here")
    b = build_fingerprint("Title", "A   lot\nof text here")
    assert a == b


def test_incident_key_is_stable_for_case_and_punctuation() -> None:
    a = build_incident_key("University of Cambridge", "Phishing")
    b = build_incident_key("university of cambridge!", "phishing")
    assert a == b
