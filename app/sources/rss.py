from __future__ import annotations

import logging
from datetime import datetime, timezone

import feedparser

from app.sources.base import SourceArticle

logger = logging.getLogger(__name__)


class RssSource:
    def __init__(self, feed_url: str, max_articles: int) -> None:
        self.feed_url = feed_url
        self.max_articles = max_articles

    def fetch(self) -> list[SourceArticle]:
        parsed = feedparser.parse(self.feed_url)
        source_name = parsed.feed.get("title", self.feed_url)

        articles: list[SourceArticle] = []
        for entry in parsed.entries[: self.max_articles]:
            link = entry.get("link")
            title = entry.get("title")
            if not link or not title:
                continue

            published_at = None
            published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
            if published_parsed:
                published_at = datetime(*published_parsed[:6], tzinfo=timezone.utc)

            articles.append(
                SourceArticle(
                    source_name=source_name,
                    source_type="rss",
                    title=title,
                    url=link,
                    published_at=published_at,
                )
            )

        logger.info("Fetched %s RSS entries from %s", len(articles), self.feed_url)
        return articles
