"""Relevance scoring engine and scored-article storage."""

import json
import math
import logging
from datetime import datetime, timezone, timedelta
from config import (
    SOURCE_CREDIBILITY,
    SCORED_ARTICLES_FILE,
    SCORED_ARTICLES_RETENTION_HOURS,
)

log = logging.getLogger("technews")

# ---------------------------------------------------------------------------
# Score weights
# ---------------------------------------------------------------------------
W_COVERAGE = 0.35
W_HN = 0.25
W_KEYWORD = 0.20
W_CREDIBILITY = 0.10
W_RECENCY = 0.10

# Normalisation caps (avoid one outlier dominating)
_MAX_COVERAGE = 5
_MAX_HN_POINTS = 500
_MAX_KEYWORD_SCORE = 10


def _get_credibility(source_name: str) -> float:
    """Return credibility score for a source (substring match, case-insensitive)."""
    name_lower = source_name.lower()
    for key, score in SOURCE_CREDIBILITY.items():
        if key in name_lower:
            return score
    return 0.5  # unknown source default


def _recency_factor(published: datetime, now: datetime | None = None) -> float:
    """Exponential decay: 1.0 if just published, ~0.3 after 24h."""
    now = now or datetime.now(timezone.utc)
    age_hours = max((now - published).total_seconds() / 3600, 0)
    return math.exp(-0.05 * age_hours)


def calculate_scores(articles: list[dict]) -> list[dict]:
    """Compute and attach ``relevance_score`` to each article."""
    now = datetime.now(timezone.utc)

    for a in articles:
        coverage = min(a.get("coverage_count", 1), _MAX_COVERAGE) / _MAX_COVERAGE
        hn = min(a.get("hn_points", 0), _MAX_HN_POINTS) / _MAX_HN_POINTS
        keyword = min(a.get("keyword_score", 0), _MAX_KEYWORD_SCORE) / _MAX_KEYWORD_SCORE
        credibility = _get_credibility(a.get("source", ""))
        recency = _recency_factor(a["published"], now)

        a["relevance_score"] = round(
            W_COVERAGE * coverage
            + W_HN * hn
            + W_KEYWORD * keyword
            + W_CREDIBILITY * credibility
            + W_RECENCY * recency,
            4,
        )

    return articles


# ---------------------------------------------------------------------------
# Persistence — JSON array with rolling retention
# ---------------------------------------------------------------------------

def _serialize_article(article: dict) -> dict:
    """Convert an article dict to a JSON-safe format."""
    d = {}
    for key, val in article.items():
        if isinstance(val, datetime):
            d[key] = val.isoformat()
        else:
            d[key] = val
    d["stored_at"] = datetime.now(timezone.utc).isoformat()
    return d


def _load_scored() -> list[dict]:
    """Load the scored articles database."""
    if not SCORED_ARTICLES_FILE.exists():
        return []
    try:
        return json.loads(SCORED_ARTICLES_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        log.warning("Corrupted scored articles file, starting fresh.")
        return []


def store_scored_articles(articles: list[dict]) -> None:
    """Append scored articles to the database and purge old entries."""
    existing = _load_scored()

    # Deduplicate by link (keep newer entry)
    seen_links = {a["link"] for a in articles}
    existing = [a for a in existing if a["link"] not in seen_links]

    existing.extend(_serialize_article(a) for a in articles)

    # Purge entries older than retention window
    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(hours=SCORED_ARTICLES_RETENTION_HOURS)
    ).isoformat()
    existing = [a for a in existing if a.get("stored_at", "") > cutoff]

    SCORED_ARTICLES_FILE.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
    log.info("Scored articles DB: %d entries.", len(existing))


def load_top_articles(hours: int = 24, limit: int = 20) -> list[dict]:
    """Load the top-scored articles from the last *hours* hours."""
    all_articles = _load_scored()

    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=hours)
    ).isoformat()

    recent = [a for a in all_articles if a.get("stored_at", "") > cutoff]

    # Filter out articles with no usable summary (paywalled)
    recent = [
        a for a in recent
        if (a.get("ai_summary") or a.get("summary", "")).strip()
    ]

    # Sort by relevance score (descending), then by stored_at (newest first)
    recent.sort(key=lambda a: (a.get("relevance_score", 0), a.get("stored_at", "")), reverse=True)

    return recent[:limit]
