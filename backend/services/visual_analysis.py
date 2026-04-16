"""Visual content analysis — describes what's shown in the video frames.

This feeds into the fact-checker so it can reason about on-screen text, graphs,
locations, people, and actions — not just the spoken transcript.
"""

import base64
import logging
import uuid
from typing import List, Optional

from emergentintegrations.llm.chat import ImageContent, LlmChat, UserMessage

from config import EMERGENT_LLM_KEY

logger = logging.getLogger(__name__)


async def analyze_visual_content(frames: List[str], video_url: str) -> Optional[str]:
    """Describe visual content of a video for fact-checking context.

    Returns a plain-text description covering on-screen text, visible factual
    claims (graphs, stats, headlines), people/locations/objects, and actions.
    Returns None on failure so the pipeline can continue with transcript only.
    """
    if not frames:
        return None

    try:
        image_contents = []
        for frame_path in frames[:5]:
            with open(frame_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                image_contents.append(ImageContent(image_base64=b64))

        system_msg = """You are a meticulous visual analyst supporting a fact-checking system.

Your job: describe everything factually relevant shown in the video frames so a fact-checker
can verify both spoken and visual claims. Focus on things that could be true/false.

Report in these sections, only including sections that apply:

ON-SCREEN TEXT: Transcribe ALL visible text exactly — captions, overlays, chyrons, headlines,
watermarks, usernames, handles, subtitles, and any text on signs/screens/documents. Preserve
numbers, dates, percentages, and names verbatim.

VISUAL CLAIMS: Any factual assertion shown visually — graphs, charts, statistics, comparisons,
quoted figures, news tickers, document excerpts. State what claim the visual is making.

PEOPLE: Describe visible people — identifiable public figures by name if recognizable,
otherwise describe them neutrally (apparent role, uniform, setting). Do NOT invent identities.

LOCATION / SETTING: Where does this appear to take place? Any recognizable landmarks, flags,
signage, news studios, logos, environment clues.

ACTIONS / EVENTS: What is happening? Is someone speaking at a podium, a crowd marching,
footage of an incident, a product demo, etc.

CONTEXT CLUES: Date/time stamps visible, broadcast network logos, social media platform
indicators, any signs this is archival vs. live footage, edited vs. raw, etc.

Rules:
- Be precise and neutral. Do NOT editorialize or fact-check yourself — just describe.
- If you cannot read text clearly, say "partially visible" rather than guessing.
- If a section doesn't apply, omit it.
- Keep it to 150-300 words total.
- Plain text, no markdown, no JSON."""

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"visual-{uuid.uuid4()}",
            system_message=system_msg,
        )
        chat.with_model("anthropic", "claude-sonnet-4-6")

        user_msg = UserMessage(
            text=(
                f"Describe the visual content of these {len(image_contents)} frames from a "
                f"social media video ({video_url}) for fact-checking context."
            ),
            file_contents=image_contents,
        )
        response = await chat.send_message(user_msg)
        description = response.strip()
        if description:
            logger.info(f"Visual analysis: {len(description)} chars")
            return description
        return None
    except Exception as e:
        logger.warning(f"Visual analysis failed: {e}")
        return None
