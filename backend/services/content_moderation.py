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
                "Does this video contain any of the following? "
                "1) Full or partial nudity (genitals, bare breasts). Normal clothing like shorts, swimwear, or crop tops is NOT nudity. "
                "2) Explicit sexual acts "
                "3) Graphic real-world violence or gore (blood, open wounds, dead bodies). Cartoon violence or news footage is fine. "
                "4) Animal cruelty (animals being tortured or killed) "
                "5) Child sexual abuse material "
                "Respond with ONLY valid JSON: "
                '{"safe": true} or {"safe": false, "reason": "<brief reason>"}'
            ),
        })

        response = await _client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=100,
            system="You are a content safety classifier. Respond with JSON only. Only flag genuinely explicit or harmful content. Do NOT flag people wearing normal everyday clothing (shorts, swimwear, tank tops, etc).",
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
