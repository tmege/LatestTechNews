"""Summarize articles using a local Ollama LLM."""

import logging
import requests
from config import OLLAMA_URL, OLLAMA_MODEL

log = logging.getLogger("technews")

_SYSTEM_PROMPT = (
    "You are a concise tech news summarizer. "
    "Summarize the following article in 2-3 sentences. "
    "Be factual, neutral, and to the point. No opinions."
)


def summarize(article: dict) -> str:
    """Return a short AI-generated summary for a single article.

    Falls back to a truncated raw summary if Ollama is unavailable.
    """
    prompt = (
        f"Title: {article['title']}\n"
        f"Source: {article['source']}\n"
        f"Content: {article['summary']}\n\n"
        "Summary:"
    )

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "system": _SYSTEM_PROMPT,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 200,
                },
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception:
        log.warning("Ollama summarization failed for '%s'", article["title"], exc_info=True)
        fallback = article.get("summary", "")
        if len(fallback) > 200:
            fallback = fallback[:200] + "..."
        return fallback


def summarize_articles(articles: list[dict]) -> list[dict]:
    """Add an ``ai_summary`` key to each article."""
    for article in articles:
        article["ai_summary"] = summarize(article)
    return articles
