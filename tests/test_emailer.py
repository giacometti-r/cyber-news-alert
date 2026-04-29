from app.alerts.emailer import Emailer


def _emailer() -> Emailer:
    return Emailer(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="u",
        smtp_password="p",
        sender_email="from@example.com",
        recipient_email="to@example.com",
    )


def test_company_subject_format() -> None:
    emailer = _emailer()
    subject = emailer.build_subject("Acme Corp", "company", "phishing")
    assert subject == "Acme Corp was attacked using phishing"


def test_non_company_subject_format() -> None:
    emailer = _emailer()
    subject = emailer.build_subject("Springfield University", "university", "vishing")
    assert subject == "[Springfield University] was attacked using vishing"


def test_body_contains_expected_fields() -> None:
    emailer = _emailer()
    body = emailer.build_body(
        abstract="Sentence one. Sentence two.",
        attack_type="phishing",
        victim_name="Acme Corp",
        victim_category="company",
        source_name="Example News",
        published_date="2026-04-29T00:00:00+00:00",
        link="https://example.com/article",
    )
    assert "Attack type: phishing" in body
    assert "Victim: Acme Corp" in body
    assert "Article link: https://example.com/article" in body
