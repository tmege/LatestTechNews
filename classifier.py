"""Classify articles into categories and diversify source selection."""

import re
import logging
from collections import defaultdict
from config import CATEGORIES, MAX_ARTICLES_PER_CATEGORY

log = logging.getLogger("technews")

_DEFAULT_CATEGORY = "tech-hardware"


def classify_article(article: dict) -> str:
    """Return the best-matching category and store keyword_score on the article."""
    text = f"{article['title']} {article['summary']}".lower()
    scores: dict[str, int] = {}

    for category, keywords in CATEGORIES.items():
        score = 0
        for keyword in keywords:
            pattern = re.escape(keyword.lower())
            if len(keyword) <= 3:
                pattern = rf"\b{pattern}\b"
            if re.search(pattern, text):
                score += 1
        scores[category] = score

    best_score = max(scores.values())
    article["keyword_score"] = best_score

    if best_score == 0:
        return _DEFAULT_CATEGORY

    return max(scores, key=scores.get)


def _diversify(articles: list[dict]) -> list[dict]:
    """Select the best articles while ensuring source diversity.

    If there are more articles than MAX_ARTICLES_PER_CATEGORY, we pick
    them via round-robin across sources so no single outlet dominates.
    If there are fewer, we keep them all — never discard relevant articles.
    """
    if len(articles) <= MAX_ARTICLES_PER_CATEGORY:
        return articles

    # Group by source, preserving order (newest first)
    by_source: dict[str, list[dict]] = defaultdict(list)
    for article in articles:
        by_source[article["source"]].append(article)

    # Round-robin: pick 1 from each source per pass until we hit the limit
    selected: list[dict] = []
    pick_round = 0

    while len(selected) < MAX_ARTICLES_PER_CATEGORY:
        added_this_round = False
        for source, source_articles in by_source.items():
            if pick_round < len(source_articles):
                selected.append(source_articles[pick_round])
                added_this_round = True
                if len(selected) >= MAX_ARTICLES_PER_CATEGORY:
                    break
        if not added_this_round:
            break
        pick_round += 1

    # Sort final selection by date (newest first)
    selected.sort(key=lambda a: a["published"], reverse=True)
    return selected


def classify_articles(articles: list[dict]) -> dict[str, list[dict]]:
    """Group articles by category with source diversity."""
    grouped: dict[str, list[dict]] = {cat: [] for cat in CATEGORIES}

    for article in articles:
        category = classify_article(article)
        grouped[category].append(article)

    # Apply diversity only when we need to cut down
    for cat in grouped:
        grouped[cat] = _diversify(grouped[cat])

    return grouped
