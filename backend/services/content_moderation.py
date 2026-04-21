"""Pre-scan content moderation — rejects NSFW, graphic violence, and other inappropriate content.

Uses Claude Haiku vision (fast + cheap) to screen extracted frames BEFORE the
expensive fact-check pipeline runs. This saves API credits and protects the
platform from processing sensitive content.
"""

import base64
import json
import logging
from typing import List, Optional

import anthropic

from config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


async def check_content_safety(frames: List[str]) -> Optional[str]:
    """Screen frames for NSFW or violent content.

    Returns None if content is safe, or a rejection message string if the
    content should be blocked. Only checks up to 2 frames for speed.
    """
    if not frames:
        return None

    try:
        content: list = []
        for frame_path in frames[:2]:
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
                "Does this video contain ANY of the following extreme content? "
                "1) Pornography (explicit sexual acts, full nudity with visible genitals). "
                "   NOT porn: swimwear, shorts, crop tops, shirtless people, cleavage, dancing. "
                "2) Child sexual abuse material. "
                "3) Extreme graphic gore shown for shock value (close-up mutilation, torture). "
                "   NOT gore: war/military footage, news coverage, protests, fights, injuries, blood. "
                "IMPORTANT: This is a fact-checking app. Most videos are news, politics, and social media content. "
                "Military footage, conflict zones, protests, confrontations, and disturbing news events are ALL SAFE. "
                "Only flag actual pornography, CSAM, or extreme torture/mutilation content. "
                "When in doubt, mark it safe. "
                "Respond with ONLY valid JSON: "
                '{"safe": true} or {"safe": false, "reason": "<brief reason>"}'
            ),
        })

        response = await _client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=100,
            system="You are a content safety classifier for a fact-checking app. Respond with JSON only. Be very permissive. Only block actual pornography, CSAM, or extreme torture/gore content. News footage, military content, protests, fights, and people in any normal clothing are always safe.",
            messages=[{"role": "user", "content": content}],
        )

        response_text = response.content[0].text.strip()
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1] if lines[-1].strip().startswith("```") else lines[1:])

        result = json.loads(response_text)

        if not result.get("safe", True):
            reason = result.get("reason", "Inappropriate content detected")
            logger.warning(f"Content moderation blocked scan: {reason}")
            return f"This video was flagged for inappropriate content ({reason}). Veritas does not process videos containing explicit, violent, or otherwise sensitive material."

        return None

    except Exception as e:
        logger.warning(f"Content moderation check failed: {e}")
        # If moderation fails, let the scan proceed — don't block users
        # because of a transient error.
        return None
