import ssl

from app.alerts.emailer import AlertEmail, DigestEmailItem, Emailer


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


def test_subject_is_normalized_when_victim_name_is_noisy() -> None:
    emailer = _emailer()
    subject = emailer.build_subject(
        "   government officials - mezha.net. News Search Thoughts About Write English Englis   ",
        "government",
        "phishing",
    )
    assert "\n" not in subject
    assert "  " not in subject


def test_body_abstract_is_compacted() -> None:
    emailer = _emailer()
    body = emailer.build_body(
        abstract="  Sentence one.\n\nSentence two.  ",
        attack_type="phishing",
        victim_name="Unknown organization",
        victim_category="company",
        source_name="Example News",
        published_date="2026-04-29T00:00:00+00:00",
        link="https://example.com/article",
    )
    assert "Abstract:\nSentence one. Sentence two." in body


def test_digest_body_groups_items_by_reason() -> None:
    emailer = _emailer()
    body = emailer.build_digest_body(
        [
            DigestEmailItem(
                title="Story A",
                source_name="Source 1",
                routing_reason="campaign_report",
                link="https://example.com/a",
                published_date="2026-04-29T00:00:00+00:00",
                attack_type="phishing",
                victim_name=None,
            ),
            DigestEmailItem(
                title="Story B",
                source_name="Source 2",
                routing_reason="campaign_report",
                link="https://example.com/b",
                published_date="2026-04-29T00:00:00+00:00",
                attack_type=None,
                victim_name="Acme Corp",
            ),
        ]
    )
    assert "Reason: campaign_report (2)" in body
    assert "Story A" in body
    assert "Story B" in body


def test_send_uses_verifying_tls_context(monkeypatch: object) -> None:
    captured: dict[str, object] = {}

    class FakeSmtp:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            captured["host"] = host
            captured["port"] = port
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            del exc_type, exc, tb
            return False

        def starttls(self, context: ssl.SSLContext | None = None) -> None:
            captured["context"] = context

        def login(self, username: str, password: str) -> None:
            captured["login"] = (username, password)

        def send_message(self, msg: object) -> None:
            captured["message"] = msg

    monkeypatch.setattr("app.alerts.emailer.smtplib.SMTP", FakeSmtp)

    emailer = _emailer()
    emailer.send(AlertEmail(subject="Subject", body="Body"))

    context = captured.get("context")
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
