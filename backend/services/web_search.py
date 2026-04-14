"""Multi-provider web search for fact-checking.

Aggregates results from:
  1. DuckDuckGo   — free, no key, but heavily rate-limited
  2. Wikipedia    — free, no key, reliable for evergreen facts
  3. Brave Search — free tier (2000 queries/month), activates if BRAVE_SEARCH_API_KEY is set

Each provider returns a list of dicts with: title, url, body, date.
The orchestrator de-duplicates by URL and returns a unified pool.
"""

import asyncio
import logging
import os
from typing import List
from urllib.parse import quote

import httpx
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

BRAVE_SEARCH_API_KEY = os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "").strip()


async def _ddg_search(query: str) -> List[dict]:
    """DuckDuckGo (news + text). Blocking library — run in a thread."""
    def _run():
        ddgs = DDGS()
        results = []
        try:
            news = ddgs.news(query, max_results=3) or []
            results.extend(news)
        except Exception as e:
            logger.debug(f"DDG news failed for {query!r}: {e}")
        try:
            text = ddgs.text(query, max_results=2) or []
            results.extend(text)
        except Exception as e:
            logger.debug(f"DDG text failed for {query!r}: {e}")
        return results

    try:
        raw = await asyncio.to_thread(_run)
    except Exception as e:
        logger.debug(f"DDG search failed for {query!r}: {e}")
        return []

    normalized = []
    for r in raw:
        url = (r.get("href") or r.get("url") or "").strip()
        if not url:
            continue
        normalized.append({
            "title": (r.get("title") or "").strip(),
            "url": url,
            "body": (r.get("body") or "").strip(),
            "date": (r.get("date") or "").strip(),
            "provider": "duckduckgo",
        })
    return normalized


async def _wikipedia_search(query: str) -> List[dict]:
    """Wikipedia MediaWiki API search — no key needed."""
    url = (
        "https://en.wikipedia.org/w/api.php"
        f"?action=query&list=search&srsearch={quote(query)}"
        "&srlimit=3&format=json&srprop=snippet|timestamp"
    )
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Veritas/1.0 (fact-checking app)"},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.debug(f"Wikipedia search failed for {query!r}: {e}")
        return []

    results = []
    for hit in data.get("query", {}).get("search", []) or []:
        title = hit.get("title", "")
        if not title:
            continue
        # Strip the HTML <span> highlights Wikipedia wraps around matched terms.
        snippet = (
            hit.get("snippet", "")
            .replace('<span class="searchmatch">', "")
            .replace("</span>", "")
            .strip()
        )
        page_url = f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
        results.append({
            "title": f"Wikipedia: {title}",
            "url": page_url,
            "body": snippet,
            "date": hit.get("timestamp", "")[:10],  # "2024-03-15T..." → "2024-03-15"
            "provider": "wikipedia",
        })
    return results


async def _brave_search(query: str) -> List[dict]:
    """Brave Search API — optional, needs BRAVE_SEARCH_API_KEY."""
    if not BRAVE_SEARCH_API_KEY:
        return []
    url = f"https://api.search.brave.com/res/v1/web/search?q={quote(query)}&count=5"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                url,
                headers={
                    "X-Subscription-Token": BRAVE_SEARCH_API_KEY,
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.debug(f"Brave search failed for {query!r}: {e}")
        return []

    results = []
    for hit in (data.get("web", {}) or {}).get("results", []) or []:
        page_url = (hit.get("url") or "").strip()
        if not page_url:
            continue
        results.append({
            "title": (hit.get("title") or "").strip(),
            "url": page_url,
            "body": (hit.get("description") or "").strip(),
            "date": (hit.get("age") or "").strip(),
            "provider": "brave",
        })
    return results


async def _tavily_search(query: str) -> List[dict]:
    """Tavily AI-native search — optional, needs TAVILY_API_KEY.

    Tavily's free tier gives 1000 queries/month and returns cleaner snippets than
    general search engines because it pre-filters for authoritative sources.
    """
    if not TAVILY_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 5,
                    "include_answer": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.debug(f"Tavily search failed for {query!r}: {e}")
        return []

    results = []
    for hit in data.get("results", []) or []:
        page_url = (hit.get("url") or "").strip()
        if not page_url:
            continue
        results.append({
            "title": (hit.get("title") or "").strip(),
            "url": page_url,
            "body": (hit.get("content") or "").strip(),
            "date": (hit.get("published_date") or "").strip()[:10],
            "provider": "tavily",
        })
    return results


async def multi_provider_search(queries: List[str]) -> List[dict]:
    """Run every query against all configured providers in parallel; return a de-duplicated list.

    Results from different providers are interleaved round-robin so no single provider dominates.
    """
    tasks = []
    for q in queries[:5]:
        tasks.append(_ddg_search(q))
        tasks.append(_wikipedia_search(q))
        if BRAVE_SEARCH_API_KEY:
            tasks.append(_brave_search(q))
        if TAVILY_API_KEY:
            tasks.append(_tavily_search(q))

    if not tasks:
        return []

    batches = await asyncio.gather(*tasks, return_exceptions=True)

    # Group results by provider for round-robin interleaving.
    by_provider: dict[str, list[dict]] = {
        "duckduckgo": [], "wikipedia": [], "brave": [], "tavily": [],
    }
    for batch in batches:
        if isinstance(batch, Exception) or not batch:
            continue
        for r in batch:
            by_provider.setdefault(r["provider"], []).append(r)

    logger.info(
        "Web search providers: DDG=%d, Wikipedia=%d, Brave=%d, Tavily=%d",
        len(by_provider["duckduckgo"]),
        len(by_provider["wikipedia"]),
        len(by_provider["brave"]),
        len(by_provider["tavily"]),
    )

    # Interleave so we don't let one provider starve the others.
    # Tavily first — its results are the highest-quality (AI-filtered for authoritative sources).
    merged: list[dict] = []
    seen_urls: set[str] = set()
    max_len = max((len(v) for v in by_provider.values()), default=0)
    for i in range(max_len):
        for provider in ("tavily", "brave", "duckduckgo", "wikipedia"):
            lst = by_provider.get(provider, [])
            if i < len(lst):
                r = lst[i]
                if r["url"] in seen_urls:
                    continue
                seen_urls.add(r["url"])
                merged.append(r)
    return merged
