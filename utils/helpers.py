from __future__ import annotations

import re
from collections import Counter
from functools import lru_cache


STOPWORDS = {
    "a",
    "about",
    "across",
    "after",
    "all",
    "also",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "but",
    "by",
    "can",
    "clear",
    "company",
    "could",
    "data",
    "details",
    "do",
    "early",
    "experience",
    "for",
    "from",
    "get",
    "have",
    "help",
    "if",
    "in",
    "including",
    "into",
    "is",
    "it",
    "its",
    "job",
    "join",
    "looking",
    "more",
    "must",
    "need",
    "of",
    "on",
    "or",
    "our",
    "role",
    "skills",
    "strong",
    "team",
    "that",
    "the",
    "their",
    "them",
    "this",
    "to",
    "using",
    "we",
    "well",
    "what",
    "when",
    "who",
    "will",
    "with",
    "work",
    "you",
    "your",
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_token(token: str) -> str:
    return re.sub(r"[^a-z0-9\+#/]+", "", token.lower())


@lru_cache(maxsize=256)
def extract_keywords(text: str, limit: int = 20) -> tuple[str, ...]:
    tokens = re.findall(r"\b[a-zA-Z][a-zA-Z0-9\-/+#]{2,}\b", text.lower())
    filtered = [token for token in tokens if token not in STOPWORDS and not token.isdigit()]
    counts = Counter(filtered)
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    keywords = [word for word, _count in ordered[:limit]]
    return tuple(keywords)


def split_sentences(text: str) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [part.strip(" -") for part in parts if part.strip()]


def parse_years_requirement(text: str) -> int | None:
    matches = re.findall(r"(\d+)\s*(?:\+|plus)?(?:\s*-\s*(\d+))?\s+years?", text.lower())
    if not matches:
        return None
    years = []
    for start, end in matches:
        years.append(int(end or start))
    return max(years) if years else None


def contains_any(text: str, phrases: list[str]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)
