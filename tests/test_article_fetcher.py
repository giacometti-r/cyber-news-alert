from bs4 import BeautifulSoup

from app.fetch.article_fetcher import ArticleFetcher


def test_extract_abstract_filters_navigation_noise() -> None:
    fetcher = ArticleFetcher(timeout_seconds=5, abstract_max_chars=420)
    text = (
        "Menu News Comment Features Interviews Science Lifestyle Share on Twitter Share on WhatsApp. "
        "Since last week, students and staff at the University of Cambridge reported phishing emails "
        "sent from compromised university member accounts. "
        "The campaign requested gift-card shipping fees and administrators warned recipients not to pay. "
        "Write for us and follow our channels for more updates."
    )
    abstract = fetcher._extract_abstract(text)
    assert "Menu News Comment" not in abstract
    assert "Share on WhatsApp" not in abstract
    assert "University of Cambridge reported phishing emails" in abstract


def test_extract_abstract_clips_to_max_chars() -> None:
    fetcher = ArticleFetcher(timeout_seconds=5, abstract_max_chars=120)
    text = (
        "Investigators said Acme Corp was attacked in a phishing campaign that stole employee credentials "
        "and enabled mailbox access across several departments. "
        "The incident response team reset accounts and blocked malicious domains."
    )
    abstract = fetcher._extract_abstract(text)
    assert len(abstract) <= 120
    assert abstract.endswith(".")


def test_extract_abstract_uses_metadata_fallback_when_text_is_noisy() -> None:
    fetcher = ArticleFetcher(timeout_seconds=5, abstract_max_chars=180)
    text = "Menu Share on WhatsApp. Advertisement. Follow us. Subscribe."
    abstract = fetcher._extract_abstract(
        text,
        metadata_abstract="Researchers reported a phishing campaign targeting multiple organizations.",
    )
    assert "phishing campaign" in abstract


def test_extract_text_handles_tag_with_missing_attrs_dict() -> None:
    fetcher = ArticleFetcher(timeout_seconds=5, abstract_max_chars=180)
    soup = BeautifulSoup(
        "<html><body><article><p>Acme Corp was attacked in a phishing incident impacting employees.</p></article></body></html>",
        "html.parser",
    )
    tag = soup.find("article")
    assert tag is not None
    tag.attrs = None  # Simulate malformed tag state seen in production pages.

    text = fetcher._extract_text(soup)
    assert "Acme Corp was attacked in a phishing incident" in text
