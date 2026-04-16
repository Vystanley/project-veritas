"""Web-augmented transcript fact-checking and background job runner."""

import asyncio
import json
import logging
import re
import shutil
import tempfile
import uuid
from datetime import datetime, timezone

from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import HTTPException

from config import EMERGENT_LLM_KEY
from jobs import FactCheckJob
from models import ClaimResult, DeepfakeResult, FactCheckResponse, ReverseImageResult
from services.deepfake import analyze_deepfake
from services.visual_analysis import analyze_visual_and_deepfake
from services.reverse_image_search import (
    reverse_image_search,
    format_for_llm as format_reverse_image_for_llm,
)
from services.web_search import multi_provider_search
from services.subscription import log_scan
from services.video import (
    download_subtitles,
    download_video,
    extract_audio,
    extract_frames,
    transcribe_audio,
)

logger = logging.getLogger(__name__)


async def extract_search_queries(transcript: str) -> list:
    """Use LLM to extract 3-5 focused search queries from a video transcript for fact-checking."""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"search-{uuid.uuid4()}",
            system_message=(
                "You extract search queries from video transcripts. Output ONLY a JSON array of "
                "3-5 short, specific search queries that would help fact-check the claims in the "
                "transcript. Focus on people's names, events, titles, specific facts, and recent "
                "news. Keep each query under 8 words. Output valid JSON array only, no other text."
            ),
        )
        chat.with_model("anthropic", "claude-haiku-4-5")
        msg = UserMessage(text=f"Extract search queries for fact-checking this transcript:\n\n{transcript[:800]}")
        response = await chat.send_message(msg)
        text = response.strip() if isinstance(response, str) else response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        queries = json.loads(text)
        if isinstance(queries, list):
            logger.info(f"Extracted search queries: {queries}")
            return [q for q in queries if isinstance(q, str) and len(q) > 3]
        return []
    except Exception as e:
        logger.warning(f"Failed to extract search queries: {e}")
        words = transcript[:600]
        phrases = set()
        for match in re.findall(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+", words):
            phrases.add(match)
        for match in re.findall(
            r"(?:secretary of \w+|president \w+|minister \w+|\w+ navy|\w+ army)",
            words,
            re.IGNORECASE,
        ):
            phrases.add(match)
        return list(phrases)[:5] if phrases else [words[:100]]


async def search_web_context(transcript: str) -> tuple[str, list[dict]]:
    """Search the web for current information related to the transcript/visual claims.

    Returns a tuple of (formatted_context_string, structured_sources_list).
    Each structured source has: id (S1, S2...), title, url, description, date.
    This lets the fact-checker cite sources by ID so we can validate URLs aren't fabricated.
    """
    try:
        search_queries = await extract_search_queries(transcript)
        all_results = await multi_provider_search(search_queries)

        if not all_results:
            logger.warning("Web search returned no results for any query (all providers)")
            return "", []

        sources = []
        for r in all_results:
            title = (r.get("title") or "").strip()
            href = (r.get("url") or "").strip()
            body = (r.get("body") or "").strip()
            date = (r.get("date") or "").strip()
            if not href:
                continue
            sources.append({
                "id": f"S{len(sources) + 1}",
                "title": title or href,
                "url": href,
                "description": body,
                "date": date,
            })
            if len(sources) >= 12:
                break

        context_parts = []
        for s in sources:
            date_str = f" [{s['date']}]" if s["date"] else ""
            context_parts.append(
                f"[{s['id']}] {s['title']}{date_str}: {s['description']} (URL: {s['url']})"
            )
        web_context = "\n".join(context_parts)

        logger.info(f"Web search returned {len(sources)} unique sources for fact-checking")
        return web_context, sources
    except Exception as e:
        logger.warning(f"Web search failed: {e}")
        return "", []


async def fact_check_transcript(
    transcript: str,
    video_url: str,
    visual_description: str | None = None,
    reverse_image: dict | None = None,
    web_context_override: tuple | None = None,
) -> dict:
    """Analyze transcript + visual content for fact-checking, enhanced with real-time web search."""
    try:
        # Use pre-fetched web context if available, otherwise search now.
        if web_context_override:
            web_context, web_sources = web_context_override
        else:
            search_text = transcript
            if visual_description:
                search_text = f"{transcript}\n\n{visual_description}"
            web_context, web_sources = await search_web_context(search_text)

        reverse_image_block = format_reverse_image_for_llm(reverse_image or {})

        today_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

        # Build the ID-indexed source pool the LLM is allowed to cite.
        source_pool_text = ""
        allowed_ids = set()
        if web_sources:
            allowed_ids = {s["id"] for s in web_sources}
            source_pool_text = (
                "AVAILABLE SOURCES (the ONLY sources you are allowed to cite — reference them by their ID):\n"
                + web_context
                + "\n\nIf no available source supports a claim, leave its `sources` array empty. "
                "DO NOT invent URLs, outlet names, or citations. Never hallucinate sources."
            )

        web_section = ""
        if web_context:
            web_section = f"""
REAL-TIME WEB SEARCH RESULTS (retrieved today, {today_str}):
{source_pool_text}

Use these results as your PRIMARY source of truth for current events. Your training data may be outdated. If the web results confirm a claim that you might otherwise doubt, trust the web results."""

        system_message = f"""You are Veritas, an expert AI fact-checker. Today's date is {today_str}. Analyze social media videos for truthfulness using BOTH the spoken transcript and a description of what is visible on screen.

CRITICAL: Your training data has a knowledge cutoff. You MUST rely on the real-time web search results provided below for any claims about recent or current events. Do NOT mark claims as false simply because they occurred after your training cutoff.

You must consider ALL claims — spoken AND visual (on-screen text, captions, graphs, chyrons, headlines, documents shown on camera). A video can assert something with a text overlay even when it's not spoken aloud. Treat on-screen text claims with the same weight as spoken claims.

CITATION RULES (strict):
- You may ONLY cite sources from the AVAILABLE SOURCES list below, using their IDs (e.g. "S1", "S3").
- If a claim is supported by one of the available sources, put its ID(s) into the claim's `sources` array, like: "sources": ["S2", "S5"].
- If NO available source supports a claim, leave `sources` as an empty array []. Do NOT fabricate URLs or invent outlet names.
- Never include raw URLs in the `sources` array — only the ID strings from the list.
{web_section}

RESPOND WITH VALID JSON ONLY:
{{
    "overall_verdict": "True" | "Mostly True" | "Partially True" | "Mostly False" | "False",
    "confidence_score": <0-100>,
    "summary": "<2-3 sentence summary>",
    "claims": [{{"claim":"<claim>","verdict":"<verdict>","explanation":"<explanation>","sources":["S1","S3"]}}]
}}

For each claim, note in the explanation whether it came from spoken audio, on-screen text, or both. Be thorough and fair. Identify all factual claims. ONLY output valid JSON."""

        visual_section = ""
        if visual_description:
            visual_section = f"\n\nVISUAL CONTENT (what's shown on screen):\n---\n{visual_description}\n---"

        reverse_image_section = ""
        if reverse_image_block:
            reverse_image_section = f"\n\n{reverse_image_block}\n"

        user_text = (
            f"Fact-check this video ({video_url}).\n\n"
            f"SPOKEN TRANSCRIPT:\n---\n{transcript}\n---"
            f"{visual_section}"
            f"{reverse_image_section}\n"
            "Identify every factual claim from both sources. If the reverse image search "
            "suggests the footage was recycled or mis-contextualized, call that out explicitly "
            "in the summary and in an appropriate claim's explanation. JSON response only."
        )

        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"factcheck-{uuid.uuid4()}", system_message=system_message)
        chat.with_model("anthropic", "claude-sonnet-4-6")
        response = await chat.send_message(UserMessage(text=user_text))
        response_text = response.strip()
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1] if lines[-1].strip().startswith("```") else lines[1:])
        parsed = json.loads(response_text)

        # --- Citation gating: resolve source IDs to real URLs, drop fabricated ones ---
        source_by_id = {s["id"]: s for s in web_sources}
        # Also accept exact URL matches for backwards compatibility with any slip-ups.
        source_by_url = {s["url"]: s for s in web_sources}

        cited_ids: list[str] = []
        for claim in parsed.get("claims", []) or []:
            raw_refs = claim.get("sources", []) or []
            resolved_urls: list[str] = []
            for ref in raw_refs:
                if not isinstance(ref, str):
                    continue
                ref = ref.strip()
                if not ref:
                    continue
                src = source_by_id.get(ref) or source_by_url.get(ref)
                if src:
                    if src["url"] not in resolved_urls:
                        resolved_urls.append(src["url"])
                    if src["id"] not in cited_ids:
                        cited_ids.append(src["id"])
                else:
                    # Fabricated or unknown — drop it, log so we can tune.
                    logger.info(f"Dropped fabricated source citation: {ref!r}")
            claim["sources"] = resolved_urls

        # Build top-level `sources` list from the web sources that were actually cited.
        # Preserve original discovery order; if nothing was cited, fall back to the top 5 for context.
        cited_set = set(cited_ids)
        top_sources = [s for s in web_sources if s["id"] in cited_set]
        if not top_sources:
            top_sources = web_sources[:5]
        parsed["sources"] = [
            {"title": s["title"], "url": s["url"], "description": s["description"]}
            for s in top_sources
        ]

        return parsed
    except json.JSONDecodeError:
        return {
            "overall_verdict": "Unable to Determine",
            "confidence_score": 0,
            "summary": "Analysis failed. Please try again.",
            "claims": [],
            "sources": [],
        }
    except Exception as e:
        logger.error(f"Fact-check error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze content: {str(e)}")


