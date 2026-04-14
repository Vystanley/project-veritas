"""Reverse image search on a representative video frame.

Pipeline:
    1. Upload the frame (bytes) to imgbb → returns a short-lived public URL.
    2. Hand that URL to SerpApi's Google Lens engine → returns visual matches.
    3. Normalize the matches into a small list of {title, url, source, date, thumbnail}
       plus an `earliest_date` hint that the fact-checker can use to detect
       recycled/mis-contextualized footage.

Both steps are optional. Missing either key (IMGBB_API_KEY, SERPAPI_API_KEY)
disables the feature gracefully — the rest of the fact-check pipeline continues.
"""

from __future__ import annotations

import base64
import logging
import os
import re
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY", "").strip()
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY", "").strip()

# Keep the uploaded image around only long enough for SerpApi to fetch it.
# imgbb's `expiration` is in seconds; 600s = 10 min is plenty.
IMGBB_EXPIRATION_SECONDS = 600

# Max matches to keep from SerpApi. More than ~8 is noise for the LLM.
MAX_MATCHES = 8


async def _upload_to_imgbb(frame_path: str) -> Optional[str]:
    """Upload a local image file to imgbb and return its public URL."""
    if not IMGBB_API_KEY:
        return None
    try:
        with open(frame_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.imgbb.com/1/upload",
                params={"key": IMGBB_API_KEY, "expiration": IMGBB_EXPIRATION_SECONDS},
                data={"image": b64},
            )
        if resp.status_code != 200:
            logger.warning(f"imgbb upload failed: {resp.status_code} {resp.text[:200]}")
            return None
        data = resp.json()
        url = (data.get("data") or {}).get("url")
        if not url:
            logger.warning(f"imgbb response missing URL: {data}")
            return None
        return url
    except Exception as e:
        logger.warning(f"imgbb upload error: {e}")
        return None


async def _serpapi_google_lens(image_url: str) -> list[dict]:
    """Query SerpApi Google Lens for visual matches of the given image URL."""
    if not SERPAPI_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.get(
                "https://serpapi.com/search",
                params={
                    "engine": "google_lens",
                    "url": image_url,
                    "api_key": SERPAPI_API_KEY,
                },
            )
        if resp.status_code != 200:
            logger.warning(f"SerpApi Lens failed: {resp.status_code} {resp.text[:200]}")
            return []
        data = resp.json()
        # SerpApi's google_lens engine returns results under "visual_matches".
        matches = data.get("visual_matches") or []
        normalized = []
        for m in matches[:MAX_MATCHES]:
            normalized.append({
                "title": (m.get("title") or "").strip(),
                "url": (m.get("link") or "").strip(),
                "source": (m.get("source") or "").strip(),
                "date": (m.get("date") or "").strip(),
                "thumbnail": (m.get("thumbnail") or "").strip(),
            })
        return [m for m in normalized if m["url"]]
    except Exception as e:
        logger.warning(f"SerpApi Lens error: {e}")
        return []


_DATE_PATTERNS = [
    "%b %d, %Y",        # "Mar 14, 2023"
    "%B %d, %Y",        # "March 14, 2023"
    "%Y-%m-%d",
    "%d %b %Y",
    "%d %B %Y",
]


def _parse_date(s: str) -> Optional[datetime]:
    if not s:
        return None
    s = s.strip()
    for fmt in _DATE_PATTERNS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    # Fallback: pull out a 4-digit year
    m = re.search(r"(19|20)\d{2}", s)
    if m:
        try:
            return datetime(year=int(m.group()), month=1, day=1)
        except ValueError:
            pass
    return None


def _earliest_date(matches: list[dict]) -> Optional[str]:
    """Return the earliest parseable date across matches (ISO format) or None."""
    parsed = [d for d in (_parse_date(m.get("date", "")) for m in matches) if d]
    if not parsed:
        return None
    return min(parsed).date().isoformat()


async def reverse_image_search(frame_paths: list[str]) -> dict:
    """Run reverse image search on the middle frame of the video.

    Returns a dict with:
        {
          "enabled": bool,              # False if keys missing or no frames
          "frame_url": str | None,      # the public URL we searched on (for debugging)
          "matches": list[{title,url,source,date,thumbnail}],
          "earliest_date": str | None,  # ISO date of oldest match, if parseable
          "note": str,                  # human-readable summary
        }
    """
    if not frame_paths:
        return {"enabled": False, "matches": [], "earliest_date": None, "note": "No frames available."}

    if not IMGBB_API_KEY or not SERPAPI_API_KEY:
        missing = []
        if not IMGBB_API_KEY:
            missing.append("IMGBB_API_KEY")
        if not SERPAPI_API_KEY:
            missing.append("SERPAPI_API_KEY")
        return {
            "enabled": False,
            "matches": [],
            "earliest_date": None,
            "note": f"Reverse image search disabled (missing {', '.join(missing)}).",
        }

    # Pick the middle frame — usually the most "content-rich" shot, avoids title cards.
    frame = frame_paths[len(frame_paths) // 2]

    image_url = await _upload_to_imgbb(frame)
    if not image_url:
        return {
            "enabled": False,
            "matches": [],
            "earliest_date": None,
            "note": "Reverse image search skipped: frame upload failed.",
        }

    matches = await _serpapi_google_lens(image_url)
    earliest = _earliest_date(matches)

    if not matches:
        note = "No visual matches found on the public web."
    else:
        note = f"Found {len(matches)} visual matches."
        if earliest:
            note += f" Earliest match: {earliest}."

    logger.info(f"Reverse image search: {note}")
    return {
        "enabled": True,
        "frame_url": image_url,
        "matches": matches,
        "earliest_date": earliest,
        "note": note,
    }


def format_for_llm(result: dict) -> str:
    """Format reverse image search results as a text block the fact-checker LLM can read."""
    if not result.get("enabled") or not result.get("matches"):
        return ""
    lines = ["REVERSE IMAGE SEARCH (did this footage appear elsewhere on the web?):"]
    if result.get("earliest_date"):
        lines.append(
            f"- Earliest known appearance of this frame on the web: {result['earliest_date']}. "
            "If this predates the video's claimed date/event, the footage may be recycled or mis-contextualized."
        )
    for i, m in enumerate(result["matches"], 1):
        date = f" [{m['date']}]" if m.get("date") else ""
        source = f" ({m['source']})" if m.get("source") else ""
        lines.append(f"- Match {i}{source}{date}: {m['title']} — {m['url']}")
    return "\n".join(lines)
