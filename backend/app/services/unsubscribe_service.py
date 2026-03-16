"""
Nexus Mail — Bulk Unsubscriber Service
Inspired by Inbox Zero's Newsletter Cleaner.
Scans newsletters/promotional emails and provides one-click unsubscribe,
auto-archive, and auto-archive+label actions.
"""

from datetime import datetime, timezone
from collections import defaultdict

from app.core.database import get_database
from app.services.gmail_service import GmailService

import structlog

logger = structlog.get_logger(__name__)


class UnsubscribeService:
    """
    Manages bulk unsubscribe operations.

    Features (inspired by Inbox Zero):
    - Scans inbox for newsletter/promotional senders
    - Groups by sender with email count and read rate
    - One-click unsubscribe via List-Unsubscribe header
    - Auto-archive: silently archives future emails from a sender
    - Auto-archive + label: archives and applies a Gmail label
    - Keep: hides the sender from the unsubscribe list
    """

    def __init__(self):
        self.gmail_service = GmailService()

    async def get_newsletter_senders(
        self, user_id: str, sort_by: str = "count", limit: int = 50
    ) -> list[dict]:
        """
        Get a list of newsletter/promotional senders with stats.
        Returns senders sorted by email count or read percentage.
        """
        db = get_database()

        # Aggregate emails by sender for newsletters and promotional categories
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "category": {"$in": ["newsletter", "promotional"]},
                }
            },
            {
                "$group": {
                    "_id": "$sender_email",
                    "sender_name": {"$first": "$sender_name"},
                    "sender_email": {"$first": "$sender_email"},
                    "total_count": {"$sum": 1},
                    "read_count": {
                        "$sum": {"$cond": [{"$eq": ["$is_read", True]}, 1, 0]}
                    },
                    "last_received": {"$max": "$received_at"},
                    "first_received": {"$min": "$received_at"},
                }
            },
            {
                "$addFields": {
                    "read_percentage": {
                        "$round": [
                            {
                                "$multiply": [
                                    {"$divide": ["$read_count", "$total_count"]},
                                    100,
                                ]
                            },
                            1,
                        ]
                    }
                }
            },
            {"$sort": {sort_by if sort_by in ["total_count", "read_percentage", "last_received"] else "total_count": -1}},
            {"$limit": limit},
        ]

        results = []
        async for doc in db.emails.aggregate(pipeline):
            # Check if already in the user's unsubscribe preferences
            pref = await db.unsubscribe_preferences.find_one(
                {"user_id": user_id, "sender_email": doc["sender_email"]}
            )

            results.append({
                "sender_name": doc["sender_name"],
                "sender_email": doc["sender_email"],
                "total_count": doc["total_count"],
                "read_count": doc["read_count"],
                "read_percentage": doc.get("read_percentage", 0),
                "last_received": doc["last_received"].isoformat() if doc.get("last_received") else None,
                "first_received": doc["first_received"].isoformat() if doc.get("first_received") else None,
                "status": pref["action"] if pref else "none",
            })

        return results

    async def unsubscribe(self, user_id: str, sender_email: str) -> dict:
        """
        Unsubscribe from a sender.
        Attempts to use the List-Unsubscribe header if available.
        Falls back to creating a Gmail filter to auto-delete.
        """
        db = get_database()

        # Find a recent email from this sender to get unsubscribe info
        email = await db.emails.find_one(
            {"user_id": user_id, "sender_email": sender_email},
            sort=[("received_at", -1)],
        )

        unsubscribe_method = "filter"  # default

        # Try to extract List-Unsubscribe header
        if email and email.get("list_unsubscribe"):
            unsubscribe_method = "header"
            # TODO: actually call the unsubscribe URL or send mailto

        # Store the preference
        await db.unsubscribe_preferences.update_one(
            {"user_id": user_id, "sender_email": sender_email},
            {
                "$set": {
                    "action": "unsubscribed",
                    "method": unsubscribe_method,
                    "sender_name": email.get("sender_name", "") if email else "",
                    "updated_at": datetime.now(timezone.utc),
                },
                "$setOnInsert": {"created_at": datetime.now(timezone.utc)},
            },
            upsert=True,
        )

        logger.info("Unsubscribed", user_id=user_id, sender=sender_email)
        return {"status": "unsubscribed", "method": unsubscribe_method}

    async def auto_archive(
        self, user_id: str, sender_email: str, label: str | None = None
    ) -> dict:
        """
        Set auto-archive for a sender.
        Future emails from this sender will be automatically archived.
        Optionally applies a Gmail label.
        """
        db = get_database()

        action = "auto_archive_label" if label else "auto_archive"

        await db.unsubscribe_preferences.update_one(
            {"user_id": user_id, "sender_email": sender_email},
            {
                "$set": {
                    "action": action,
                    "label": label,
                    "updated_at": datetime.now(timezone.utc),
                },
                "$setOnInsert": {"created_at": datetime.now(timezone.utc)},
            },
            upsert=True,
        )

        logger.info("Auto-archive set", user_id=user_id, sender=sender_email, label=label)
        return {"status": action, "label": label}

    async def keep_sender(self, user_id: str, sender_email: str) -> dict:
        """
        Mark a sender as 'keep' — hides them from the unsubscribe list.
        Does not affect email delivery.
        """
        db = get_database()

        await db.unsubscribe_preferences.update_one(
            {"user_id": user_id, "sender_email": sender_email},
            {
                "$set": {
                    "action": "keep",
                    "updated_at": datetime.now(timezone.utc),
                },
                "$setOnInsert": {"created_at": datetime.now(timezone.utc)},
            },
            upsert=True,
        )

        return {"status": "keep"}

    async def apply_auto_archive_rules(self, user_id: str, email_doc: dict) -> bool:
        """
        Check if an incoming email should be auto-archived
        based on the user's unsubscribe preferences.
        Called during email sync for each new email.
        Returns True if the email was auto-archived.
        """
        db = get_database()

        pref = await db.unsubscribe_preferences.find_one(
            {"user_id": user_id, "sender_email": email_doc.get("sender_email")}
        )

        if not pref:
            return False

        action = pref.get("action")

        if action in ("auto_archive", "auto_archive_label", "unsubscribed"):
            # Mark as auto-archived in our DB
            await db.emails.update_one(
                {"_id": email_doc["_id"], "user_id": user_id},
                {
                    "$set": {
                        "auto_archived": True,
                        "auto_archive_label": pref.get("label"),
                    }
                },
            )
            logger.info(
                "Auto-archived email",
                sender=email_doc.get("sender_email"),
                action=action,
            )
            return True

        return False
