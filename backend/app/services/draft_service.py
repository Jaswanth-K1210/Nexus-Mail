"""
Nexus Mail — Draft-First Service
DLP safety layer: AI generates drafts but NEVER sends without user approval.

Architecture pattern from Inbox Zero:
- Default: All AI-generated replies stored as pending drafts
- User previews → approves/edits/rejects → then it's sent
- Power mode: Auto-send when AI confidence >= user threshold
"""

from datetime import datetime, timezone
from bson import ObjectId

from app.core.database import get_database
from app.services.gmail_service import GmailService
from app.services.sse_service import push_to_user

import structlog

logger = structlog.get_logger(__name__)


class DraftService:
    """
    Manages the draft-first workflow for all AI-generated outbound emails.
    Nothing leaves the system without explicit user approval (or high-confidence auto-send).
    """

    def __init__(self):
        self.gmail_service = GmailService()

    async def create_draft(
        self,
        user_id: str,
        email_id: str,
        draft_body: str,
        draft_type: str = "reply",
        ai_confidence: float = 0.0,
        recipient_email: str = "",
        recipient_name: str = "",
        subject: str = "",
        thread_id: str | None = None,
        source: str = "pipeline",
    ) -> dict:
        """
        Store an AI-generated draft for user review.

        Args:
            draft_type: "reply" | "accept" | "decline" | "suggest" | "nudge" | "forward"
            ai_confidence: 0.0 - 1.0, how confident the AI is in the draft quality
            source: "pipeline" | "meeting" | "nudge" | "rule"
        """
        db = get_database()

        draft_doc = {
            "user_id": user_id,
            "email_id": email_id,
            "draft_body": draft_body,
            "draft_type": draft_type,
            "ai_confidence": ai_confidence,
            "recipient_email": recipient_email,
            "recipient_name": recipient_name,
            "subject": subject,
            "thread_id": thread_id,
            "source": source,
            "status": "pending",  # pending | approved | rejected | auto_sent
            "created_at": datetime.now(timezone.utc),
            "reviewed_at": None,
        }

        # Check if auto-send is enabled and confidence exceeds threshold
        user = await db.users.find_one(
            {"_id": user_id},
            {"auto_send_enabled": 1, "auto_send_threshold": 1},
        )

        auto_send_enabled = user.get("auto_send_enabled", False) if user else False
        auto_send_threshold = user.get("auto_send_threshold", 0.95) if user else 0.95

        if auto_send_enabled and ai_confidence >= auto_send_threshold:
            # High confidence + auto-send enabled → send immediately
            draft_doc["status"] = "auto_sent"
            draft_doc["reviewed_at"] = datetime.now(timezone.utc)

            result = await db.email_drafts.insert_one(draft_doc)

            # Actually send the email
            await self.gmail_service.send_reply(
                user_id=user_id,
                to_email=recipient_email,
                subject=subject,
                body=draft_body,
                thread_id=thread_id,
            )

            logger.info(
                "Draft auto-sent (high confidence)",
                draft_id=str(result.inserted_id),
                confidence=ai_confidence,
                threshold=auto_send_threshold,
            )

            # Notify user via SSE
            await push_to_user(user_id, "draft_auto_sent", {
                "draft_id": str(result.inserted_id),
                "recipient": recipient_email,
                "subject": subject,
                "confidence": ai_confidence,
            })

            return {
                "draft_id": str(result.inserted_id),
                "status": "auto_sent",
                "confidence": ai_confidence,
            }

        # Default: store as pending draft for user review
        result = await db.email_drafts.insert_one(draft_doc)

        # Notify user via SSE that a new draft is ready
        await push_to_user(user_id, "new_draft", {
            "draft_id": str(result.inserted_id),
            "draft_type": draft_type,
            "recipient": recipient_email,
            "subject": subject,
            "preview": draft_body[:100],
        })

        logger.info(
            "Draft created for review",
            draft_id=str(result.inserted_id),
            draft_type=draft_type,
            confidence=ai_confidence,
        )

        return {
            "draft_id": str(result.inserted_id),
            "status": "pending",
            "confidence": ai_confidence,
        }

    async def get_pending_drafts(self, user_id: str) -> list[dict]:
        """Get all pending drafts for a user."""
        db = get_database()

        drafts = []
        cursor = db.email_drafts.find(
            {"user_id": user_id, "status": "pending"}
        ).sort("created_at", -1)

        async for draft in cursor:
            drafts.append({
                "_id": str(draft["_id"]),
                "email_id": draft.get("email_id"),
                "draft_body": draft.get("draft_body", ""),
                "draft_type": draft.get("draft_type", "reply"),
                "ai_confidence": draft.get("ai_confidence", 0),
                "recipient_email": draft.get("recipient_email", ""),
                "recipient_name": draft.get("recipient_name", ""),
                "subject": draft.get("subject", ""),
                "thread_id": draft.get("thread_id"),
                "source": draft.get("source", "pipeline"),
                "status": draft.get("status", "pending"),
                "created_at": draft["created_at"].isoformat(),
            })

        return drafts

    async def approve_draft(self, draft_id: str, user_id: str) -> dict:
        """Approve a draft and send it via Gmail."""
        db = get_database()

        draft = await db.email_drafts.find_one(
            {"_id": ObjectId(draft_id), "user_id": user_id}
        )
        if not draft:
            raise ValueError("Draft not found")
        if draft["status"] != "pending":
            raise ValueError(f"Draft is not pending (status: {draft['status']})")

        # Send the email
        await self.gmail_service.send_reply(
            user_id=user_id,
            to_email=draft["recipient_email"],
            subject=draft["subject"],
            body=draft["draft_body"],
            thread_id=draft.get("thread_id"),
        )

        # Update draft status
        await db.email_drafts.update_one(
            {"_id": ObjectId(draft_id)},
            {"$set": {
                "status": "approved",
                "reviewed_at": datetime.now(timezone.utc),
            }},
        )

        logger.info("Draft approved and sent", draft_id=draft_id)
        return {"status": "approved", "sent": True}

    async def reject_draft(self, draft_id: str, user_id: str) -> dict:
        """Reject a draft — discard without sending."""
        db = get_database()

        result = await db.email_drafts.update_one(
            {"_id": ObjectId(draft_id), "user_id": user_id, "status": "pending"},
            {"$set": {
                "status": "rejected",
                "reviewed_at": datetime.now(timezone.utc),
            }},
        )

        if result.modified_count == 0:
            raise ValueError("Draft not found or already resolved")

        logger.info("Draft rejected", draft_id=draft_id)
        return {"status": "rejected"}

    async def edit_draft(
        self, draft_id: str, user_id: str, new_body: str
    ) -> dict:
        """Edit a draft's body text before sending."""
        db = get_database()

        result = await db.email_drafts.update_one(
            {"_id": ObjectId(draft_id), "user_id": user_id, "status": "pending"},
            {"$set": {
                "draft_body": new_body,
                "ai_confidence": 0.0,  # Reset confidence since human edited
            }},
        )

        if result.modified_count == 0:
            raise ValueError("Draft not found or already resolved")

        return {"status": "updated"}

    async def get_auto_send_settings(self, user_id: str) -> dict:
        """Get the user's auto-send configuration."""
        db = get_database()
        user = await db.users.find_one(
            {"_id": user_id},
            {"auto_send_enabled": 1, "auto_send_threshold": 1},
        )

        return {
            "auto_send_enabled": user.get("auto_send_enabled", False) if user else False,
            "auto_send_threshold": user.get("auto_send_threshold", 0.95) if user else 0.95,
        }

    async def update_auto_send_settings(
        self, user_id: str, enabled: bool, threshold: float = 0.95
    ) -> dict:
        """Update auto-send configuration."""
        db = get_database()

        # Enforce minimum threshold for safety
        if threshold < 0.8:
            threshold = 0.8

        await db.users.update_one(
            {"_id": user_id},
            {"$set": {
                "auto_send_enabled": enabled,
                "auto_send_threshold": threshold,
            }},
        )

        logger.info(
            "Auto-send settings updated",
            user_id=user_id,
            enabled=enabled,
            threshold=threshold,
        )

        return {"auto_send_enabled": enabled, "auto_send_threshold": threshold}
