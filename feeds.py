"""Fetch and filter RSS feeds."""

import re
import time
import logging
import ipaddress
import feedparser
import requests
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta
from dateutil import parser as dateparser
from config import RSS_FEEDS

log = logging.getLogger("technews")

_FEED_TIMEOUT = 30  # seconds
_FEED_MAX_SIZE = 5 * 1024 * 1024  # 5 MB

# Spam / promo filter
_SPAM_PATTERNS = [
    r"coupon", r"promo code", r"discount", r"% off", r"\$\d+ off",
    r"save up to", r"deal of the day", r"best deals", r"sponsored",
    r"\bbest\b.{0,20}\b\d{4}\b",  # "Best ... 2026" buyer guides
    r"buying guide", r"our pick", r"top \d+ best",
]
_SPAM_RE = re.compile("|".join(_SPAM_PATTERNS), re.IGNORECASE)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return _HTML_TAG_RE.sub("", text).strip()


def sanitize_for_discord(text: str) -> str:
    """Strip Discord mention triggers and markdown from untrusted text."""
    text = text.replace("@everyone", "@\u200beveryone")
    text = text.replace("@here", "@\u200bhere")
    for char in ("*", "_", "~", "|", "`", ">"):
        text = text.replace(char, "")
    return text


def _is_spam(title: str, summary: str) -> bool:
    """Return True if an article looks like spam/promo content."""
    return bool(_SPAM_RE.search(f"{title} {summary}"))


# Hacker News metadata lines to strip from summaries
_HN_NOISE_RE = re.compile(
    r"(Article URL:\s*\S+\s*|Comments URL:\s*\S+\s*|Points:\s*\d+\s*|Comments:\s*\d+\s*)",
    re.IGNORECASE,
)


_HN_POINTS_RE = re.compile(r"Points:\s*(\d+)", re.IGNORECASE)
_HN_COMMENTS_RE = re.compile(r"Comments:\s*(\d+)", re.IGNORECASE)


def _extract_hn_engagement(summary: str) -> tuple[int, int]:
    """Extract HN points and comment count from summary before cleanup."""
    points_m = _HN_POINTS_RE.search(summary)
    comments_m = _HN_COMMENTS_RE.search(summary)
    return (
        int(points_m.group(1)) if points_m else 0,
        int(comments_m.group(1)) if comments_m else 0,
    )


def _clean_summary(summary: str) -> str:
    """Remove Hacker News metadata and other noise from summaries."""
    summary = _HN_NOISE_RE.sub("", summary).strip()
    # Collapse multiple whitespace / newlines
    summary = re.sub(r"\s+", " ", summary).strip()
    return summary


_MIN_SUMMARY_LENGTH = 50  # below this, try scraping the article page

_SCRAPE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LatestTechNews/1.0)",
}
_P_TAG_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.DOTALL | re.IGNORECASE)


def _is_safe_url(url: str) -> bool:
    """Reject URLs targeting private/internal networks (SSRF protection)."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname or ""
        if hostname in ("localhost", "0.0.0.0"):
            return False
        try:
            addr = ipaddress.ip_address(hostname)
            if addr.is_private or addr.is_loopback or addr.is_link_local:
                return False
        except ValueError:
            pass  # hostname is a domain name, not an IP — that's fine
        return True
    except Exception:
        return False


def _scrape_excerpt(url: str) -> str:
    """Fetch the article page and extract a text excerpt from <p> tags.

    Returns up to 500 characters of body text, or empty string on failure.
    """
    if not _is_safe_url(url):
        log.warning("Blocked scrape of unsafe URL: %s", url)
        return ""
    try:
        resp = requests.get(url, headers=_SCRAPE_HEADERS, timeout=10,
                            allow_redirects=False)
        resp.raise_for_status()
        paragraphs = _P_TAG_RE.findall(resp.text)
        text_parts = [_strip_html(p).strip() for p in paragraphs]
        # Keep only paragraphs with real content (>40 chars filters nav/footer junk)
        text_parts = [p for p in text_parts if len(p) > 40]
        body = " ".join(text_parts)
        if body:
            log.info("Scraped excerpt for: %s", url)
            return body[:500]
    except Exception:
        log.debug("Failed to scrape excerpt for an article")
    return ""


def _extract_image(entry) -> str:
    """Try to extract an image URL from an RSS entry."""
    # media:content or media:thumbnail
    media = entry.get("media_content", [])
    for m in media:
        url = m.get("url", "")
        if url and ("image" in m.get("type", "image")):
            return url

    media_thumb = entry.get("media_thumbnail", [])
    if media_thumb:
        return media_thumb[0].get("url", "")

    # Enclosures (common in Atom feeds)
    for enc in entry.get("enclosures", []):
        if "image" in enc.get("type", ""):
            return enc.get("href", "") or enc.get("url", "")

    # Fallback: extract first <img src="..."> from summary HTML
    raw_summary = entry.get("summary", "")
    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw_summary)
    if img_match:
        return img_match.group(1)

    return ""


def fetch_articles(hours: int = 24) -> list[dict]:
    """Fetch all RSS feeds and return articles from the last *hours* hours.

    Returns a list of dicts sorted by publication date (newest first).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    articles: list[dict] = []

    for feed_url in RSS_FEEDS:
        try:
            resp = requests.get(feed_url, timeout=_FEED_TIMEOUT)
            resp.raise_for_status()
            if len(resp.content) > _FEED_MAX_SIZE:
                log.warning("Feed too large, skipping: %s", feed_url)
                continue
            feed = feedparser.parse(resp.content)
        except Exception:
            log.warning("Failed to fetch feed: %s", feed_url)
            time.sleep(2)
            continue

        source_name = getattr(feed.feed, "title", feed_url)
        source_name = "".join(c for c in source_name if c.isprintable() or c in "\n\t ")
        source_name = source_name.strip()[:200]

        time.sleep(0.5)  # stagger requests to avoid rate-limiting

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

            raw_summary_text = _strip_html(entry.get("summary", ""))
            hn_points, hn_comments = _extract_hn_engagement(raw_summary_text)

            title = sanitize_for_discord(entry.get("title", "").strip())
            link = entry.get("link", "").strip()
            summary = sanitize_for_discord(_clean_summary(raw_summary_text))

            if not title or not link:
                continue
            if not link.startswith("https://"):
                if link.startswith("http://"):
                    link = "https://" + link[7:]
                else:
                    continue
            if _is_spam(title, summary):
                continue

            # If RSS summary is too short, try scraping the article page
            if len(summary) < _MIN_SUMMARY_LENGTH:
                scraped = _scrape_excerpt(link)
                if scraped:
                    summary = sanitize_for_discord(scraped)

            image = _extract_image(entry)

            articles.append({
                "title": title,
                "link": link,
                "summary": summary[:500],
                "source": source_name,
                "published": published,
                "image": image,
                "hn_points": hn_points,
                "hn_comments": hn_comments,
            })

    articles.sort(key=lambda a: a["published"], reverse=True)
    return articles
