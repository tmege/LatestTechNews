# LatestTechNews

Automated tech news aggregator that fetches, classifies, summarizes and posts the best daily tech news to Discord — with AI-powered summaries and a relevance-scored daily digest.

## How It Works

```
                    CRON 1 (every 6h): main.py
                    ========================
                    RSS Feeds (16 sources)
                            |
                      Spam filtering
                            |
                    Deduplication + coverage counting
                            |
                      Paywall detection
                            |
                    Empty content scraping (fallback)
                            |
                    Classification (keywords)
                            |
                    AI Summarization (Claude API) + empty filter
                            |
                    Discord (3 category channels, empty filtered)
                            |
                    Score & store articles
                            |
                    .scored_articles.json
                            |
                    CRON 2 (daily at 20:00): resume.py
                    ==================================
                    Load top 20 by relevance score
                            |
                    Generate condensed digest (Claude API)
                            |
                    Discord (#daily-resume)
```

## Dual Cron Architecture

| Cron | Schedule | Script | Purpose |
|------|----------|--------|---------|
| **Cron 1** | Every 6 hours | `main.py` | Fetch, classify, summarize, post to category channels, score & store |
| **Cron 2** | Daily at 20:00 | `resume.py` | Read scored articles, pick top 20, generate digest, post to résumé channel |

This separation ensures the daily digest reflects a full day of coverage with the most relevant articles ranked by a composite score.

## Discord Channels

| Channel | Content | Color |
|---|---|---|
| `#ai-machine-learning` | AI, LLMs, robotics, generative AI, OpenAI, Anthropic, DeepMind | Purple |
| `#finance-crypto` | Crypto, blockchain, fintech, funding rounds, IPOs, regulation | Green |
| `#tech-hardware` | Hardware, Big Tech, cybersecurity, semiconductors, gadgets | Blue |
| `#daily-resume` | Top 20 most relevant articles of the day (scored digest) | Red |

## Relevance Scoring

The daily digest doesn't just pick the most recent articles — it ranks them by **relevance score**, a weighted composite of real engagement signals:

```
score = 0.35 * coverage       # how many sources covered the same story
      + 0.25 * hn_engagement  # Hacker News points (extracted from RSS)
      + 0.20 * keyword_match  # keyword strength from classifier
      + 0.10 * credibility    # source tier (MIT=1.0, CoinDesk=0.6)
      + 0.10 * recency        # exponential decay over 24h
```

| Signal | Weight | Source | Rationale |
|--------|:------:|--------|-----------|
| **Coverage count** | 35% | Deduplication phase | If 4+ sources cover the same story, it's major news |
| **HN engagement** | 25% | Hacker News RSS | Points reflect tech community interest |
| **Keyword strength** | 20% | Classifier | More keyword matches = stronger topic signal |
| **Source credibility** | 10% | Config (MBFC ratings) | Tier 1 sources weighted higher |
| **Recency** | 10% | Publication date | Newer articles get a slight boost |

Articles with empty summaries (typically from paywalled sources) are automatically excluded from the digest.

## Sourcing Strategy