async def process_fact_check_background(job: FactCheckJob):
    """Run the entire fact-check pipeline in the background with progress updates."""
    temp_dir = tempfile.mkdtemp()
    try:
        job.status = "processing"
        job.progress = 5
        job.progress_message = "Checking for subtitles..."
        await job.save()

        transcript = None
        deepfake_result = None
        visual_description = None
        reverse_image_data = None

        # --- Try subtitles FIRST (fast metadata fetch, no video download) ---
        early_web_context = None   # will hold (web_context, web_sources) if available early
        try:
            sub_transcript = await download_subtitles(job.video_url, temp_dir)
            if sub_transcript and len(sub_transcript.strip()) >= 10:
                transcript = sub_transcript
                logger.info(f"Got subtitle transcript early: {len(transcript)} chars")
        except Exception as e:
            logger.warning(f"Early subtitle download failed: {e}")

        # If we got subtitles, kick off web search NOW — it runs while video downloads.
        early_web_task = None
        if transcript:
            early_web_task = asyncio.create_task(search_web_context(transcript))

        job.progress = 10
        job.progress_message = "Downloading video..."
        await job.save()

        video_path = None
        try:
            video_path = await download_video(job.video_url, temp_dir)
        except Exception as e:
            logger.exception(f"Video download exception: {type(e).__name__}: {e}")

        if video_path:
            logger.info("Video downloaded — running full analysis pipeline")

            job.progress = 20
            job.progress_message = "Extracting frames & audio..."
            await job.save()

            # Extract frames ONCE and share between deepfake + visual analysis
            try:
                frames = await extract_frames(video_path, temp_dir, num_frames=5)
            except Exception as e:
                logger.warning(f"Frame extraction failed: {e}")
                frames = []

            async def run_visual_and_deepfake():
                """Combined visual description + deepfake in ONE LLM call."""
                if not frames:
                    return None, None
                try:
                    return await analyze_visual_and_deepfake(frames, job.video_url)
                except Exception as e:
                    logger.warning(f"Combined visual+deepfake failed: {e}")
                    return None, None

            async def run_transcription():
                # Skip audio transcription if we already have subtitles
                if transcript and len(transcript.strip()) >= 10:
                    logger.info("Skipping audio transcription — already have subtitles")
                    return transcript
                try:
                    audio_path = await extract_audio(video_path, temp_dir)
                    return await transcribe_audio(audio_path, temp_dir)
                except Exception as e:
                    logger.warning(f"Audio extraction/transcription failed: {e}")
                    return None

            async def run_reverse_image():
                if not frames:
                    return None
                try:
                    return await reverse_image_search(frames)
                except Exception as e:
                    logger.warning(f"Reverse image search failed: {e}")
                    return None

            job.progress = 30
            job.progress_message = "Reading screen, checking for deepfakes & recycled footage..."
            await job.save()

            visual_df_task = asyncio.create_task(run_visual_and_deepfake())
            transcription_task = asyncio.create_task(run_transcription())
            reverse_image_task = asyncio.create_task(run_reverse_image())
            (visual_description, deepfake_result), transcript, reverse_image_data = await asyncio.gather(
                visual_df_task, transcription_task, reverse_image_task
            )

            job.progress = 55
            job.progress_message = "Audio + visual analysis complete..."
            await job.save()
        else:
            logger.info("Video download failed — subtitle-only mode")
            job.progress = 20
            job.progress_message = "Video download failed, using subtitles..."
            await job.save()

        has_transcript = bool(transcript and len(transcript.strip()) >= 10)
        has_visual = bool(visual_description and len(visual_description.strip()) >= 40)

        # If we have neither spoken content nor visual content, we can't fact-check anything.
        if not has_transcript and not has_visual:
            job.status = "failed"
            job.error = (
                "Could not extract speech, captions, or readable visual content from this video. "
                "The platform may be blocking downloads from our server, or the video has no "
                "analyzable content."
            )
            await job.save()
            return

        # If transcript is missing but we have visual content, proceed with a placeholder so the
        # fact-checker still runs against on-screen text and visible claims. Be explicit about
        # what happened so users don't assume the video was silent when it wasn't.
        if not has_transcript:
            transcript = (
                "(Speech recognition couldn't parse the audio on this video. This usually "
                "happens when background music drowns out the speech, the audio is heavily "
                "compressed, or the speaker isn't in English. Fact-checking proceeded using "
                "on-screen text and visual content instead.)"
            )

        if not deepfake_result:
            deepfake_result = DeepfakeResult(
                is_deepfake=False, confidence=0, risk_level="unknown",
                analysis=(
                    "Deepfake analysis was skipped because the video file could not be "
                    "downloaded. Only the transcript/captions were analyzed."
                ),
                indicators=[],
            )

        # Collect early web search results if available, otherwise search now.
        web_context_override = None
        if early_web_task:
            try:
                early_web_context = await early_web_task
                if early_web_context and early_web_context[1]:
                    web_context_override = early_web_context
                    logger.info("Using early web search results (ran in parallel with video analysis)")
            except Exception as e:
                logger.warning(f"Early web search failed: {e}")

        job.progress = 65
        job.progress_message = "Searching web for context..." if not web_context_override else "AI analyzing claims..."
        await job.save()

        job.progress = 75
        job.progress_message = "AI analyzing claims..."
        await job.save()

        result = await fact_check_transcript(
            transcript, job.video_url, visual_description, reverse_image_data,
            web_context_override=web_context_override,
        )

        job.progress = 95
        job.progress_message = "Compiling results..."
        await job.save()

        check_id = str(uuid.uuid4())
        claims = [
            ClaimResult(
                claim=c.get("claim", ""),
                verdict=c.get("verdict", "Unknown"),
                explanation=c.get("explanation", ""),
                sources=c.get("sources", []),
            )
            for c in result.get("claims", [])
        ]

        reverse_image_obj = None
        if reverse_image_data:
            reverse_image_obj = ReverseImageResult(
                enabled=reverse_image_data.get("enabled", False),
                frame_url=reverse_image_data.get("frame_url"),
                matches=reverse_image_data.get("matches", []) or [],
                earliest_date=reverse_image_data.get("earliest_date"),
                note=reverse_image_data.get("note", ""),
            )

        response_data = FactCheckResponse(
            id=check_id,
            overall_verdict=result.get("overall_verdict", "Unable to Determine"),
            confidence_score=result.get("confidence_score", 0),
            summary=result.get("summary", ""),
            transcript=transcript,
            visual_description=visual_description,
            claims=claims,
            sources=result.get("sources", []),
            deepfake=deepfake_result,
            reverse_image=reverse_image_obj,
            video_url=job.video_url,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        await log_scan(job.user_id, job.video_url, check_id)

        job.progress = 100
        job.progress_message = "Analysis complete!"
        job.status = "completed"
        job.result = response_data.dict()
        await job.save()

    except HTTPException as he:
        job.status = "failed"
        job.error = str(he.detail)
        await job.save()
    except Exception as e:
        logger.error(f"Background fact-check error: {e}", exc_info=True)
        job.status = "failed"
        job.error = f"Analysis failed: {str(e)}"
        await job.save()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
