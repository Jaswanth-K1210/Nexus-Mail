"""
Nexus Mail — Auto-Reply Service
Automatically generates and sends AI-crafted replies for low-priority emails
that need a response but don't require the user's attention.

Criteria for auto-reply:
  - Email is classified as low priority (score < 35)
  - Suggested action is NOT "ACTION REQUIRED"
  - Category is NOT: important, meeting_invitation, spam
  - Email appears to need a simple acknowledgement/reply
  - User has enabled auto-reply in their settings

The reply is generated using the user's tone profile, sent via Gmail,
and logged in `auto_replies` collection for transparency.
"""

from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId

from app.core.database import get_database
from app.services.gmail_service import GmailService
from app.services.sse_service import push_to_user
from app.ai_worker.ai_provider import ai_provider, TaskType
from app.ai_worker.utils import sanitize_for_prompt

import structlog

logger = structlog.get_logger(__name__)

# Categories that should NEVER get auto-replies
EXCLUDED_CATEGORIES = {"important", "meeting_invitation", "spam"}

# Suggested actions that should NEVER get auto-replies
EXCLUDED_ACTIONS = {"ACTION REQUIRED"}

# Maximum priority score for auto-reply eligibility
MAX_PRIORITY_SCORE = 35

AUTO_REPLY_PROMPT = """You are an AI email assistant for Nexus Mail.
Generate a brief, natural acknowledgement reply to this email.

The user's tone profile:
{tone_profile}

Rules:
- This is a LOW-PRIORITY email that just needs a quick acknowledgement.
- Keep the reply SHORT (1-2 sentences max).
- Be polite but brief — "Thanks for the update!", "Got it, thanks!", "Noted, appreciate it." style.
- Match the user's communication style from the tone profile.
- Do NOT make any commitments, promises, or ask follow-up questions.
- Do NOT offer to do anything or schedule anything.
- Do NOT repeat the email content back.
- Sound natural and human, not robotic.

Respond in JSON format:
{{
    "reply_text": "<the short reply>",
    "confidence": <0.0-1.0 how appropriate this auto-reply is>
}}"""


