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
NOISE_SENTENCE_RE = re.compile(
    (
        r"\b(menu|news search|share on|write for us|comment|features|lifestyle|fashion|film|"
        r"whatsapp|linkedin|advertisement|subscribe|cookie policy|privacy policy|follow us)\b"
    ),
    re.I,
)
BOILERPLATE_ATTR_RE = re.compile(
    r"(nav|menu|header|footer|promo|advert|ad-|share|social|cookie|newsletter|subscribe)",
    re.I,
)


@dataclass(frozen=True)
class ArticleContent:
    full_text: str
    abstract: str


class ArticleFetcher:
    def __init__(self, timeout_seconds: int, abstract_max_chars: int = 420) -> None:
        self.timeout_seconds = timeout_seconds
        self.abstract_max_chars = abstract_max_chars
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

        soup = BeautifulSoup(html, "html.parser")
        text = self._extract_text(soup)
        if not text:
            return None

        metadata_abstract = self._extract_metadata_abstract(soup)
        abstract = self._extract_abstract(text, metadata_abstract=metadata_abstract)
        if not abstract:
            return None

        return ArticleContent(full_text=text, abstract=abstract)

    def _extract_text(self, soup: BeautifulSoup) -> str:
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "form", "aside"]):
            tag.decompose()

        for node in soup.find_all(True):
            attrs_obj = getattr(node, "attrs", None)
            if not isinstance(attrs_obj, dict):
                continue

            node_id = attrs_obj.get("id") or ""
            class_value = attrs_obj.get("class")
            class_names = " ".join(class_value) if isinstance(class_value, list) else ""
            attrs = " ".join(
                [
                    node_id,
                    class_names,
                ]
            )
            if BOILERPLATE_ATTR_RE.search(attrs):
                node.decompose()

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
        normalized = re.sub(r"\bAdvertisement\b", "", normalized, flags=re.I)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _extract_metadata_abstract(self, soup: BeautifulSoup) -> str:
        for key, value in (
            ("property", "og:description"),
            ("name", "description"),
        ):
            tag = soup.find("meta", attrs={key: value})
            if tag and tag.get("content"):
                content = re.sub(r"\s+", " ", str(tag["content"]).strip())
                if len(content) >= 50 and not self._is_noisy_sentence(content):
                    return content
        return ""

    def _extract_abstract(self, text: str, metadata_abstract: str = "", max_sentences: int = 3) -> str:
        sentences = SENTENCE_SPLIT_RE.split(text)
        kept: list[str] = []

        for sentence in sentences:
            candidate = sentence.strip()
            if len(candidate) < 40:
                continue
            if not MEANINGFUL_SENTENCE_RE.search(candidate):
                continue
            if self._is_noisy_sentence(candidate):
                continue
            if not self._has_alpha_density(candidate):
                continue
            kept.append(candidate)
            if len(kept) >= max_sentences:
                break

        abstract = " ".join(kept)
        if not abstract and metadata_abstract:
            abstract = metadata_abstract
        if len(abstract) <= self.abstract_max_chars:
            return abstract
        return self._clip_sentence_boundary(abstract, self.abstract_max_chars)

    def _is_noisy_sentence(self, sentence: str) -> bool:
        if NOISE_SENTENCE_RE.search(sentence):
            return True
        if sentence.count("|") >= 2:
            return True
        if sentence.count(" 20") >= 3:
            return True
        if sentence.count(",") > 8:
            return True
        return False

    def _has_alpha_density(self, sentence: str) -> bool:
        letters = sum(1 for ch in sentence if ch.isalpha())
        total = max(len(sentence), 1)
        return (letters / total) >= 0.55

    def _clip_sentence_boundary(self, text: str, max_chars: int) -> str:
        sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]
        kept: list[str] = []
        for sentence in sentences:
            candidate = " ".join(kept + [sentence]).strip()
            if len(candidate) <= max_chars:
                kept.append(sentence)
                continue
            break
        if kept:
            result = " ".join(kept).strip()
            return result if result.endswith((".", "!", "?")) else f"{result}."

        for sentence in sentences:
            if len(sentence) <= max_chars:
                return sentence if sentence.endswith((".", "!", "?")) else f"{sentence}."

        clipped = text[:max_chars].rstrip()
        last_space = clipped.rfind(" ")
        if last_space >= 40:
            clipped = clipped[:last_space]
        return clipped
