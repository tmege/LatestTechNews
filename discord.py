"""Format and send articles to Discord via webhooks."""

import logging
import requests
from datetime import datetime, timezone
from config import WEBHOOKS, EMBED_COLORS, CATEGORY_LABELS, MAX_ARTICLES_PER_CATEGORY

log = logging.getLogger("technews")


def _build_embeds(articles: list[dict], category: str) -> list[dict]:
    """Build Discord embed objects for a list of articles."""
    color = EMBED_COLORS.get(category, 0x95A5A6)
    embeds = []

    for article in articles[:MAX_ARTICLES_PER_CATEGORY]:
        description = article.get("ai_summary") or article.get("summary", "")
        if len(description) > 300:
            description = description[:300] + "..."

        embeds.append({
            "title": article["title"][:256],
            "url": article["link"],
            "description": description,
            "color": color,
            "footer": {"text": f"Source: {article['source']}"},
            "timestamp": article["published"].isoformat(),
        })

    return embeds


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
    embeds = _build_embeds(articles, category)

    # Discord allows max 10 embeds per message
    for i in range(0, len(embeds), 10):
        batch = embeds[i : i + 10]
        payload = {
            "content": f"**{label} — {today}**" if i == 0 else None,
            "embeds": batch,
        }

        if dry_run:
            print(f"\n{'=' * 60}")
            print(f"[DRY RUN] {label} — {len(batch)} articles")
            print(f"{'=' * 60}")
            for embed in batch:
                print(f"  - {embed['title']}")
                print(f"    {embed['description'][:100]}...")
                print(f"    {embed['url']}")
                print()
            continue

        try:
            resp = requests.post(webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            log.info("Posted %d articles to %s", len(batch), category)
        except Exception:
            log.error("Failed to post to %s", category, exc_info=True)
