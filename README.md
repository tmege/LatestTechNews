# LatestTechNews

Automated tech news aggregator that fetches, classifies, summarizes and posts the best daily tech news to Discord.

## How It Works

```
RSS Feeds (10 curated sources)
        ↓
  Spam filtering
        ↓
  Deduplication (title similarity)
        ↓
  Classification (keyword matching)
        ↓
  AI Summarization (Ollama, local)
        ↓
  Discord Webhooks (3 channels)
```

Articles are fetched from curated RSS feeds, filtered for spam/promo content, deduplicated, classified into one of three categories, optionally summarized by a local LLM (Ollama), and posted to dedicated Discord channels.

## Discord Channels

| Channel | Content | Color |
|---|---|---|
| `#ai-machine-learning` | AI, LLMs, robotics, generative AI, OpenAI, Anthropic, DeepMind | Purple |
| `#finance-crypto` | Crypto, blockchain, fintech, funding rounds, IPOs, regulation | Green |
| `#tech-hardware` | Hardware, Big Tech, cybersecurity, semiconductors, gadgets | Blue |

## Sourcing Strategy

All sources have been independently evaluated for credibility using [Media Bias/Fact Check](https://mediabiasfactcheck.com/) ratings and industry reputation.

### Tier 1 — Highest Credibility (9+/10)

| Source | Score | RSS Feed | Notes |
|---|:-:|---|---|
| MIT Technology Review | 9.5 | `technologyreview.com/feed/` | Published since 1899. MBFC: Very High factual reporting. |
| Ars Technica | 9.0 | `feeds.arstechnica.com/arstechnica/index` | MBFC: Least Biased. Technically deep, expert-level reporting. |
| Wired | 8.5 | `wired.com/feed/rss` | MBFC: High factual reporting. Strong investigative journalism. |
| BleepingComputer | 8.5 | `bleepingcomputer.com/feed/` | Leading cybersecurity news. 20+ years of trusted reporting. |

### Tier 2 — High Credibility (7.5+/10)

| Source | Score | RSS Feed | Notes |
|---|:-:|---|---|
| The Verge | 8.0 | `theverge.com/rss/index.xml` | MBFC: High factual reporting. Consumer tech focus. |
| TechCrunch | 7.5 | `techcrunch.com/feed/` | MBFC: High factual reporting. Best for startup/VC breaking news. |
| VentureBeat | 7.5 | `venturebeat.com/category/ai/feed/` | Strong AI/enterprise coverage. Center bias rating. |

### Tier 3 — Moderate (6-7/10, used with caution)

| Source | Score | RSS Feed | Notes |
|---|:-:|---|---|
| Hacker News | 7.0 | `hnrss.org/frontpage` | Community-curated aggregator. Quality depends on linked source. |
| CoinDesk | 6.0 | `coindesk.com/arc/outboundfeeds/rss/` | Best crypto coverage but owned by Bullish (crypto exchange). |

### Excluded Sources

| Source | Reason |
|---|---|
| The Block | Secret funding from Sam Bankman-Fried / Alameda Research. Credibility permanently compromised. |

### Classification Logic

Articles are classified using keyword matching against title + summary:
- Each category has 25+ curated keywords
- Short keywords (<=3 chars) use word-boundary matching to avoid false positives
- When an article matches multiple categories, the one with the highest keyword score wins
- Unclassified articles default to `tech-hardware`

### Spam Filtering

Articles are automatically filtered out if their title or summary matches promotional patterns: coupons, promo codes, discounts, deals, sponsored content.

### Deduplication

When the same story is covered by multiple sources, duplicates are removed using title similarity (SequenceMatcher, threshold: 0.6). The most recent version is kept.

## Tech Stack

- **Python 3.9+**
- **feedparser** — RSS feed parsing
- **requests** — HTTP client (Discord webhooks, Ollama API)
- **python-dateutil** — Robust date parsing from RSS feeds
- **python-dotenv** — Environment variable management
- **Ollama** — Local LLM for article summarization (Llama 3.1 8B recommended)

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Ollama

```bash
brew install ollama
ollama serve           # start the server
ollama pull llama3.1   # download the model (~4.7 GB)
```

### 3. Configure Discord webhooks

In your Discord server:

1. **Server Settings** → **Integrations** → **Webhooks**
2. Create 3 webhooks, one per channel (`#ai-machine-learning`, `#finance-crypto`, `#tech-hardware`)
3. Copy each webhook URL

```bash
cp .env.example .env
# Edit .env with your webhook URLs
```

### 4. Run manually

From the project directory:

```bash
cd /Users/pab7o/Dev/LatestTechNews/LatestTechNews-repo

# Full run with AI summaries
python3 main.py

# Test without posting to Discord
python3 main.py --dry-run

# Fast mode without AI summaries
python3 main.py --no-summary

# Fetch articles from the last 48 hours
python3 main.py --hours 48

# Debug logging
python3 main.py -v

# Combine flags
python3 main.py --dry-run --no-summary --hours 12 -v
```

### 5. Automate with cron

```bash
crontab -e
```

Add:

```
0 8 * * * cd /path/to/LatestTechNews-repo && /usr/bin/python3 main.py >> /tmp/technews.log 2>&1
```

This runs every day at 08:00. Logs are written to `/tmp/technews.log`.

Make sure Ollama is running (`ollama serve`) or add it to your Mac login items (**System Settings → General → Login Items**) for automatic startup.

## Project Structure

```
LatestTechNews-repo/
├── main.py           # Entry point, orchestrates the pipeline
├── config.py         # Configuration (feeds, keywords, webhooks)
├── feeds.py          # RSS fetching, spam filtering, HTML cleanup
├── classifier.py     # Keyword-based article classification
├── dedup.py          # Title similarity deduplication
├── summarizer.py     # Ollama-powered article summarization
├── discord.py        # Discord embed formatting and webhook delivery
├── requirements.txt  # Python dependencies
├── .env.example      # Environment variable template
└── .gitignore
```

## License

MIT
