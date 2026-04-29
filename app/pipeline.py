from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.alerts.emailer import AlertEmail, Emailer
from app.db import Database
from app.dedup.deduplicator import build_content_hash, build_fingerprint, canonicalize_url
from app.detection.attack_classifier import AttackClassifier
from app.detection.victim_extractor import VictimExtractor
from app.fetch.article_fetcher import ArticleFetcher
from app.models import Alert, Article, ArticleFingerprint
from app.sources.base import SourceArticle

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineMetrics:
    processed: int = 0
    alerts_sent: int = 0
    skipped: int = 0
    errors: int = 0


class MonitorPipeline:
    def __init__(
        self,
        database: Database,
        fetcher: ArticleFetcher,
        classifier: AttackClassifier,
        victim_extractor: VictimExtractor,
        emailer: Emailer,
    ) -> None:
        self.database = database
        self.fetcher = fetcher
        self.classifier = classifier
        self.victim_extractor = victim_extractor
        self.emailer = emailer

    def run(self, articles: list[SourceArticle]) -> PipelineMetrics:
        metrics = PipelineMetrics()

        for item in articles:
            try:
                metrics = self._process_one(item, metrics)
            except Exception as exc:
                logger.exception("Unhandled processing failure url=%s error=%s", item.url, exc)
                metrics = PipelineMetrics(
                    processed=metrics.processed,
                    alerts_sent=metrics.alerts_sent,
                    skipped=metrics.skipped,
                    errors=metrics.errors + 1,
                )

        return metrics

    def _process_one(self, item: SourceArticle, metrics: PipelineMetrics) -> PipelineMetrics:
        canonical_url = canonicalize_url(item.url)

        with self.database.session() as session:
            existing = session.scalar(select(Article.id).where(Article.canonical_url == canonical_url))
            if existing:
                return PipelineMetrics(metrics.processed + 1, metrics.alerts_sent, metrics.skipped + 1, metrics.errors)

        content = self.fetcher.fetch(item.url)
        if not content:
            return PipelineMetrics(metrics.processed + 1, metrics.alerts_sent, metrics.skipped + 1, metrics.errors)

        classification = self.classifier.classify(item.title, content.full_text)
        if not classification.is_attack or not classification.attack_type:
            return PipelineMetrics(metrics.processed + 1, metrics.alerts_sent, metrics.skipped + 1, metrics.errors)

        victim = self.victim_extractor.extract(item.title, content.full_text)
        if not victim.victim_name or not victim.victim_category:
            return PipelineMetrics(metrics.processed + 1, metrics.alerts_sent, metrics.skipped + 1, metrics.errors)

        fingerprint = build_fingerprint(item.title, content.full_text)
        content_hash = build_content_hash(content.full_text)

        subject = self.emailer.build_subject(victim.victim_name, victim.victim_category, classification.attack_type)
        published = item.published_at.astimezone(timezone.utc).isoformat() if item.published_at else "unknown"
        body = self.emailer.build_body(
            abstract=content.abstract,
            attack_type=classification.attack_type,
            victim_name=victim.victim_name,
            victim_category=victim.victim_category,
            source_name=item.source_name,
            published_date=published,
            link=item.url,
        )

        article_id: int | None = None
        alert_id: int | None = None
        with self.database.session() as session:
            fp_exists = session.scalar(
                select(ArticleFingerprint.id).where(ArticleFingerprint.fingerprint == fingerprint)
            )
            if fp_exists:
                return PipelineMetrics(metrics.processed + 1, metrics.alerts_sent, metrics.skipped + 1, metrics.errors)

            try:
                article = Article(
                    source_name=item.source_name,
                    source_type=item.source_type,
                    title=item.title,
                    url=item.url,
                    canonical_url=canonical_url,
                    published_at=item.published_at,
                    article_text=content.full_text,
                    abstract=content.abstract,
                    attack_type=classification.attack_type,
                    victim_name=victim.victim_name,
                    victim_category=victim.victim_category,
                    content_hash=content_hash,
                )
                session.add(article)
                session.flush()

                session.add(ArticleFingerprint(article_id=article.id, fingerprint=fingerprint))

                alert = Alert(
                    article_id=article.id,
                    recipient_email=self.emailer.recipient_email,
                    subject=subject,
                    body=body,
                    status="pending",
                    error_message=None,
                )
                session.add(alert)
                session.flush()
                article_id = article.id
                alert_id = alert.id
            except IntegrityError:
                session.rollback()
                logger.info("Duplicate detected during insert, skipping url=%s", item.url)
                return PipelineMetrics(metrics.processed + 1, metrics.alerts_sent, metrics.skipped + 1, metrics.errors)

        send_status = "sent"
        send_error = None
        try:
            self.emailer.send(AlertEmail(subject=subject, body=body))
        except Exception as exc:
            logger.exception("Email sending failed url=%s error=%s", item.url, exc)
            send_status = "failed"
            send_error = str(exc)

        if alert_id is not None and article_id is not None:
            with self.database.session() as session:
                alert = session.scalar(select(Alert).where(Alert.id == alert_id, Alert.article_id == article_id))
                if alert is not None:
                    alert.status = send_status
                    alert.error_message = send_error

        sent_delta = 1 if send_status == "sent" else 0
        return PipelineMetrics(metrics.processed + 1, metrics.alerts_sent + sent_delta, metrics.skipped, metrics.errors)
