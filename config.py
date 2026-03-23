"""Central configuration for LatestTechNews."""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("technews")

# ---------------------------------------------------------------------------
# Discord webhooks — one per channel
# ---------------------------------------------------------------------------
WEBHOOKS: dict[str, str] = {
    "ai-ml": os.getenv("DISCORD_WEBHOOK_AI", ""),
    "finance-crypto": os.getenv("DISCORD_WEBHOOK_FINANCE", ""),
    "tech-hardware": os.getenv("DISCORD_WEBHOOK_TECH", ""),
    "geopolitics": os.getenv("DISCORD_WEBHOOK_GEO", ""),
    "daily-resume": os.getenv("DISCORD_WEBHOOK_RESUME", ""),
}

# ---------------------------------------------------------------------------
# Claude API (Anthropic)
# ---------------------------------------------------------------------------
CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

# ---------------------------------------------------------------------------
# RSS feeds — curated for reliability (see README for credibility scores)
# ---------------------------------------------------------------------------
RSS_FEEDS: list[str] = [
    # --- Tier 1 (credibility 9+/10) ---
    "https://www.technologyreview.com/feed/",                    # MIT Tech Review (9.5)
    "https://feeds.arstechnica.com/arstechnica/index",           # Ars Technica (9.0)
    "https://www.wired.com/feed/rss",                            # Wired (8.5)
    "https://www.bleepingcomputer.com/feed/",                    # BleepingComputer (8.5)
    "https://www.tomshardware.com/feeds.xml",                    # Tom's Hardware (8.5)
    # --- Tier 2 (credibility 7.5+/10) ---
    "https://www.theverge.com/rss/index.xml",                    # The Verge (8.0)
    "https://techcrunch.com/feed/",                              # TechCrunch (7.5)
    "https://venturebeat.com/category/ai/feed/",                 # VentureBeat AI (7.5)
    "https://techcrunch.com/category/fintech/feed/",             # TechCrunch Fintech (7.5)
    "https://openai.com/news/rss.xml",                           # OpenAI Blog (8.5)
    "https://feeds.feedburner.com/kdnuggets-data-mining-analytics",  # KDnuggets (8.0)
    "https://www.marktechpost.com/feed/",                        # MarkTechPost (7.5)
    "https://cointelegraph.com/rss",                             # Cointelegraph (7.5)
    "https://decrypt.co/feed",                                   # Decrypt (7.5)
    # --- Tier 3 (credibility 6-7/10) — used with caution ---
    "https://www.coindesk.com/arc/outboundfeeds/rss/",           # CoinDesk (6.0)
    "https://hnrss.org/frontpage",                               # Hacker News (7.0, aggregator)
    # --- Geopolitics (credibility 7-9.5/10) ---
    "https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com/world&ceid=US:en&hl=en-US&gl=US",  # Reuters World (9.5)
    "https://apnews.com/world-news.rss",                         # AP News (9.0)
    "https://feeds.bbci.co.uk/news/world/rss.xml",               # BBC World (8.5)
    "https://www.france24.com/en/rss",                           # France 24 (8.5)
    "https://rss.dw.com/rdf/rss-en-all",                        # Deutsche Welle (8.0)
    "https://www.aljazeera.com/xml/rss/all.xml",                 # Al Jazeera (7.0)
]

