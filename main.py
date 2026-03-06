#!/usr/bin/env python3
"""LatestTechNews — Daily tech news aggregator for Discord."""

import sys
import logging
import argparse

from feeds import fetch_articles
from dedup import deduplicate
from classifier import classify_articles
from summarizer import summarize_articles
from discord import send_to_discord


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch and post daily tech news to Discord.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print results without posting to Discord.",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip AI summarization (faster, no Ollama needed).",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Fetch articles from the last N hours (default: 24).",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging.",
    )
    args = parser.parse_args()

    _setup_logging(verbose=args.verbose)
    log = logging.getLogger("technews")

    # 1. Fetch
    log.info("[1/5] Fetching RSS feeds...")
    articles = fetch_articles(hours=args.hours)
    log.info("      Found %d articles.", len(articles))

    if not articles:
        log.warning("No articles found. Exiting.")
        return 0

    # 2. Deduplicate
    log.info("[2/5] Deduplicating...")
    articles = deduplicate(articles)
    log.info("      %d unique articles.", len(articles))

    # 3. Classify
    log.info("[3/5] Classifying articles...")
    grouped = classify_articles(articles)
    for cat, items in grouped.items():
        log.info("      %s: %d articles", cat, len(items))

    # 4. Summarize
    if not args.no_summary:
        log.info("[4/5] Summarizing with Ollama...")
        for cat in grouped:
            grouped[cat] = summarize_articles(grouped[cat])
    else:
        log.info("[4/5] Skipping summarization (--no-summary).")

    # 5. Post to Discord
    log.info("[5/5] Posting to Discord...")
    for cat, items in grouped.items():
        send_to_discord(cat, items, dry_run=args.dry_run)

    log.info("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
