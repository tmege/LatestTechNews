"""Summarize articles using the Claude API (Anthropic)."""

import logging
import anthropic
from config import CLAUDE_API_KEY, CLAUDE_MODEL

log = logging.getLogger("technews")

_SYSTEM_PROMPT = (
    "You are a tech news summarizer. "
    "Summarize the following article in 4-6 sentences. "
    "Cover the key facts, context, and why it matters. "
    "Be factual, neutral, and informative. No opinions. "
    "Use formal academic English. "
    "Start directly with the summary text. Do not include any heading or label like 'Summary'."
)

_MIN_CONTENT_LENGTH = 30  # skip API call if summary is shorter than this

# Phrases that indicate the LLM couldn't summarize (empty/paywalled content)
_NO_CONTENT_PHRASES = [
    "no content provided",
    "no content available",
    "article appears to be incomplete",
    "unable to summarize",
    "unfortunately, it seems there is no",
    "no article content",
    "i cannot summarize",
    "there is no content",
    "the article is empty",
    "no text to summarize",
]

client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)


def summarize(article: dict) -> str:
    """Return a short AI-generated summary for a single article.

    Falls back to a truncated raw summary if the Claude API is unavailable.
    """
    raw_summary = article.get("summary", "").strip()

    # Pre-filter: skip API call if there's not enough content to summarize
    if len(raw_summary) < _MIN_CONTENT_LENGTH:
        log.info("Skipping summarization: summary too short (%d chars)", len(raw_summary))
        return raw_summary

    # Cap content size to control API costs
    title = article.get("title", "")[:300]
    source = article.get("source", "")[:200]
    content = raw_summary[:2000]

    prompt = (
        f"Title: {title}\n"
        f"Source: {source}\n"
        f"Content: {content}\n\n"
        "Summary:"
    )

    try:
        message = client.messages.create(
            model=CLAUDE_MODEL,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=512,
            timeout=60,
        )
        ai_text = message.content[0].text.strip()

        # Post-filter: detect LLM "no content" responses
        ai_lower = ai_text.lower()
        if any(phrase in ai_lower for phrase in _NO_CONTENT_PHRASES):
            log.warning("LLM returned 'no content' response — discarding")
            return ""

        return ai_text
    except Exception:
        log.warning("Claude summarization failed for an article")
        fallback = raw_summary
        if len(fallback) > 200:
            fallback = fallback[:200] + "..."
        return fallback


def summarize_articles(articles: list[dict]) -> list[dict]:
    """Add an ``ai_summary`` key to each article."""
    for article in articles:
        article["ai_summary"] = summarize(article)
    return articles


_RESUME_SYSTEM_PROMPT = (
    "You are a daily tech news digest writer. "
    "From the list of articles below, write a concise digest in formal academic English. "
    "Organize by theme with bold headers: **AI**, **Crypto/Finance**, **Tech/Hardware**. "
    "Use bullet points (•) for each article, one bullet per article, 1-2 lines max each. "
    "Be factual, neutral, and informative. No opinions."
)


def generate_daily_resume(articles: list[dict]) -> str:
    """Generate a condensed daily digest from a list of articles.

    Uses Claude API to produce a ~20-50 line summary in French.
    Falls back to a simple bullet-point list if the API is unavailable.
    """
    # Build article list for the prompt
    lines = []
    for i, a in enumerate(articles, 1):
        summary = a.get("ai_summary") or a.get("summary", "")
        lines.append(f"{i}. [{a['source']}] {a['title']}\n   {summary[:200]}")

    prompt = "\n".join(lines)

    try:
        message = client.messages.create(
            model=CLAUDE_MODEL,
            system=_RESUME_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2048,
            timeout=120,
        )
        return message.content[0].text.strip()
    except Exception:
        log.warning("Claude daily digest generation failed")
        # Fallback: simple bullet list
        fallback_lines = []
        for a in articles:
            fallback_lines.append(f"• **{a['title']}** ({a['source']})")
        return "\n".join(fallback_lines)
