from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select

from app.alerts.emailer import AlertEmail
from app.config import Settings
from app.db import Database
from app.fetch.article_fetcher import ArticleContent
from app.models import Alert
from app.pipeline import MonitorPipeline
from app.schema_init import initialize_schema
from app.sources.base import SourceArticle


class FakeFetcher:
    def __init__(self, content: ArticleContent) -> None:
        self.content = content

    def fetch(self, url: str) -> ArticleContent | None:
        return self.content


class FakeClassifier:
    @dataclass(frozen=True)
    class Result:
        is_attack: bool
        attack_type: str | None
        reason: str

    def classify(self, title: str, text: str) -> Result:
        return self.Result(is_attack=True, attack_type="phishing", reason="qualified")


class FakeVictimExtractor:
    @dataclass(frozen=True)
    class Result:
        victim_name: str | None
        victim_category: str | None

    def extract(self, title: str, text: str) -> Result:
        return self.Result(victim_name="Acme Corp", victim_category="company")


class FakeEmailer:
    recipient_email = "to@example.com"

    def __init__(self) -> None:
        self.sent: list[AlertEmail] = []

    def build_subject(self, victim_name: str, victim_category: str, attack_type: str) -> str:
        return f"{victim_name} was attacked using {attack_type}"

    def build_body(self, **kwargs: str) -> str:
        return f"body:{kwargs['attack_type']}:{kwargs['victim_name']}"

    def send(self, email: AlertEmail) -> None:
        self.sent.append(email)


class FailingEmailer(FakeEmailer):
    def send(self, email: AlertEmail) -> None:
        raise RuntimeError("smtp down")


def _settings(db_url: str) -> Settings:
    return Settings(
        smtp_host="smtp",
        smtp_port=587,
        smtp_username="u",
        smtp_password="p",
        sender_email="from@example.com",
        recipient_email="to@example.com",
        database_url=db_url,
        log_level="INFO",
        request_timeout_seconds=5,
        max_articles_per_source=10,
        enable_gdelt=False,
        gdelt_query_window_minutes=180,
        rss_feeds=[],
        google_news_queries=[],
    )


def test_pipeline_sends_once_for_duplicates() -> None:
    database = Database(_settings("sqlite+pysqlite:///:memory:"))
    initialize_schema(database)

    fetcher = FakeFetcher(ArticleContent(full_text="attack text", abstract="first sentence. second sentence."))
    emailer = FakeEmailer()
    pipeline = MonitorPipeline(
        database=database,
        fetcher=fetcher,
        classifier=FakeClassifier(),
        victim_extractor=FakeVictimExtractor(),
        emailer=emailer,
    )

    articles = [
        SourceArticle(
            source_name="s1",
            source_type="rss",
            title="Acme Corp attacked in phishing",
            url="https://example.com/article?utm_source=news",
            published_at=datetime.now(timezone.utc),
        ),
        SourceArticle(
            source_name="s2",
            source_type="rss",
            title="Acme Corp attacked in phishing",
            url="https://example.com/article",
            published_at=datetime.now(timezone.utc),
        ),
    ]

    metrics = pipeline.run(articles)
    assert metrics.alerts_sent == 1
    assert len(emailer.sent) == 1
    assert metrics.errors == 0

    with database.session() as session:
        alert = session.scalar(select(Alert))
        assert alert is not None
        assert alert.status == "sent"
        assert alert.error_message is None


def test_pipeline_marks_alert_failed_when_email_send_fails() -> None:
    database = Database(_settings("sqlite+pysqlite:///:memory:"))
    initialize_schema(database)

    fetcher = FakeFetcher(ArticleContent(full_text="attack text", abstract="first sentence. second sentence."))
    emailer = FailingEmailer()
    pipeline = MonitorPipeline(
        database=database,
        fetcher=fetcher,
        classifier=FakeClassifier(),
        victim_extractor=FakeVictimExtractor(),
        emailer=emailer,
    )

    article = SourceArticle(
        source_name="s1",
        source_type="rss",
        title="Acme Corp attacked in phishing",
        url="https://example.com/article",
        published_at=datetime.now(timezone.utc),
    )

    metrics = pipeline.run([article])
    assert metrics.alerts_sent == 0
    assert metrics.errors == 0
    assert len(emailer.sent) == 0

    with database.session() as session:
        alert = session.scalar(select(Alert))
        assert alert is not None
        assert alert.status == "failed"
        assert "smtp down" in (alert.error_message or "")
