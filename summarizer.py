"""Summarize articles using a local Ollama LLM."""

import logging
import requests
from config import OLLAMA_URL, OLLAMA_MODEL

log = logging.getLogger("technews")

_SYSTEM_PROMPT = (
    "You are a tech news summarizer. "
    "Summarize the following article in 4-6 sentences. "
    "Cover the key facts, context, and why it matters. "
    "Be factual, neutral, and informative. No opinions."
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
                    "num_predict": 512,
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


_RESUME_SYSTEM_PROMPT = (
    "Tu es un rédacteur de résumé tech quotidien. "
    "À partir de la liste d'articles ci-dessous, rédige un résumé concis en français. "
    "Organise par thème (IA, Crypto/Finance, Tech/Hardware). "
    "Chaque article résumé en 1-2 lignes max. "
    "Le résumé total doit faire entre 20 et 50 lignes. "
    "Sois factuel, neutre et informatif. Pas d'opinions."
)


def generate_daily_resume(articles: list[dict]) -> str:
    """Generate a condensed daily digest from a list of articles.

    Uses Ollama to produce a ~20-50 line summary in French.
    Falls back to a simple bullet-point list if Ollama is unavailable.
    """
    # Build article list for the prompt
    lines = []
    for i, a in enumerate(articles, 1):
        summary = a.get("ai_summary") or a.get("summary", "")
        lines.append(f"{i}. [{a['source']}] {a['title']}\n   {summary[:200]}")

    prompt = "\n".join(lines)

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "system": _RESUME_SYSTEM_PROMPT,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 2048,
                },
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception:
        log.warning("Ollama daily résumé generation failed", exc_info=True)
        # Fallback: simple bullet list
        fallback_lines = []
        for a in articles:
            fallback_lines.append(f"• **{a['title']}** ({a['source']})")
        return "\n".join(fallback_lines)
