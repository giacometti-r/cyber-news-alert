from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class SourceArticle:
    source_name: str
    source_type: str
    title: str
    url: str
    published_at: datetime | None


class NewsSource(Protocol):
    def fetch(self) -> list[SourceArticle]:
        ...
