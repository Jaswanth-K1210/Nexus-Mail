"""
Nexus Mail — Task 3: Email Summarization
Runs for every email. For meeting invitations, focuses on sender context.
"""

from app.ai_worker.ai_provider import ai_provider, TaskType
import structlog

logger = structlog.get_logger(__name__)

SUMMARISE_SYSTEM_PROMPT = """You are an AI email summarizer for Nexus Mail, a professional email assistant.

Create a concise, actionable summary of the email. Your summary should:
1. Be 2-3 sentences maximum
2. Highlight the key ask or information
3. Note any deadlines or time-sensitive elements
4. Include the sender's role/relationship context if identifiable

Respond in JSON format:
{
    "summary": "<2-3 sentence summary>",
    "key_topic": "<one phrase describing the main topic>",
    "time_sensitive": <true or false>,
    "deadline": "<deadline if mentioned, else null>"
}"""

SUMMARISE_MEETING_PROMPT = """You are an AI email summarizer for Nexus Mail.

This email is a MEETING INVITATION. Focus your summary on:
1. Who is the sender and what is their likely role/organization?
2. What is the meeting about — the purpose and context?
3. Is there any relevant history or urgency mentioned?
4. What preparation might be needed?

Respond in JSON format:
{
    "summary": "<2-3 sentence summary focusing on sender context and meeting purpose>",
    "key_topic": "<what the meeting is about>",
    "sender_context": "<any contextual info about the sender>",
    "time_sensitive": true,
    "deadline": "<proposed meeting date/time>"
}"""


async def summarise_email(
    subject: str,
    body: str,
    sender: str,
    is_meeting: bool = False,
) -> dict:
    """
    Task 3: Summarize the email content.
    Uses a specialized prompt for meeting invitations.
    """
    prompt = SUMMARISE_MEETING_PROMPT if is_meeting else SUMMARISE_SYSTEM_PROMPT

    user_prompt = f"""Summarize this email:

FROM: {sender}
SUBJECT: {subject}

BODY:
{body[:3000]}"""

    try:
        result = await ai_provider.complete_json(
            system_prompt=prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            task_type=TaskType.SUMMARIZATION,
        )

        logger.info("Email summarized", topic=result.get("key_topic", ""))
        return result

    except Exception as e:
        logger.error("Summarization failed", error=str(e))
        return {
            "summary": f"Email from {sender} about: {subject}",
            "key_topic": subject,
            "time_sensitive": False,
            "deadline": None,
        }