All sources have been independently evaluated for credibility using [Media Bias/Fact Check](https://mediabiasfactcheck.com/) ratings and industry reputation. Sources scoring below 6/10 are excluded entirely.

### Tier 1 — Highest Credibility (8.5+/10)

| Source | Score | Category | Notes |
|---|:-:|---|---|
| MIT Technology Review | 9.5 | AI/ML | Published since 1899. MBFC: Very High factual reporting. |
| Ars Technica | 9.0 | Tech | MBFC: Least Biased. Technically deep, expert-level reporting. |
| Wired | 8.5 | Tech | MBFC: High factual reporting. Strong investigative journalism. |
| BleepingComputer | 8.5 | Tech | Leading cybersecurity news. 20+ years of trusted reporting. |
| Tom's Hardware | 8.5 | Tech | MBFC: High factual reporting. Hardware reviews and benchmarks since 1996. |
| OpenAI Blog | 8.5 | AI/ML | Official primary source for OpenAI announcements and research. |

### Tier 2 — High Credibility (7.5+/10)

| Source | Score | Category | Notes |
|---|:-:|---|---|
| The Verge | 8.0 | Tech | MBFC: High factual reporting. Consumer tech focus. |
| KDnuggets | 8.0 | AI/ML | Leading data science and ML publication since 1993. |
| TechCrunch | 7.5 | Tech/Finance | MBFC: High factual reporting. Best for startup/VC breaking news. |
| VentureBeat | 7.5 | AI/ML | Strong AI/enterprise coverage. Center bias rating. |
| MarkTechPost | 7.5 | AI/ML | AI research news and ML paper breakdowns. 2M+ community. |
| Cointelegraph | 7.5 | Finance | One of the largest crypto media outlets. Daily coverage. |
| Decrypt | 7.5 | Finance | Crypto and Web3 news. Clear editorial/opinion separation. |

### Tier 3 — Moderate (6-7/10, used with caution)

| Source | Score | Category | Notes |
|---|:-:|---|---|
| Hacker News | 7.0 | Tech | Community-curated aggregator. Quality depends on linked source. |
| CoinDesk | 6.0 | Finance | Best crypto coverage but owned by Bullish (crypto exchange). |

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

### Empty Content Handling

Some sources (especially Hacker News) provide RSS entries with minimal or no summary — just metadata like points and comment counts. The system handles this with 3 layers of protection:

1. **Page scraping** — When an RSS summary is shorter than 50 characters, the system fetches the article page and extracts text from `<p>` tags (timeout: 10s, capped at 500 chars)
2. **Pre-summarization filter** — If the summary is still under 30 characters after scraping, the Claude API call is skipped entirely (no wasted compute)
3. **Post-summarization filter** — If Claude returns a "no content" response (e.g. "Unfortunately, it seems there is no content provided..."), the summary is discarded
4. **Discord filter** — Articles with no usable summary (`ai_summary` and `summary` both empty) are excluded from Discord posts

### Spam Filtering

Articles are automatically filtered out if their title or summary matches promotional patterns: coupons, promo codes, discounts, deals, sponsored content.

### Deduplication & Coverage Counting

When the same story is covered by multiple sources, duplicates are detected using title similarity (SequenceMatcher, threshold: 0.6). Instead of simply discarding duplicates, the system counts how many sources covered each story and records which sources reported it. This **coverage count** is the strongest signal in the relevance scoring formula — a story covered by 4+ sources is almost certainly important.

## Tech Stack

- **Python 3.9+**
- **feedparser** — RSS feed parsing
- **requests** — HTTP client (Discord webhooks)
- **python-dateutil** — Robust date parsing from RSS feeds
- **python-dotenv** — Environment variable management
- **anthropic** — Claude API SDK for article summarization (Haiku 4.5)

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure your Claude API key

Get your API key from [console.anthropic.com](https://console.anthropic.com/) and add it to your `.env` file:

```bash
CLAUDE_API_KEY=sk-ant-your-key-here
```

### 3. Configure Discord webhooks

In your Discord server:

1. **Server Settings** > **Integrations** > **Webhooks**
2. Create 4 webhooks, one per channel (`#ai-machine-learning`, `#finance-crypto`, `#tech-hardware`, `#daily-resume`)
3. Copy each webhook URL

```bash
cp .env.example .env
# Edit .env with your webhook URLs
```

### 4. Run

```bash
# === CRON 1: Fetch, classify, post & score ===
python3 main.py                        # full run
python3 main.py --dry-run              # test without posting
python3 main.py --no-summary           # skip Claude API
python3 main.py --hours 48 -v          # last 48h, debug

# === CRON 2: Daily digest ===
python3 resume.py                      # post top 20 digest
python3 resume.py --dry-run            # preview digest
python3 resume.py --top 10             # top 10 only
python3 resume.py --hours 12           # last 12h only
python3 resume.py --no-summary -v      # bullet list, debug
```

### 5. Automate with cron

```bash
crontab -e
```

Add:

```cron
# Fetch & post 1h30 before US market open (8:00 AM EDT = 12:00 UTC)
0 12 * * 1-5 cd /path/to/LatestTechNews-repo && /usr/bin/python3 main.py >> /tmp/technews.log 2>&1

# Fetch & post 30min after US market close (4:30 PM EDT = 20:30 UTC)
30 20 * * 1-5 cd /path/to/LatestTechNews-repo && /usr/bin/python3 main.py >> /tmp/technews.log 2>&1

# Digest 5min after each news run
5 12 * * 1-5 cd /path/to/LatestTechNews-repo && /usr/bin/python3 resume.py >> /tmp/technews-resume.log 2>&1
35 20 * * 1-5 cd /path/to/LatestTechNews-repo && /usr/bin/python3 resume.py >> /tmp/technews-resume.log 2>&1
```

Make sure your `CLAUDE_API_KEY` is set in your `.env` file.

## Project Structure

```
LatestTechNews-repo/
├── main.py           # Cron 1: fetch, classify, summarize, post, score
├── resume.py         # Cron 2: daily digest from scored articles
├── config.py         # Configuration (feeds, keywords, webhooks, credibility)
├── feeds.py          # RSS fetching, spam filtering, HN engagement extraction, page scraping fallback
├── classifier.py     # Keyword-based classification (exposes keyword_score)
├── dedup.py          # Title similarity dedup + coverage counting
├── summarizer.py     # Claude API-powered summarization + digest generation
├── scoring.py        # Relevance scoring engine + JSON storage
├── discord.py        # Discord formatting, rate limiting, webhook delivery
├── history.py        # Posted-article tracking (7-day retention)
├── requirements.txt  # Python dependencies
├── .env.example      # Environment variable template
└── .gitignore
```

## License

MIT
