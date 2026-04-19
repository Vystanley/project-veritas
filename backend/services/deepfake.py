"""Deepfake / AI-generated content detection via vision LLM."""

import base64
import json
import logging
from typing import List

import anthropic

from config import ANTHROPIC_API_KEY
from models import DeepfakeResult

logger = logging.getLogger(__name__)

_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


async def analyze_deepfake(frames: List[str], video_url: str) -> DeepfakeResult:
    """Analyze video frames for deepfake indicators using a vision LLM."""
    if not frames:
        return DeepfakeResult(
            is_deepfake=False, confidence=0, risk_level="low",
            analysis="No frames available for analysis.", indicators=[],
        )

    try:
        # Build content blocks: images + text prompt
        content: list = []
        for frame_path in frames[:3]:
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
                f"Analyze these {len(frames[:3])} frames from a social media video for "
                f"deepfake/AI-generation indicators. Video URL: {video_url}\n\n"
                "Provide your deepfake analysis in JSON format only."
            ),
        })

        system_msg = """You are an expert deepfake detection AI. Analyze video frames for signs of AI-generated or manipulated content.

Look for these indicators:
- Facial inconsistencies: asymmetry, blurred edges around face, unnatural skin texture
- Eye/mouth artifacts: irregular blinking, distorted teeth, lip-sync issues
- Lighting anomalies: inconsistent shadows, unnatural reflections, lighting direction mismatches
- Background glitches: warping, blending artifacts, inconsistent perspective
- Hair/ear artifacts: blurred boundaries, unnatural movement patterns
- Resolution inconsistencies: face sharper/blurrier than background
- Temporal artifacts: flickering, morphing between frames

RESPOND WITH VALID JSON ONLY:
{
    "is_deepfake": true/false,
    "confidence": <0-100 how confident you are in your assessment>,
    "risk_level": "low" | "medium" | "high",
    "analysis": "<2-3 sentence explanation of your findings>",
    "indicators": ["<list of specific indicators found or notable observations>"]
}

Be conservative — only flag as high risk if strong indicators are present. Many legitimate videos have minor artifacts from compression."""

        response = await _client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=512,
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
        return DeepfakeResult(
            is_deepfake=result.get("is_deepfake", False),
            confidence=result.get("confidence", 0),
            risk_level=result.get("risk_level", "low"),
            analysis=result.get("analysis", ""),
            indicators=result.get("indicators", []),
        )
    except Exception as e:
        logger.error(f"Deepfake analysis error: {e}")
        return DeepfakeResult(
            is_deepfake=False, confidence=0, risk_level="low",
            analysis="Deepfake analysis could not be completed.", indicators=[],
        )
