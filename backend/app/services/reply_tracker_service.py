"""
Nexus Mail — Reply Tracker Service
Inspired by Inbox Zero's "Reply Zero" feature.
Tracks emails needing replies and emails awaiting responses from others.
Supports one-click AI-generated follow-up nudges.
"""

from datetime import datetime, timedelta, timezone
from bson import ObjectId

from app.core.database import get_database
from app.ai_worker.ai_provider import ai_provider

import structlog

logger = structlog.get_logger(__name__)


class ReplyTrackerService:
    """
    Reply tracking system — ensures no email falls through the cracks.

    Features (inspired by Inbox Zero's Reply Zero):
    - "To Reply" list: Emails you haven't responded to yet
    - "Awaiting Reply" list: Emails you sent waiting for their response
    - One-click Nudge: AI drafts a polite follow-up message
    - Filter by age (overdue conversations)
    - Mark as Done: removes from tracking lists
    """

    async def get_needs_reply(
        self, user_id: str, filter_age: str | None = None, limit: int = 50
    ) -> list[dict]:
        """
        Get emails that need your reply.
        These are emails classified as 'requires_response' that you haven't replied to.
        """
        db = get_database()

        query = {
            "user_id": user_id,
            "category": {"$in": ["requires_response", "important"]},
            "replied": {"$ne": True},
            "reply_dismissed": {"$ne": True},
        }

        # Filter by age
        if filter_age:
            now = datetime.now(timezone.utc)
            if filter_age == "today":
                query["received_at"] = {"$gte": now.replace(hour=0, minute=0, second=0)}
            elif filter_age == "this_week":
                query["received_at"] = {"$gte": now - timedelta(days=7)}
            elif filter_age == "overdue":
                # Older than 48 hours and still unreplied
                query["received_at"] = {"$lte": now - timedelta(hours=48)}

        cursor = db.emails.find(
            query,
            {
                "body_text": 0,
                "body_html": 0,
            },
        ).sort("received_at", -1).limit(limit)

        results = []
        async for email in cursor:
            age = self._calculate_age(email.get("received_at"))
            results.append({
                "id": str(email["_id"]),
                "subject": email.get("subject", ""),
                "sender_name": email.get("sender_name", ""),
                "sender_email": email.get("sender_email", ""),
                "snippet": email.get("snippet", ""),
                "received_at": email["received_at"].isoformat() if email.get("received_at") else None,
                "age": age,
                "is_overdue": age.get("hours", 0) > 48,
                "severity": email.get("severity", 3),
                "summary": email.get("summary"),
                "reply_draft": email.get("reply_draft"),
            })

        return results

    async def get_awaiting_reply(
        self, user_id: str, filter_age: str | None = None, limit: int = 50
    ) -> list[dict]:
        """
        Get emails you've sent that are awaiting a response from someone else.
        Tracks threads where you were the last to reply.
        """
        db = get_database()

        query = {
            "user_id": user_id,
            "category": "awaiting_reply",
            "response_received": {"$ne": True},
            "tracking_dismissed": {"$ne": True},
        }

        if filter_age == "overdue":
            now = datetime.now(timezone.utc)
            query["replied_at"] = {"$lte": now - timedelta(days=3)}

        cursor = db.emails.find(
            query,
            {"body_text": 0, "body_html": 0},
        ).sort("replied_at", -1).limit(limit)

        results = []
        async for email in cursor:
            age = self._calculate_age(email.get("replied_at") or email.get("received_at"))
            results.append({
                "id": str(email["_id"]),
                "subject": email.get("subject", ""),
                "sender_name": email.get("sender_name", ""),
                "sender_email": email.get("sender_email", ""),
                "snippet": email.get("snippet", ""),
                "replied_at": email["replied_at"].isoformat() if email.get("replied_at") else None,
                "age": age,
                "is_overdue": age.get("days", 0) >= 3,
                "waiting_days": age.get("days", 0),
            })

        return results

    async def generate_nudge(self, user_id: str, email_id: str) -> dict:
        """
        One-click nudge — AI generates a polite follow-up message.
        Perfect for when you're waiting for a reply and need to remind them.
        """
        db = get_database()

        email = await db.emails.find_one({"_id": ObjectId(email_id), "user_id": user_id})
        if not email:
            raise ValueError("Email not found")

        # Get user's tone profile
        user = await db.users.find_one({"_id": user_id}, {"tone_profile": 1, "name": 1})
        tone_str = str(user.get("tone_profile")) if user and user.get("tone_profile") else "Professional and friendly"
        user_name = user.get("name", "") if user else ""

        age = self._calculate_age(email.get("replied_at") or email.get("received_at"))

        nudge_text = await ai_provider.complete(
            system_prompt=f"""You are an email assistant. Write a brief, polite follow-up/nudge email.
Style: {tone_str}
Write ONLY the email body text, no subject line, no JSON.
Be natural and not robotic. Keep it 2-3 sentences max.
Do NOT be passive-aggressive.""",
            user_prompt=f"""Write a gentle follow-up nudge for this email thread:

ORIGINAL SUBJECT: {email.get('subject', '')}
TO: {email.get('sender_name', '')} <{email.get('sender_email', '')}>
DAYS WAITING: {age.get('days', 0)}

The user ({user_name}) is following up on a previous conversation. Draft a short, polite nudge.""",
            temperature=0.5,
        )

        return {
            "nudge_text": nudge_text.strip(),
            "to_email": email.get("sender_email"),
            "subject": f"Re: {email.get('subject', '')}",
            "thread_id": email.get("thread_id"),
        }

    async def mark_as_replied(self, user_id: str, email_id: str) -> dict:
        """Mark an email as replied to — removes from 'To Reply' list."""
        db = get_database()

        result = await db.emails.update_one(
            {"_id": ObjectId(email_id), "user_id": user_id},
            {
                "$set": {
                    "replied": True,
                    "replied_at": datetime.now(timezone.utc),
                }
            },
        )

        if result.modified_count == 0:
            raise ValueError("Email not found")

        return {"status": "marked_as_replied"}

    async def mark_as_done(self, user_id: str, email_id: str) -> dict:
        """
        Mark an email tracking as done — removes from both lists.
        Equivalent to Inbox Zero's 'Mark as Done'.
        """
        db = get_database()

        await db.emails.update_one(
            {"_id": ObjectId(email_id), "user_id": user_id},
            {
                "$set": {
                    "reply_dismissed": True,
                    "tracking_dismissed": True,
                }
            },
        )

        return {"status": "done"}

    async def get_reply_stats(self, user_id: str) -> dict:
        """Get summary stats for the Reply Zero dashboard."""
        db = get_database()

        to_reply = await db.emails.count_documents({
            "user_id": user_id,
            "category": {"$in": ["requires_response", "important"]},
            "replied": {"$ne": True},
            "reply_dismissed": {"$ne": True},
        })

        awaiting = await db.emails.count_documents({
            "user_id": user_id,
            "category": "awaiting_reply",
            "response_received": {"$ne": True},
            "tracking_dismissed": {"$ne": True},
        })

        # Overdue counts
        now = datetime.now(timezone.utc)
        overdue_to_reply = await db.emails.count_documents({
            "user_id": user_id,
            "category": {"$in": ["requires_response", "important"]},
            "replied": {"$ne": True},
            "reply_dismissed": {"$ne": True},
            "received_at": {"$lte": now - timedelta(hours=48)},
        })

        overdue_awaiting = await db.emails.count_documents({
            "user_id": user_id,
            "category": "awaiting_reply",
            "response_received": {"$ne": True},
            "tracking_dismissed": {"$ne": True},
            "replied_at": {"$lte": now - timedelta(days=3)},
        })

        return {
            "to_reply_count": to_reply,
            "awaiting_reply_count": awaiting,
            "overdue_to_reply": overdue_to_reply,
            "overdue_awaiting": overdue_awaiting,
        }

    def _calculate_age(self, timestamp: datetime | None) -> dict:
        """Calculate the age of an email in human-readable form."""
        if not timestamp:
            return {"hours": 0, "days": 0, "label": "just now"}

        now = datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        delta = now - timestamp
        hours = int(delta.total_seconds() / 3600)
        days = delta.days

        if hours < 1:
            label = "just now"
        elif hours < 24:
            label = f"{hours}h ago"
        elif days == 1:
            label = "yesterday"
        elif days < 7:
            label = f"{days}d ago"
        else:
            label = f"{days // 7}w ago"

        return {"hours": hours, "days": days, "label": label}
