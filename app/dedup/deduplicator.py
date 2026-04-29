from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_QUERY_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
}


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    path = re.sub(r"/+", "/", parsed.path or "/")
    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=False)
        if k.lower() not in TRACKING_QUERY_PARAMS
    ]
    query = urlencode(sorted(query_pairs))

    canonical = urlunparse(
        (
            parsed.scheme.lower() or "https",
            parsed.netloc.lower(),
            path.rstrip("/") or "/",
            "",
            query,
            "",
        )
    )
    return canonical


def _normalize_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.lower()).strip()
    return cleaned


def build_fingerprint(title: str, text: str) -> str:
    normalized = _normalize_text(f"{title} {text[:3000]}")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_content_hash(text: str) -> str:
    normalized = _normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
