from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from html import unescape

import requests
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
MEANINGFUL_SENTENCE_RE = re.compile(r"[A-Za-z]{3,}")


@dataclass(frozen=True)
class ArticleContent:
    full_text: str
    abstract: str


class ArticleFetcher:
    def __init__(self, timeout_seconds: int) -> None:
        self.timeout_seconds = timeout_seconds
        self.user_agent = "CyberNewsAlert/1.0 (+https://example.local)"

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(requests.RequestException),
    )
    def _download(self, url: str) -> str:
        response = requests.get(
            url,
            timeout=self.timeout_seconds,
            headers={"User-Agent": self.user_agent},
        )
        response.raise_for_status()
        return response.text

    def fetch(self, url: str) -> ArticleContent | None:
        try:
            html = self._download(url)
        except requests.RequestException as exc:
            logger.warning("Failed to fetch article url=%s error=%s", url, exc)
            return None

        text = self._extract_text(html)
        if not text:
            return None

        abstract = self._extract_abstract(text)
        if not abstract:
            return None

        return ArticleContent(full_text=text, abstract=abstract)

    def _extract_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "form"]):
            tag.decompose()

        candidates = []
        for selector in ["article", "main", "div[itemprop='articleBody']", "body"]:
            for node in soup.select(selector):
                text = node.get_text(" ", strip=True)
                if len(text) > 400:
                    candidates.append(text)

        if not candidates:
            candidates = [soup.get_text(" ", strip=True)]

        longest = max(candidates, key=len, default="")
        normalized = re.sub(r"\s+", " ", unescape(longest)).strip()
        return normalized

    def _extract_abstract(self, text: str, max_sentences: int = 3) -> str:
        sentences = SENTENCE_SPLIT_RE.split(text)
        kept: list[str] = []

        for sentence in sentences:
            candidate = sentence.strip()
            if len(candidate) < 40:
                continue
            if not MEANINGFUL_SENTENCE_RE.search(candidate):
                continue
            kept.append(candidate)
            if len(kept) >= max_sentences:
                break

        return " ".join(kept)
