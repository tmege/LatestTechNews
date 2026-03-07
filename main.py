#!/usr/bin/env python3
"""LatestTechNews — Tech news aggregator for Discord."""

import sys
import logging
import argparse

from feeds import fetch_articles
from dedup import deduplicate
from classifier import classify_articles
from summarizer import summarize_articles
from discord import send_to_discord
from history import filter_already_posted, mark_as_posted
from scoring import calculate_scores, store_scored_articles


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch and post tech news to Discord.",
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
    args.hours = min(args.hours, 168)  # cap at 1 week

    _setup_logging(verbose=args.verbose)
    log = logging.getLogger("technews")

    # 1. Fetch
    log.info("[1/7] Fetching RSS feeds...")
    articles = fetch_articles(hours=args.hours)
    log.info("      Found %d articles.", len(articles))

    if not articles:
        log.warning("No articles found. Exiting.")
        return 0

    # 2. Deduplicate (counts coverage before removing)
    log.info("[2/7] Deduplicating...")
    articles = deduplicate(articles)
    log.info("      %d unique articles.", len(articles))

    # 3. Filter already posted
    log.info("[3/7] Filtering already-posted articles...")
    articles = filter_already_posted(articles)
    log.info("      %d new articles.", len(articles))

    if not articles:
        log.info("No new articles to post. Exiting.")
        return 0

    # 4. Classify (also sets keyword_score on each article)
    log.info("[4/7] Classifying articles...")
    grouped = classify_articles(articles)
    for cat, items in grouped.items():
        log.info("      %s: %d articles", cat, len(items))

    # 5. Summarize
    if not args.no_summary:
        log.info("[5/7] Summarizing with Ollama...")
        for cat in grouped:
            grouped[cat] = summarize_articles(grouped[cat])
    else:
        log.info("[5/7] Skipping summarization (--no-summary).")

    # 6. Post to Discord
    log.info("[6/7] Posting to Discord...")
    all_posted: list[dict] = []
    for cat, items in grouped.items():
        send_to_discord(cat, items, dry_run=args.dry_run)
        all_posted.extend(items)

    # 7. Score & store for daily digest (resume.py reads this)
    log.info("[7/7] Scoring and storing articles...")
    all_posted = calculate_scores(all_posted)
    top = sorted(all_posted, key=lambda a: a.get("relevance_score", 0), reverse=True)
    for a in top[:5]:
        log.info("      %.3f | %s (%s, cov=%d)",
                 a["relevance_score"], a["title"][:60],
                 a["source"], a.get("coverage_count", 1))

    if not args.dry_run:
        store_scored_articles(all_posted)
        mark_as_posted(all_posted)
    else:
        log.info("      [DRY RUN] Skipping storage.")

    log.info("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
