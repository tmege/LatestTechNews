"""Classify articles into categories based on keyword matching."""

import re
import logging
from config import CATEGORIES

log = logging.getLogger("technews")

# Default category for unclassified articles
_DEFAULT_CATEGORY = "tech-hardware"


def classify_article(article: dict) -> str:
    """Return the best-matching category for an article."""
    text = f"{article['title']} {article['summary']}".lower()
    scores: dict[str, int] = {}

    for category, keywords in CATEGORIES.items():
        score = 0
        for keyword in keywords:
            pattern = re.escape(keyword.lower())
            # Word-boundary match for short keywords to avoid false positives
            if len(keyword) <= 3:
                pattern = rf"\b{pattern}\b"
            if re.search(pattern, text):
                score += 1
        scores[category] = score

    if max(scores.values()) == 0:
        return _DEFAULT_CATEGORY

    return max(scores, key=scores.get)


def classify_articles(articles: list[dict]) -> dict[str, list[dict]]:
    """Group articles by category."""
    grouped: dict[str, list[dict]] = {cat: [] for cat in CATEGORIES}

    for article in articles:
        category = classify_article(article)
        grouped[category].append(article)

    return grouped
