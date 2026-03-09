#!/usr/bin/env python3
"""Daily digest — reads scored articles and posts a condensed top-20 résumé.

Run this as a separate cron job (e.g. daily at 20:00) after main.py has been
collecting and scoring articles throughout the day.

Usage:
    python3 resume.py                    # generate & post digest
    python3 resume.py --dry-run          # preview without posting
    python3 resume.py --top 10           # top 10 instead of 20
    python3 resume.py --hours 12         # last 12 hours only
"""

import sys
import logging
import argparse

from scoring import load_top_articles
from summarizer import generate_daily_resume
from discord import send_daily_resume
from config import MAX_RESUME_ARTICLES


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate and post the daily tech news digest.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print digest without posting to Discord.",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip Claude API — use simple bullet list instead.",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Look back N hours for scored articles (default: 24).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=MAX_RESUME_ARTICLES,
        help=f"Number of top articles to include (default: {MAX_RESUME_ARTICLES}).",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging.",
    )
    args = parser.parse_args()

    _setup_logging(verbose=args.verbose)
    log = logging.getLogger("technews")

    # 1. Load top scored articles
    log.info("[1/3] Loading top %d articles from last %dh...", args.top, args.hours)
    articles = load_top_articles(hours=args.hours, limit=args.top)
    log.info("      Found %d articles.", len(articles))

    if not articles:
        log.warning("No scored articles found. Run main.py first.")
        return 0

    for a in articles[:5]:
        log.info("      %.3f | %s", a.get("relevance_score", 0), a["title"][:60])

    # 2. Generate digest
    log.info("[2/3] Generating digest...")
    if not args.no_summary:
        resume_text = generate_daily_resume(articles)
    else:
        lines = []
        for i, a in enumerate(articles, 1):
            score = a.get("relevance_score", 0)
            lines.append(f"{i}. **{a['title']}** ({a['source']}) — score: {score:.2f}")
        resume_text = "\n".join(lines)

    # 3. Post to Discord
    log.info("[3/3] Posting digest...")
    send_daily_resume(resume_text, dry_run=args.dry_run)

    log.info("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
