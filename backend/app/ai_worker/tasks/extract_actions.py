"""
Nexus Mail — Task 4: Action Item Extraction
Extracts actionable items from emails.
For meeting invitations, primary action is Accept/Decline decision.
"""

from app.ai_worker.ai_provider import ai_provider
import structlog

logger = structlog.get_logger(__name__)

EXTRACT_ACTIONS_PROMPT = """You are an AI action item extractor for Nexus Mail.

Extract all actionable items from the email. An action item is something the recipient needs to DO.

Respond in JSON format:
{
    "action_items": [
        {
            "action": "<description of what needs to be done>",
            "priority": "<high | medium | low>",
            "deadline": "<deadline if mentioned, else null>",
            "type": "<reply | review | approve | schedule | other>"
        }
    ],
    "requires_response": <true or false>,
    "response_urgency": "<immediate | today | this_week | whenever | none>"
}"""

EXTRACT_MEETING_ACTIONS_PROMPT = """You are an AI action item extractor for Nexus Mail.

This email is a MEETING INVITATION. The primary action is the Accept/Decline decision.
Also extract any secondary actions mentioned in the email body.

Respond in JSON format:
{
    "action_items": [
        {
            "action": "Respond to meeting invitation (Accept/Decline/Suggest alternative)",
            "priority": "high",
            "deadline": "<proposed meeting date>",
            "type": "schedule"
        }
    ],
    "requires_response": true,
    "response_urgency": "today"
}

Add any additional action items from the email body (e.g., "prepare slides", "review document before meeting")."""


async def extract_actions(
    subject: str,
    body: str,
    sender: str,
    is_meeting: bool = False,
) -> dict:
    """
    Task 4: Extract actionable items from the email.
    Uses specialized prompt for meetings.
    """
    prompt = EXTRACT_MEETING_ACTIONS_PROMPT if is_meeting else EXTRACT_ACTIONS_PROMPT

    user_prompt = f"""Extract action items from this email:

FROM: {sender}
SUBJECT: {subject}

BODY:
{body[:3000]}"""

    try:
        result = await ai_provider.complete_json(
            system_prompt=prompt,
            user_prompt=user_prompt,
            temperature=0.2,
        )

        action_items = result.get("action_items", [])
        logger.info("Actions extracted", count=len(action_items))

        return result

    except Exception as e:
        logger.error("Action extraction failed", error=str(e))
        return {
            "action_items": [],
            "requires_response": False,
            "response_urgency": "none",
        }
