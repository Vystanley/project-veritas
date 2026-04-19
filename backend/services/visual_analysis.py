"""Combined visual content analysis + deepfake detection in a single LLM call.

This feeds into the fact-checker so it can reason about on-screen text, graphs,
locations, people, and actions — not just the spoken transcript. Also checks
for deepfake / AI-generation indicators in the same pass, saving an API round trip.
"""

import base64
import json
import logging
from typing import List, Optional, Tuple

import anthropic

from config import ANTHROPIC_API_KEY
from models import DeepfakeResult

logger = logging.getLogger(__name__)

# Reuse a single async client across calls (connection pooling).
_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


async def analyze_visual_and_deepfake(
    frames: List[str], video_url: str
) -> Tuple[Optional[str], DeepfakeResult]:
    """Combined visual description + deepfake analysis in ONE LLM call.

    Returns (visual_description, deepfake_result). On failure, returns
    (None, default_deepfake_result) so the pipeline can continue.
    """
    default_deepfake = DeepfakeResult(
        is_deepfake=False, confidence=0, risk_level="low",
        analysis="Visual analysis could not be completed.", indicators=[],
    )
    if not frames:
        return None, default_deepfake

    try:
        # Build the content blocks: images first, then the text prompt.
        content: list = []
        for frame_path in frames[:5]:
            with open(frame_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": b64,
                },
            })

        content.append({
            "type": "text",
            "text": (
                f"Analyze these {len(frames[:5])} frames from a social media video "
                f"({video_url}). Provide both visual description and deepfake analysis in JSON."
            ),
        })

        system_msg = """You are a combined visual analyst and deepfake detector for a fact-checking system.
You will receive frames from a social media video. You must do TWO tasks in a SINGLE response:

TASK 1 — VISUAL DESCRIPTION:
Describe everything factually relevant shown in the frames. Focus on things that could be true/false.
Cover: on-screen text (captions, overlays, headlines — transcribe exactly), visual claims (graphs,
stats, quoted figures), people (identify public figures if recognizable), location/setting, actions/events,
and context clues (timestamps, logos, platform indicators).
Rules: be precise and neutral, don't editorialize, keep to 150-250 words, plain text.

TASK 2 — DEEPFAKE CHECK:
Analyze the same frames for signs of AI-generated or manipulated content.
Look for: facial inconsistencies, eye/mouth artifacts, lighting anomalies, background glitches,
hair/ear artifacts, resolution inconsistencies, temporal artifacts between frames.
Be conservative — only flag as high risk if strong indicators are present.

RESPOND WITH VALID JSON ONLY:
{
    "visual_description": "<plain text description from Task 1>",
    "deepfake": {
        "is_deepfake": true/false,
        "confidence": <0-100>,
        "risk_level": "low" | "medium" | "high",
        "analysis": "<2-3 sentence explanation>",
        "indicators": ["<list of specific indicators or observations>"]
    }
}"""

        response = await _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_msg,
            messages=[{"role": "user", "content": content}],
        )

        response_text = response.content[0].text.strip()
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            start = 1
            end = len(lines) - 1 if lines[-1].strip().startswith("```") else len(lines)
            response_text = "\n".join(lines[start:end])

        result = json.loads(response_text)

        # Extract visual description
        visual_desc = result.get("visual_description")
        if visual_desc and len(visual_desc.strip()) < 20:
            visual_desc = None

        # Extract deepfake result
        df = result.get("deepfake", {})
        deepfake_result = DeepfakeResult(
            is_deepfake=df.get("is_deepfake", False),
            confidence=df.get("confidence", 0),
            risk_level=df.get("risk_level", "low"),
            analysis=df.get("analysis", ""),
            indicators=df.get("indicators", []),
        )

        logger.info(f"Combined visual+deepfake analysis: {len(visual_desc or '')} chars description, risk={deepfake_result.risk_level}")
        return visual_desc, deepfake_result

    except Exception as e:
        logger.warning(f"Combined visual+deepfake analysis failed: {e}")
        return None, default_deepfake


# Keep the old function signature for backwards compatibility if needed elsewhere.
async def analyze_visual_content(frames: List[str], video_url: str) -> Optional[str]:
    """Legacy wrapper — returns just the visual description."""
    desc, _ = await analyze_visual_and_deepfake(frames, video_url)
    return desc
