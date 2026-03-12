"""
Nexus Mail — Task 1: Email Classification
Classifies emails into 8 categories and sets the is_meeting_invitation flag.
Runs for every email.
"""

from app.ai_worker.ai_provider import ai_provider, TaskType
from app.ai_worker.utils import sanitize_for_prompt
import structlog

logger = structlog.get_logger(__name__)

CLASSIFY_SYSTEM_PROMPT = """You are an expert email classifier for a professional email assistant called Nexus Mail.

Use the USER PERSONA PROFILE (if provided) to personalize the classification and Suggested Action based on who the user is and what they likely care about.
- Elevate the priority and Suggested Action for emails directly relevant to their job role.
- Downgrade standard/generic emails to "LOW RELEVANCE" or "AUTO-ARCHIVE" if it contradicts their role (e.g., sales pitches to a developer).

Classify the email into EXACTLY ONE of these 8 categories:
1. "important" — Urgent emails from known contacts, important business updates, action-required items, direct messages from colleagues, peers, or investors.
2. "requires_response" — Emails that explicitly ask for a reply or input from the user
3. "meeting_invitation" — Emails proposing a meeting, call, sync, demo, interview, or containing .ics attachments
4. "newsletter" — Periodic updates, blog digests, subscription content
5. "promotional" — Marketing emails, sales offers, product announcements
6. "social" — EXACTLY social media notifications (LinkedIn, Twitter, etc), connection requests. DO NOT put peer-to-peer emails from real people discussing work here.
7. "transactional" — Receipts, order confirmations, shipping updates, password resets
8. "spam" — Junk, phishing attempts, suspicious content

For meeting detection, look for AT LEAST TWO of these signals:
- Subject contains: meeting, call, sync, catch up, interview, demo, discussion, let's connect, availability
- Body contains a specific date/time: "Thursday at 3pm", "March 10th, 10:30 AM"
- Body contains a meeting link: Zoom, Google Meet, Teams, Calendly URL
- Body asks about availability: "are you available", "does this time work", "when are you free"
- Email has a .ics calendar attachment

IMPORTANT: If the email has a .ics attachment, ALWAYS classify as "meeting_invitation" regardless of other signals.

Analyze the email and also provide a Suggested Action. It must be EXACTLY ONE of these 4 verdicts:
1. "ACTION REQUIRED" (User must write a reply, click a link to approve something, pay an invoice, or schedule a meeting).
2. "REVIEW ONLY" (Important information from a boss or client, system alerts requiring awareness, but no direct reply is needed).
3. "LOW RELEVANCE" (Newsletters, generic updates, social notifications — safe to skim and ignore).
4. "AUTO-ARCHIVE" (Cold sales emails, pure promotional spam, or noise the user should delete without reading).

Respond in plain text exactly in this format (no json, no quotes):
Category: <one of the 8 categories>
Suggested Action: <one of the 4 actions>
Severity: <1-5 integer>
Is Meeting Invitation: <true or false>
Confidence: <0.0-1.0>
Reasoning: <brief explanation>"""


async def classify_email(subject: str, body: str, sender: str, has_ics: bool = False, user_persona: str = "") -> dict:
    """
    Task 1: Classify an email into one of 8 categories.
    Also sets the is_meeting_invitation flag.
    """
    user_prompt = f"""Classify this email:

FROM: {sanitize_for_prompt(sender, 200)}
SUBJECT: {sanitize_for_prompt(subject, 500)}
HAS .ICS ATTACHMENT: {has_ics}
USER PERSONA PROFILE: {user_persona}

BODY:
{sanitize_for_prompt(body, 3000)}"""

    try:
        result = await ai_provider.complete_text_kv(
            system_prompt=CLASSIFY_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
            task_type=TaskType.CLASSIFICATION,
        )

        # Validate the response
        valid_categories = [
            "important", "requires_response", "meeting_invitation",
            "newsletter", "promotional", "social", "transactional", "spam"
        ]

        category = result.get("category", "important").lower()
        if category not in valid_categories:
            category = "important"

        try:
            severity = max(1, min(5, int(result.get("severity", "3"))))
        except ValueError:
            severity = 3
            
        # Handle string "true" / "false"
        is_meeting_str = result.get("is meeting invitation", "false").lower()
        is_meeting = is_meeting_str == "true"

        # Override: .ics attachment always means meeting
        if has_ics:
            is_meeting = True
            category = "meeting_invitation"

        try:
            confidence = float(result.get("confidence", "0"))
        except ValueError:
            confidence = 0.0

        suggested_action = result.get("suggested action", "REVIEW ONLY").upper()
        valid_actions = ["ACTION REQUIRED", "REVIEW ONLY", "LOW RELEVANCE", "AUTO-ARCHIVE"]
        if suggested_action not in valid_actions:
            suggested_action = "REVIEW ONLY"

        logger.info(
            "Email classified",
            category=category,
            suggested_action=suggested_action,
            severity=severity,
            is_meeting=is_meeting,
            confidence=confidence,
        )

        return {
            "category": category,
            "suggested_action": suggested_action,
            "severity": severity,
            "is_meeting_invitation": is_meeting,
            "confidence": confidence,
            "reasoning": result.get("reasoning", ""),
        }

    except Exception as e:
        logger.error("Classification failed", error=str(e))
        return {
            "category": "important",
            "suggested_action": "REVIEW ONLY",
            "severity": 3,
            "is_meeting_invitation": has_ics,
            "confidence": 0.0,
            "reasoning": f"Classification failed: {str(e)}",
        }
