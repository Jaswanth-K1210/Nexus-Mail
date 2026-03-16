"""
Nexus Mail — Cold Email Blocker
Inspired by Inbox Zero's Cold Email Blocker.
Uses AI to detect and auto-handle cold/spam outreach emails.
"""

from datetime import datetime, timezone
from bson import ObjectId

from app.core.database import get_database
from app.ai_worker.ai_provider import ai_provider, TaskType
from app.ai_worker.sanitizer import sanitize_email_body

import structlog

logger = structlog.get_logger(__name__)

COLD_EMAIL_DETECTION_PROMPT = """You are a cold email detection AI. Analyze the email and determine if it is a cold email (unsolicited outreach).

Signals of a COLD EMAIL:
- Sender has never emailed this person before (first contact)
- Sales pitch or business proposal from unknown company
- "I found you on LinkedIn/Twitter" type introductions
- Unsolicited partnership or collaboration requests
- Recruitment emails from unknown recruiters
- Generic templates with [Name] style personalization
- Links to book a demo/call with no prior relationship
- "We help companies like yours..." type language

Signals that it is NOT a cold email:
- From a known contact or existing conversation
- From a service the user has signed up for
- Transactional email (order, receipt, etc.)
- Newsletter the user subscribed to
- Internal company email
- Personal email from friends/family

Respond in JSON:
{
    "is_cold_email": true/false,
    "confidence": 0.0-1.0,
    "reason": "<brief explanation>",
    "cold_email_type": "<sales | recruitment | partnership | spam | other | none>"
}"""


