from __future__ import annotations

import re
from dataclasses import dataclass


ATTACK_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "phishing": [re.compile(r"\bphishing\b", re.I)],
    "malvertising": [re.compile(r"\bmalvertising\b", re.I), re.compile(r"\bmalicious ads?\b", re.I)],
    "impersonation": [re.compile(r"\bimpersonat(?:ion|ing)\b", re.I)],
    "business email compromise": [re.compile(r"\b(BEC|business email compromise)\b", re.I)],
    "smishing": [re.compile(r"\bsmishing\b", re.I)],
    "vishing": [re.compile(r"\bvishing\b", re.I)],
    "fake updates": [re.compile(r"\bfake update(?:s)?\b", re.I)],
    "seo poisoning": [re.compile(r"\bSEO poisoning\b", re.I)],
    "watering hole": [re.compile(r"\bwatering hole\b", re.I)],
    "social media scams": [re.compile(r"\bsocial media scam\w*\b", re.I)],
    "credential theft": [re.compile(r"\bcredential(?:s)? theft\b", re.I), re.compile(r"\bstolen credentials?\b", re.I)],
}

INCIDENT_PATTERNS = [
    re.compile(r"\b(attacked|targeted|compromised|breach(?:ed)?|stolen|hijacked|defraud(?:ed)?)\b", re.I),
    re.compile(r"\b(campaign|incident|scam|intrusion)\b", re.I),
]

NEGATIVE_PATTERNS = [
    re.compile(r"\bhow to\b", re.I),
    re.compile(r"\bawareness\b", re.I),
    re.compile(r"\bbest practices\b", re.I),
    re.compile(r"\bwebinar\b", re.I),
    re.compile(r"\bproduct announcement\b", re.I),
    re.compile(r"\bpress release\b", re.I),
    re.compile(r"\bthreat report\b", re.I),
    re.compile(r"\bresearch report\b", re.I),
]


@dataclass(frozen=True)
class ClassificationResult:
    is_attack: bool
    attack_type: str | None
    reason: str


class AttackClassifier:
    def classify(self, title: str, text: str) -> ClassificationResult:
        content = f"{title}. {text}"

        attack_type = self._detect_attack_type(content)
        if not attack_type:
            return ClassificationResult(False, None, "no-attack-keyword")

        incident_score = sum(1 for p in INCIDENT_PATTERNS if p.search(content))
        if incident_score == 0:
            return ClassificationResult(False, attack_type, "missing-incident-language")

        negative_score = sum(1 for p in NEGATIVE_PATTERNS if p.search(content))
        if negative_score >= 2:
            return ClassificationResult(False, attack_type, "likely-generic-or-marketing")

        return ClassificationResult(True, attack_type, "qualified")

    def _detect_attack_type(self, content: str) -> str | None:
        for attack_type, patterns in ATTACK_PATTERNS.items():
            if any(pattern.search(content) for pattern in patterns):
                return attack_type
        return None
