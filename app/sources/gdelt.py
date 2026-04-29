from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus

import requests
from dateutil import parser as date_parser
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.sources.base import SourceArticle

logger = logging.getLogger(__name__)


class GdeltSource:
    def __init__(self, query: str, max_articles: int, timeout: int, timespan_minutes: int) -> None:
        self.query = query
        self.max_articles = max_articles
        self.timeout = timeout
        self.timespan_minutes = timespan_minutes

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(requests.RequestException),
    )
    def _fetch_json(self, url: str) -> dict[str, Any]:
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def fetch(self) -> list[SourceArticle]:
        query = quote_plus(self.query)
        url = (
            "https://api.gdeltproject.org/api/v2/doc/doc?"
            f"query={query}&mode=ArtList&maxrecords={self.max_articles}&format=json"
            "&sort=DateDesc"
            f"&timespan={self.timespan_minutes}min"
        )

        payload = self._fetch_json(url)
        articles_data = payload.get("articles", [])
        articles: list[SourceArticle] = []
        for item in articles_data:
            title = item.get("title")
            link = item.get("url")
            if not title or not link:
                continue

            published_at = None
            seen_date = item.get("seendate")
            if seen_date:
                try:
                    published_at = date_parser.parse(seen_date).astimezone(timezone.utc)
                except (ValueError, TypeError):
                    published_at = None

            articles.append(
                SourceArticle(
                    source_name="GDELT",
                    source_type="gdelt",
                    title=title,
                    url=link,
                    published_at=published_at,
                )
            )

        logger.info("Fetched %s GDELT entries", len(articles))
        return articles
