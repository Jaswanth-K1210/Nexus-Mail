"""
Nexus Mail — Task 6: Reply Draft Generation
Generates AI-drafted replies using the user's tone profile.
For meeting invitations, pre-generates BOTH acceptance and decline drafts.
Per v3.1 spec: both drafts stored, correct one used when user decides.
"""

from app.ai_worker.ai_provider import ai_provider
import structlog

logger = structlog.get_logger(__name__)

REPLY_DRAFT_PROMPT = """You are an AI email reply assistant for Nexus Mail.

Draft a professional reply to this email. Match the user's communication style based on their tone profile.

Tone Profile (if available):
{tone_profile}

Rules:
- Match the formality level of the original email
- Be concise — 2-4 sentences unless the context requires more
- Address the key points raised in the email
- Do not make commitments the user hasn't approved
- Sound natural, not robotic

Respond in JSON format:
{{
    "reply_draft": "<the drafted reply text>",
    "tone": "<formal | semi-formal | casual>",
    "confidence": <0.0-1.0 how confident this reply is appropriate>
}}"""

MEETING_REPLY_PROMPT = """You are an AI email reply assistant for Nexus Mail.

Generate TWO reply drafts for this meeting invitation:
1. An ACCEPTANCE reply
2. A DECLINE reply

Use the user's tone profile to match their communication style.

Tone Profile (if available):
{tone_profile}

Rules for ACCEPTANCE:
- Thank the sender for the invitation
- Confirm the date/time
- Express enthusiasm appropriately (match the user's style)
- Keep it brief — 2-3 sentences

Rules for DECLINE:
- Thank the sender politely
- Express regret that the time doesn't work
- Be gracious without over-explaining
- Keep it brief — 2-3 sentences

Respond in JSON format:
{{
    "accept_draft": "<acceptance reply text>",
    "decline_draft": "<decline reply text>",
    "tone": "<formal | semi-formal | casual>",
    "confidence": <0.0-1.0>
}}"""


async def generate_reply_draft(
    subject: str,
    body: str,
    sender: str,
    sender_name: str,
    is_meeting: bool = False,
    tone_profile: dict | None = None,
    availability: str | None = None,
) -> dict:
    """
    Task 6: Generate reply draft(s).
    For meetings: generates both accept and decline drafts.
    For regular emails: generates a single contextual reply.
    """
    tone_str = str(tone_profile) if tone_profile else "No tone profile available — use a professional, friendly tone."

    if is_meeting:
        prompt = MEETING_REPLY_PROMPT.format(tone_profile=tone_str)
        availability_context = f"\nUser's calendar status: {availability}" if availability else ""

        user_prompt = f"""Generate acceptance and decline reply drafts for this meeting invitation:

FROM: {sender_name} <{sender}>
SUBJECT: {subject}
{availability_context}

BODY:
{body[:2000]}"""
    else:
        prompt = REPLY_DRAFT_PROMPT.format(tone_profile=tone_str)
        user_prompt = f"""Draft a reply to this email:

FROM: {sender_name} <{sender}>
SUBJECT: {subject}

BODY:
{body[:2000]}"""

    try:
        result = await ai_provider.complete_json(
            system_prompt=prompt,
            user_prompt=user_prompt,
            temperature=0.4,
        )

        logger.info(
            "Reply draft generated",
            is_meeting=is_meeting,
            tone=result.get("tone", ""),
        )

        return result

    except Exception as e:
        logger.error("Reply draft generation failed", error=str(e))
        if is_meeting:
            return {
                "accept_draft": f"Hi {sender_name}, thank you for the invitation. I'd be happy to attend. Looking forward to it!",
                "decline_draft": f"Hi {sender_name}, thank you for the invitation. Unfortunately, I won't be able to make it at that time. I appreciate you reaching out.",
                "tone": "semi-formal",
                "confidence": 0.3,
            }
        return {
            "reply_draft": f"Hi {sender_name}, thank you for your email. I will get back to you on this shortly.",
            "tone": "semi-formal",
            "confidence": 0.3,
        }
