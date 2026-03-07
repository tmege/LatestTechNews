"""Format and send articles to Discord via webhooks."""

import time
import logging
import requests
from datetime import datetime, timezone
from config import WEBHOOKS, CATEGORY_LABELS, MAX_ARTICLES_PER_CATEGORY

log = logging.getLogger("technews")

DISCORD_MAX_LENGTH = 2000
_RATE_LIMIT_DELAY = 0.5  # seconds between webhook posts


def _format_article(index: int, article: dict) -> str:
    """Format a single article as numbered text."""
    title = article["title"]
    link = article["link"]
    source = article["source"]
    summary = article.get("ai_summary") or article.get("summary", "")

    return (
        f"**{index}. {title}**\n"
        f"{summary}\n"
        f"Source: {source} | [Lire l'article]({link})\n"
    )


def _post_messages(
    webhook_url: str,
    messages: list[str],
    label: str,
) -> int:
    """Post a list of messages to a Discord webhook with rate limiting.

    Returns the number of successfully posted messages.
    """
    posted = 0
    for msg in messages:
        try:
            resp = requests.post(
                webhook_url,
                json={"content": msg},
                timeout=10,
            )
            # Honor Discord rate limits
            if resp.status_code == 429:
                retry_after = resp.json().get("retry_after", 5)
                log.warning("Rate limited, retrying in %.1fs", retry_after)
                time.sleep(retry_after)
                resp = requests.post(
                    webhook_url,
                    json={"content": msg},
                    timeout=10,
                )
            resp.raise_for_status()
            posted += 1
        except requests.exceptions.RequestException as exc:
            log.error("Failed to post to %s: %s", label, exc)
            return posted
        time.sleep(_RATE_LIMIT_DELAY)
    return posted


def send_to_discord(
    category: str,
    articles: list[dict],
    dry_run: bool = False,
) -> None:
    """Send articles to the appropriate Discord channel via webhook."""
    webhook_url = WEBHOOKS.get(category, "")

    if not webhook_url and not dry_run:
        log.warning("No webhook configured for %s — skipping.", category)
        return

    if not articles:
        log.info("No articles for %s — skipping.", category)
        return

    label = CATEGORY_LABELS.get(category, category)
    today = datetime.now(timezone.utc).strftime("%d %B %Y")
    header = f"**{label} — {today}**\n\n"

    # Filter out articles with no usable content
    articles = [
        a for a in articles
        if (a.get("ai_summary") or a.get("summary", "")).strip()
    ]

    if not articles:
        log.info("No articles with content for %s — skipping.", category)
        return

    # Build all formatted articles
    formatted = []
    for i, article in enumerate(articles[:MAX_ARTICLES_PER_CATEGORY], 1):
        formatted.append(_format_article(i, article))

    # Split into messages that fit within Discord's 2000 char limit
    messages = []
    current = header
    for block in formatted:
        if len(current) + len(block) + 1 > DISCORD_MAX_LENGTH:
            messages.append(current.rstrip())
            current = ""
        current += block + "\n"
    if current.strip():
        messages.append(current.rstrip())

    if dry_run:
        print(f"\n{'=' * 60}")
        print(f"[DRY RUN] {label} — {len(formatted)} articles in {len(messages)} message(s)")
        print(f"{'=' * 60}")
        for msg in messages:
            print(msg)
            print(f"--- ({len(msg)} chars) ---\n")
        return

    posted = _post_messages(webhook_url, messages, label)
    log.info("Posted %d articles to %s (%d message(s))", len(formatted), category, posted)


def send_daily_resume(
    resume_text: str,
    dry_run: bool = False,
) -> None:
    """Send the daily résumé to the dedicated Discord channel."""
    webhook_url = WEBHOOKS.get("daily-resume", "")

    if not webhook_url and not dry_run:
        log.warning("No webhook configured for daily-resume — skipping.")
        return

    if not resume_text:
        log.info("Empty résumé — skipping.")
        return

    label = CATEGORY_LABELS.get("daily-resume", "Résumé du jour")
    today = datetime.now(timezone.utc).strftime("%d %B %Y")
    header = f"**{label} — {today}**\n\n"

    full_text = header + resume_text

    # Split into chunks respecting Discord's 2000 char limit
    messages = []
    current = ""
    for line in full_text.split("\n"):
        if len(current) + len(line) + 1 > DISCORD_MAX_LENGTH:
            messages.append(current.rstrip())
            current = ""
        current += line + "\n"
    if current.strip():
        messages.append(current.rstrip())

    if dry_run:
        print(f"\n{'=' * 60}")
        print(f"[DRY RUN] {label} — {len(messages)} message(s)")
        print(f"{'=' * 60}")
        for msg in messages:
            print(msg)
            print(f"--- ({len(msg)} chars) ---\n")
        return

    posted = _post_messages(webhook_url, messages, label)
    log.info("Posted daily résumé (%d message(s))", posted)
