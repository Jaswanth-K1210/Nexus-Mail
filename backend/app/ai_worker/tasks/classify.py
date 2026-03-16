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


async def classify_email(
    subject: str,
    body: str,
    sender: str,
    has_ics: bool = False,
    user_persona: str = "",
    user_role: str | None = None,
) -> dict:
    """
    Task 1: Classify an email.
    If user_role is set, uses role-specific categories (up to ~15).
    Otherwise falls back to the default 8-category prompt.
    """
    from app.ai_worker.role_categories import get_role_prompt, get_role_categories, VALID_ROLES

    # Pick the right system prompt and valid categories
    if user_role and user_role in VALID_ROLES:
        system_prompt = get_role_prompt(user_role)
        valid_categories = get_role_categories(user_role)
    else:
        system_prompt = CLASSIFY_SYSTEM_PROMPT
        valid_categories = [
            "important", "requires_response", "meeting_invitation",
            "newsletter", "promotional", "social", "transactional", "spam",
        ]

    user_prompt = f"""Classify this email:

FROM: {sanitize_for_prompt(sender, 200)}
SUBJECT: {sanitize_for_prompt(subject, 500)}
HAS .ICS ATTACHMENT: {has_ics}
USER PERSONA PROFILE: {user_persona}

BODY:
{sanitize_for_prompt(body, 3000)}"""

    try:
        result = await ai_provider.complete_text_kv(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            task_type=TaskType.CLASSIFICATION,
        )

        raw_category = str(result.get("category", "important")).lower()
        category = "important"
        for vc in valid_categories:
            if vc in raw_category:
                category = vc
                break

        try:
            import re
            raw_severity = str(result.get("severity", "3"))
            digits = re.findall(r'\d', raw_severity)
            if digits:
                severity = max(1, min(5, int(digits[0])))
            else:
                severity = 3
        except Exception:
            severity = 3
            
        # Handle string "true" / "false"
        is_meeting_str = str(result.get("is meeting invitation", "false")).lower()
        is_meeting = "true" in is_meeting_str

        # Override: .ics attachment always means meeting
        if has_ics:
            is_meeting = True
            category = "meeting_invitation"

        try:
            import re
            raw_conf = str(result.get("confidence", "0"))
            floats = re.findall(r'0\.\d+|1\.0|1|0', raw_conf)
            if floats:
                confidence = float(floats[0])
            else:
                confidence = 0.0
        except Exception:
            confidence = 0.0

        raw_action = str(result.get("suggested action", "REVIEW ONLY")).upper()
        valid_actions = ["ACTION REQUIRED", "REVIEW ONLY", "LOW RELEVANCE", "AUTO-ARCHIVE"]
        suggested_action = "REVIEW ONLY"
        for va in valid_actions:
            if va in raw_action:
                suggested_action = va
                break

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
