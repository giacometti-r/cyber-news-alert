from __future__ import annotations

import re
from dataclasses import dataclass

ORG_CUES = {
    "company": ["inc", "corp", "ltd", "llc", "plc", "company", "co."],
    "government": ["ministry", "department", "government", "city of", "state of", "agency"],
    "university": ["university", "college", "institute", "school"],
    "hospital": ["hospital", "health", "healthcare", "clinic", "medical center", "nhs"],
}

VICTIM_PATTERNS = [
    re.compile(r"\b(?:targeted|attacked|compromised|breached)\s+([A-Z][\w&.\- ]{2,80})", re.I),
    re.compile(r"\b([A-Z][\w&.\- ]{2,80})\s+(?:was|were)\s+(?:targeted|attacked|compromised|breached)", re.I),
    re.compile(r"\bagainst\s+([A-Z][\w&.\- ]{2,80})", re.I),
]

STOP_TOKENS = {"the", "a", "an", "this", "that", "these", "those", "phishing", "attack", "campaign"}


@dataclass(frozen=True)
class VictimResult:
    victim_name: str | None
    victim_category: str | None


class VictimExtractor:
    def extract(self, title: str, text: str) -> VictimResult:
        content = f"{title}. {text[:1500]}"

        for pattern in VICTIM_PATTERNS:
            match = pattern.search(content)
            if not match:
                continue

            raw = self._normalize_candidate(match.group(1))
            if not raw:
                continue

            category = self._classify_org(raw)
            if category:
                return VictimResult(raw, category)

        return VictimResult(None, None)

    def _normalize_candidate(self, raw: str) -> str | None:
        candidate = re.sub(r"\s+", " ", raw.strip(" .,:;|-"))
        if len(candidate) < 3:
            return None

        lowered = candidate.lower()
        if lowered in STOP_TOKENS:
            return None

        return candidate

    def _classify_org(self, name: str) -> str | None:
        low = name.lower()
        for category, cues in ORG_CUES.items():
            if any(cue in low for cue in cues):
                return category

        words = name.split()
        if len(words) >= 2 and all(word[:1].isupper() for word in words[:2]):
            return "company"

        return None
