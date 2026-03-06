"""Deduplicate articles by title similarity."""

from difflib import SequenceMatcher


def _similarity(a: str, b: str) -> float:
    """Return similarity ratio between two strings (0.0 to 1.0)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def deduplicate(articles: list[dict], threshold: float = 0.6) -> list[dict]:
    """Remove duplicate articles whose titles exceed *threshold* similarity."""
    unique: list[dict] = []

    for article in articles:
        if any(_similarity(article["title"], u["title"]) > threshold for u in unique):
            continue
        unique.append(article)

    return unique
