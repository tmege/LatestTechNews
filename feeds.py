"""Fetch and filter RSS feeds."""

import re
import logging
import feedparser
from datetime import datetime, timezone, timedelta
from dateutil import parser as dateparser
from config import RSS_FEEDS

log = logging.getLogger("technews")

# Spam / promo filter
_SPAM_PATTERNS = [
    r"coupon", r"promo code", r"discount", r"% off", r"\$\d+ off",
    r"save up to", r"deal of the day", r"best deals", r"sponsored",
]
_SPAM_RE = re.compile("|".join(_SPAM_PATTERNS), re.IGNORECASE)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return _HTML_TAG_RE.sub("", text).strip()


def _is_spam(title: str, summary: str) -> bool:
    """Return True if an article looks like spam/promo content."""
    return bool(_SPAM_RE.search(f"{title} {summary}"))


def fetch_articles(hours: int = 24) -> list[dict]:
    """Fetch all RSS feeds and return articles from the last *hours* hours.

    Returns a list of dicts sorted by publication date (newest first).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    articles: list[dict] = []

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
        except Exception:
            log.warning("Failed to fetch %s", feed_url, exc_info=True)
            continue

        source_name = getattr(feed.feed, "title", feed_url)

        for entry in feed.entries:
            published_raw = entry.get("published") or entry.get("updated")
            if not published_raw:
                continue

            try:
                published = dateparser.parse(published_raw)
            except (ValueError, TypeError):
                continue

            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)

            if published < cutoff:
                continue

            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            summary = _strip_html(entry.get("summary", ""))

            if not title or not link:
                continue
            if _is_spam(title, summary):
                continue

            articles.append({
                "title": title,
                "link": link,
                "summary": summary[:500],
                "source": source_name,
                "published": published,
            })

    articles.sort(key=lambda a: a["published"], reverse=True)
    return articles
