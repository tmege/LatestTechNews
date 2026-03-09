"""Track posted articles to avoid duplicates across runs."""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

log = logging.getLogger("technews")

_HISTORY_FILE = Path(__file__).parent / ".history.json"
_RETENTION_DAYS = 7  # purge entries older than this


def _load() -> dict[str, str]:
    """Load history: {link: iso_timestamp} with validation."""
    if not _HISTORY_FILE.exists():
        return {}
    try:
        data = json.loads(_HISTORY_FILE.read_text())
        if not isinstance(data, dict):
            log.warning("Invalid history format, starting fresh.")
            return {}
        return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str)}
    except (json.JSONDecodeError, OSError):
        log.warning("Corrupted history file, starting fresh.")
        return {}


def _save(history: dict[str, str]) -> None:
    """Save history to disk."""
    _HISTORY_FILE.write_text(json.dumps(history, indent=2))


def filter_already_posted(articles: list[dict]) -> list[dict]:
    """Remove articles that were already posted in a previous run."""
    history = _load()
    new_articles = []

    for article in articles:
        if article["link"] not in history:
            new_articles.append(article)

    skipped = len(articles) - len(new_articles)
    if skipped:
        log.info("Skipped %d already-posted articles.", skipped)

    return new_articles


def mark_as_posted(articles: list[dict]) -> None:
    """Record articles as posted so they won't be sent again."""
    history = _load()
    now = datetime.now(timezone.utc).isoformat()

    for article in articles:
        history[article["link"]] = now

    # Purge old entries
    cutoff = (datetime.now(timezone.utc) - timedelta(days=_RETENTION_DAYS)).isoformat()
    history = {link: ts for link, ts in history.items() if ts > cutoff}

    _save(history)
    log.info("History updated: %d entries.", len(history))