# ---------------------------------------------------------------------------
# Classification keywords per category
# ---------------------------------------------------------------------------
CATEGORIES: dict[str, list[str]] = {
    "ai-ml": [
        "AI", "artificial intelligence", "machine learning", "LLM", "GPT",
        "Claude", "Gemini", "neural", "deep learning", "NLP", "robotics",
        "autonomous", "OpenAI", "Anthropic", "DeepMind", "Mistral",
        "transformer", "diffusion", "generative", "AGI", "computer vision",
        "chatbot", "large language model", "foundation model", "Copilot",
        "Llama", "Stable Diffusion", "Midjourney", "Sora",
    ],
    "finance-crypto": [
        "crypto", "bitcoin", "ethereum", "blockchain", "DeFi", "NFT",
        "fintech", "trading", "stock", "IPO", "funding", "venture capital",
        "Series A", "Series B", "valuation", "acquisition", "SEC",
        "regulation", "stablecoin", "Web3", "DAO", "token", "mining",
        "exchange", "wallet", "ledger",
    ],
    "tech-hardware": [
        "Apple", "Google", "Microsoft", "Samsung", "chip", "GPU", "CPU",
        "semiconductor", "iPhone", "Android", "Windows", "Linux", "cloud",
        "cybersecurity", "hack", "breach", "privacy", "5G", "quantum",
        "VR", "AR", "headset", "laptop", "processor", "Nvidia", "AMD",
        "Intel", "Tesla", "SpaceX", "server", "data center",
    ],
    "geopolitics": [
        "geopolitics", "diplomacy", "sanctions", "NATO", "UN", "United Nations",
        "treaty", "conflict", "war", "ceasefire", "humanitarian", "refugee",
        "election", "coup", "embargo", "territorial", "sovereignty", "annexation",
        "nuclear", "missile", "military", "peacekeeping", "G7", "G20", "BRICS",
        "foreign policy", "geopolitical", "international relations",
    ],
}

# ---------------------------------------------------------------------------
# Discord styling
# ---------------------------------------------------------------------------
EMBED_COLORS: dict[str, int] = {
    "ai-ml": 0x9B59B6,         # purple
    "finance-crypto": 0x2ECC71,  # green
    "tech-hardware": 0x3498DB,   # blue
    "geopolitics": 0xE67E22,     # orange
    "daily-resume": 0xE74C3C,    # red
}

CATEGORY_LABELS: dict[str, str] = {
    "ai-ml": "🤖 AI & Machine Learning",
    "finance-crypto": "💰 Finance & Crypto",
    "tech-hardware": "🔧 Tech & Hardware",
    "geopolitics": "🌍 Geopolitics",
    "daily-resume": "📰 Daily Digest",
}

# Max articles included in the daily résumé
MAX_RESUME_ARTICLES: int = 20

# Max articles per category to post
MAX_ARTICLES_PER_CATEGORY: int = 10

# ---------------------------------------------------------------------------
# Scoring — source credibility (0.0 to 1.0, derived from MBFC ratings)
# ---------------------------------------------------------------------------
from pathlib import Path

SCORED_ARTICLES_FILE: Path = Path(__file__).parent / ".scored_articles.json"
SCORED_ARTICLES_RETENTION_HOURS: int = 48

# Maps partial source name (lowercase) → credibility score.
# feedparser returns the feed <title> which varies, so we match substrings.
SOURCE_CREDIBILITY: dict[str, float] = {
    "mit technology review": 1.0,    # 9.5/10
    "ars technica": 0.95,            # 9.0/10
    "wired": 0.85,                   # 8.5/10
    "bleepingcomputer": 0.85,        # 8.5/10
    "tom's hardware": 0.85,          # 8.5/10
    "openai": 0.85,                  # 8.5/10
    "the verge": 0.80,               # 8.0/10
    "kdnuggets": 0.80,               # 8.0/10
    "techcrunch": 0.75,              # 7.5/10
    "venturebeat": 0.75,             # 7.5/10
    "marktechpost": 0.75,            # 7.5/10
    "cointelegraph": 0.75,           # 7.5/10
    "decrypt": 0.75,                 # 7.5/10
    "hacker news": 0.70,             # 7.0/10
    "coindesk": 0.60,                # 6.0/10
    # Geopolitics sources
    "reuters": 0.95,                 # 9.5/10
    "associated press": 0.90,        # 9.0/10
    "ap news": 0.90,                 # 9.0/10
    "bbc": 0.85,                     # 8.5/10
    "france 24": 0.85,               # 8.5/10
    "france24": 0.85,                # 8.5/10
    "dw": 0.80,                      # 8.0/10
    "deutsche welle": 0.80,          # 8.0/10
    "al jazeera": 0.70,              # 7.0/10
    "aljazeera": 0.70,               # 7.0/10
}