class AutoReplyService:
    """Handles automatic reply generation and sending for low-priority emails."""

    def __init__(self):
        self.gmail_service = GmailService()

    async def get_settings(self, user_id: str) -> dict:
        """Get the user's auto-reply settings."""
        db = get_database()
        try:
            user_oid = ObjectId(user_id)
        except (InvalidId, TypeError):
            user_oid = user_id

        user = await db.users.find_one(
            {"_id": user_oid},
            {"auto_reply_enabled": 1, "auto_reply_categories": 1},
        )

        return {
            "enabled": user.get("auto_reply_enabled", False) if user else False,
            "categories": user.get("auto_reply_categories", [
                "newsletter", "transactional", "social", "promotional",
            ]) if user else [],
        }

    async def update_settings(self, user_id: str, enabled: bool, categories: list[str] | None = None) -> dict:
        """Update auto-reply settings."""
        db = get_database()
        try:
            user_oid = ObjectId(user_id)
        except (InvalidId, TypeError):
            user_oid = user_id

        update = {"auto_reply_enabled": enabled}
        if categories is not None:
            # Filter out excluded categories
            safe_categories = [c for c in categories if c not in EXCLUDED_CATEGORIES]
            update["auto_reply_categories"] = safe_categories

        await db.users.update_one({"_id": user_oid}, {"$set": update})

        logger.info("Auto-reply settings updated", user_id=user_id, enabled=enabled)
        return {"enabled": enabled, "categories": update.get("auto_reply_categories", categories)}

    async def should_auto_reply(self, user_id: str, email_doc: dict) -> bool:
        """Determine if an email qualifies for auto-reply."""
        settings = await self.get_settings(user_id)

        if not settings["enabled"]:
            return False

        category = email_doc.get("category", "")
        suggested_action = email_doc.get("suggested_action", "")
        priority_score = email_doc.get("priority_score", 50)

        # Hard exclusions
        if category in EXCLUDED_CATEGORIES:
            return False
        if suggested_action in EXCLUDED_ACTIONS:
            return False
        if priority_score > MAX_PRIORITY_SCORE:
            return False

        # Category must be in user's allowed auto-reply categories
        allowed_categories = settings.get("categories", [])
        if allowed_categories and category not in allowed_categories:
            return False

        # Don't auto-reply to noreply addresses
        sender_email = email_doc.get("sender_email", "") or email_doc.get("sender", "")
        if any(x in sender_email.lower() for x in ["noreply", "no-reply", "donotreply", "mailer-daemon"]):
            return False

        # Don't auto-reply if we already auto-replied to this email
        db = get_database()
        existing = await db.auto_replies.find_one({
            "email_id": str(email_doc.get("_id", "")),
            "user_id": user_id,
        })
        if existing:
            return False

        return True

    async def generate_and_send(self, user_id: str, email_doc: dict) -> dict | None:
        """Generate an auto-reply and send it. Returns the auto-reply record or None."""
        db = get_database()
        email_id = str(email_doc["_id"])

        # Get user's tone profile
        try:
            user_oid = ObjectId(user_id)
        except (InvalidId, TypeError):
            user_oid = user_id

        user = await db.users.find_one(
            {"_id": user_oid},
            {"tone_profile": 1},
        )
        tone_profile = user.get("tone_profile", {}) if user else {}
        tone_str = str(tone_profile) if tone_profile else "Professional, friendly, concise."

        sender_name = email_doc.get("sender_name", "")
        sender_email = email_doc.get("sender_email", "") or email_doc.get("sender", "")
        subject = email_doc.get("subject", "")
        body = email_doc.get("body_text", "") or email_doc.get("ai_summary", "")

        # Generate the reply
        system_prompt = AUTO_REPLY_PROMPT.format(tone_profile=tone_str)
        user_prompt = f"""Generate a quick acknowledgement reply for this email:

FROM: {sanitize_for_prompt(sender_name, 200)} <{sanitize_for_prompt(sender_email, 200)}>
SUBJECT: {sanitize_for_prompt(subject, 500)}
CATEGORY: {email_doc.get('category', 'unknown')}

EMAIL BODY:
{sanitize_for_prompt(body, 1000)}"""

        try:
            result = await ai_provider.complete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                task_type=TaskType.REPLY_DRAFT,
            )

            reply_text = result.get("reply_text", "").strip()
            confidence = result.get("confidence", 0.0)

            if not reply_text or confidence < 0.6:
                logger.info(
                    "Auto-reply skipped (low confidence or empty)",
                    email_id=email_id,
                    confidence=confidence,
                )
                return None

            # Send via Gmail
            thread_id = email_doc.get("thread_id")
            await self.gmail_service.send_reply(
                user_id=user_id,
                to_email=sender_email,
                subject=f"Re: {subject}" if not subject.startswith("Re:") else subject,
                body=reply_text,
                thread_id=thread_id,
            )

            # Store the auto-reply record
            auto_reply_doc = {
                "user_id": user_id,
                "email_id": email_id,
                "sender_name": sender_name,
                "sender_email": sender_email,
                "subject": subject,
                "category": email_doc.get("category", ""),
                "priority_score": email_doc.get("priority_score", 0),
                "reply_text": reply_text,
                "confidence": confidence,
                "status": "sent",
                "sent_at": datetime.now(timezone.utc),
            }
            insert_result = await db.auto_replies.insert_one(auto_reply_doc)

            logger.info(
                "Auto-reply sent",
                email_id=email_id,
                to=sender_email,
                confidence=confidence,
                category=email_doc.get("category"),
            )

            # Notify user via SSE
            await push_to_user(user_id, "auto_reply_sent", {
                "auto_reply_id": str(insert_result.inserted_id),
                "email_id": email_id,
                "to": sender_email,
                "subject": subject,
                "reply_preview": reply_text[:100],
            })

            return {
                "auto_reply_id": str(insert_result.inserted_id),
                "reply_text": reply_text,
                "confidence": confidence,
                "status": "sent",
            }

        except Exception as e:
            logger.error("Auto-reply failed", email_id=email_id, error=str(e))
            return None

    async def get_auto_reply_log(self, user_id: str, limit: int = 30) -> list[dict]:
        """Get the user's auto-reply history."""
        db = get_database()

        replies = []
        cursor = db.auto_replies.find(
            {"user_id": user_id}
        ).sort("sent_at", -1).limit(limit)

        async for doc in cursor:
            replies.append({
                "id": str(doc["_id"]),
                "email_id": doc.get("email_id", ""),
                "sender_name": doc.get("sender_name", ""),
                "sender_email": doc.get("sender_email", ""),
                "subject": doc.get("subject", ""),
                "category": doc.get("category", ""),
                "priority_score": doc.get("priority_score", 0),
                "reply_text": doc.get("reply_text", ""),
                "confidence": doc.get("confidence", 0),
                "status": doc.get("status", "sent"),
                "sent_at": doc["sent_at"].isoformat() if doc.get("sent_at") else None,
            })

        return replies

    async def get_stats(self, user_id: str) -> dict:
        """Get auto-reply statistics."""
        db = get_database()
        total = await db.auto_replies.count_documents({"user_id": user_id})
        return {"total_auto_replies": total}
