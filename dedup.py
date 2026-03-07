"""Deduplicate articles by title similarity, tracking coverage count."""

from difflib import SequenceMatcher


def _similarity(a: str, b: str) -> float:
    """Return similarity ratio between two strings (0.0 to 1.0)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def deduplicate(articles: list[dict], threshold: float = 0.6) -> list[dict]:
    """Remove duplicate articles whose titles exceed *threshold* similarity.

    Each kept article gets:
    - ``coverage_count``: how many sources covered the same story
    - ``covered_by``: list of source names that covered it
    """
    unique: list[dict] = []

    for article in articles:
        merged = False
        for u in unique:
            if _similarity(article["title"], u["title"]) > threshold:
                # Same story — increment coverage on the kept article
                u["coverage_count"] += 1
                src = article.get("source", "")
                if src and src not in u["covered_by"]:
                    u["covered_by"].append(src)
                merged = True
                break

        if not merged:
            article["coverage_count"] = 1
            article["covered_by"] = [article.get("source", "")]
            unique.append(article)

    return unique