class ColdEmailBlocker:
    """
    AI-powered cold email detection and blocking.

    Features (inspired by Inbox Zero):
    - AI classification of cold emails with customizable prompts
    - Three modes: list only, auto-label, auto-archive+label
    - View detected cold emails in a dedicated list
    - Test mode to preview detections before enabling auto-actions
    - Custom prompt support for user-specific filtering rules
    """

    async def detect_cold_email(
        self, subject: str, body: str, sender_email: str, sender_name: str, user_id: str
    ) -> dict:
        """
        Detect if an email is a cold email using AI.
        Checks sender history to determine if this is a first-time contact.
        """
        db = get_database()

        # Check if sender has emailed this user before
        prior_count = await db.emails.count_documents(
            {"user_id": user_id, "sender_email": sender_email}
        )
        is_first_contact = prior_count <= 1  # 1 because current email is already stored

        # Check against user's contacts/whitelist
        is_whitelisted = await db.sender_whitelist.find_one(
            {"user_id": user_id, "sender_email": sender_email}
        )

        if is_whitelisted:
            return {"is_cold_email": False, "confidence": 1.0, "reason": "Whitelisted sender"}

        user_prompt = f"""Analyze this email for cold email detection:

FROM: {sender_name} <{sender_email}>
SUBJECT: {subject}
FIRST TIME CONTACTING: {is_first_contact}
PRIOR EMAILS FROM THIS SENDER: {prior_count}

BODY:
{body[:2000]}"""

        try:
            result = await ai_provider.complete_json(
                system_prompt=COLD_EMAIL_DETECTION_PROMPT,
                user_prompt=user_prompt,
                temperature=0.1,
                task_type=TaskType.COLD_EMAIL,
            )

            return result

        except Exception as e:
            logger.error("Cold email detection failed", error=str(e))
            return {
                "is_cold_email": False,
                "confidence": 0.0,
                "reason": f"Detection failed: {str(e)}",
                "cold_email_type": "none",
            }

    async def get_blocker_settings(self, user_id: str) -> dict:
        """Get user's cold email blocker settings."""
        db = get_database()

        settings = await db.cold_email_settings.find_one({"user_id": user_id})

        if not settings:
            return {
                "enabled": False,
                "mode": "list",  # list | auto_label | auto_archive_label
                "custom_prompt": None,
                "label_name": "Cold Email",
            }

        return {
            "enabled": settings.get("enabled", False),
            "mode": settings.get("mode", "list"),
            "custom_prompt": settings.get("custom_prompt"),
            "label_name": settings.get("label_name", "Cold Email"),
        }

    async def update_settings(
        self,
        user_id: str,
        enabled: bool | None = None,
        mode: str | None = None,
        custom_prompt: str | None = None,
        label_name: str | None = None,
    ) -> dict:
        """Update cold email blocker settings."""
        db = get_database()

        update = {"updated_at": datetime.now(timezone.utc)}
        if enabled is not None:
            update["enabled"] = enabled
        if mode is not None:
            update["mode"] = mode
        if custom_prompt is not None:
            update["custom_prompt"] = custom_prompt
        if label_name is not None:
            update["label_name"] = label_name

        await db.cold_email_settings.update_one(
            {"user_id": user_id},
            {"$set": update, "$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
            upsert=True,
        )

        return await self.get_blocker_settings(user_id)

    async def get_cold_emails(self, user_id: str, limit: int = 50) -> list[dict]:
        """Get list of detected cold emails."""
        db = get_database()

        cursor = db.emails.find(
            {"user_id": user_id, "is_cold_email": True},
            {"body_text": 0, "body_html": 0},
        ).sort("received_at", -1).limit(limit)

        results = []
        async for email in cursor:
            results.append({
                "id": str(email["_id"]),
                "subject": email.get("subject", ""),
                "sender_name": email.get("sender_name", ""),
                "sender_email": email.get("sender_email", ""),
                "received_at": email["received_at"].isoformat() if email.get("received_at") else None,
                "cold_email_type": email.get("cold_email_type", "other"),
                "cold_email_reason": email.get("cold_email_reason", ""),
            })

        return results

    async def whitelist_sender(self, user_id: str, sender_email: str) -> dict:
        """Add a sender to the whitelist — their emails will never be flagged as cold."""
        db = get_database()

        await db.sender_whitelist.update_one(
            {"user_id": user_id, "sender_email": sender_email},
            {
                "$set": {"updated_at": datetime.now(timezone.utc)},
                "$setOnInsert": {"created_at": datetime.now(timezone.utc)},
            },
            upsert=True,
        )

        # Un-flag any existing cold emails from this sender
        await db.emails.update_many(
            {"user_id": user_id, "sender_email": sender_email, "is_cold_email": True},
            {"$set": {"is_cold_email": False}},
        )

        return {"status": "whitelisted", "sender": sender_email}

    async def process_incoming_email(self, user_id: str, email_doc: dict) -> dict | None:
        """
        Process an incoming email through the cold email blocker.
        Called during the AI pipeline for each new email.
        Returns detection result or None if blocker is disabled.
        """
        db = get_database()

        settings = await self.get_blocker_settings(user_id)
        if not settings.get("enabled"):
            return None

        # BUG FIX: Use sanitized body so HTML-only emails are also analyzed.
        # Previously passed raw body_text which can be empty for HTML emails.
        body = sanitize_email_body(
            body_text=email_doc.get("body_text", ""),
            body_html=email_doc.get("body_html", ""),
        )
        result = await self.detect_cold_email(
            subject=email_doc.get("subject", ""),
            body=body,
            sender_email=email_doc.get("sender_email", ""),
            sender_name=email_doc.get("sender_name", ""),
            user_id=user_id,
        )

        if result.get("is_cold_email") and result.get("confidence", 0) >= 0.7:
            update_fields = {
                "is_cold_email": True,
                "cold_email_type": result.get("cold_email_type", "other"),
                "cold_email_reason": result.get("reason", ""),
            }

            mode = settings.get("mode", "list")
            if mode in ("auto_label", "auto_archive_label"):
                update_fields["cold_email_labeled"] = True
            if mode == "auto_archive_label":
                update_fields["auto_archived"] = True

            await db.emails.update_one(
                {"_id": email_doc["_id"], "user_id": user_id},
                {"$set": update_fields},
            )

            logger.info(
                "Cold email detected",
                sender=email_doc.get("sender_email"),
                type=result.get("cold_email_type"),
                mode=mode,
            )

        return result
