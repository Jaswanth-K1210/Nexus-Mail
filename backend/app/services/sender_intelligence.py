"""
Nexus Mail — Sender Intelligence Service
Builds comprehensive profiles of senders combining Superhuman's velocity
metrics and Inbox Zero's cold outreach detection.
"""

from datetime import datetime, timezone
from bson import ObjectId

from app.core.database import get_database

import structlog

logger = structlog.get_logger(__name__)


class SenderIntelligenceService:
    """Service to build and retrieve comprehensive sender profiles."""

    async def get_or_build_profile(self, user_id: str, sender_email: str) -> dict:
        """
        Get the sender profile, building or updating it if necessary.
        """
        db = get_database()
        
        # Check if we have a recent profile (built in the last 24 hours)
        profile = await db.sender_profiles.find_one({
            "user_id": user_id,
            "sender_email": sender_email
        })

        now = datetime.now(timezone.utc)
        
        needs_update = True
        if profile and profile.get("updated_at"):
            updated_at = profile["updated_at"]
            if getattr(updated_at, "tzinfo", None) is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
                
            age_hours = (now - updated_at).total_seconds() / 3600
            if age_hours < 24:
                needs_update = False
                
        if not needs_update and profile:
            return profile

        # Build new profile
        new_profile = await self._build_profile(db, user_id, sender_email)
        
        # Store it
        await db.sender_profiles.update_one(
            {"user_id": user_id, "sender_email": sender_email},
            {"$set": new_profile},
            upsert=True
        )
        
        logger.info("Sender profile built/updated", user_id=user_id, sender_email=sender_email)
        
        return new_profile

    async def _build_profile(self, db, user_id: str, sender_email: str) -> dict:
        """Computes all stats for a sender."""
        
        # 1. Total emails received
        total_received = await db.emails.count_documents({
            "user_id": user_id,
            "sender_email": sender_email
        })

        # 2. Total read
        total_read = await db.emails.count_documents({
            "user_id": user_id,
            "sender_email": sender_email,
            "is_read": True
        })
        
        read_rate = (total_read / total_received) if total_received > 0 else 0.0

        # 3. Thread engagement (surrogate for replies)
        thread_ids = await db.emails.distinct("thread_id", {
            "user_id": user_id,
            "sender_email": sender_email,
        })
        threads_with_multiple_messages = 0
        if thread_ids:
            # Count how many of these threads have > 1 message
            pipeline = [
                {"$match": {"user_id": user_id, "thread_id": {"$in": thread_ids}}},
                {"$group": {"_id": "$thread_id", "count": {"$sum": 1}}},
                {"$match": {"count": {"$gt": 1}}}
            ]
            engaged_threads = await db.emails.aggregate(pipeline).to_list(length=None)
            threads_with_multiple_messages = len(engaged_threads)

        # 4. First and last contact
        first_email = await db.emails.find_one(
            {"user_id": user_id, "sender_email": sender_email},
            sort=[("received_at", 1)]
        )
        last_email = await db.emails.find_one(
            {"user_id": user_id, "sender_email": sender_email},
            sort=[("received_at", -1)]
        )
        
        first_contact = first_email.get("received_at") if first_email else None
        last_contact = last_email.get("received_at") if last_email else None
        
        sender_name = last_email.get("sender_name", "") if last_email else ""

        # 5. Category distribution
        pipeline = [
            {"$match": {"user_id": user_id, "sender_email": sender_email}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}}
        ]
        category_counts = await db.emails.aggregate(pipeline).to_list(length=None)
        categories = {item["_id"] or "unclassified": item["count"] for item in category_counts}

        # 6. Relationship strength (0-1)
        relationship_strength = 0.0
        if total_received > 0:
            # High weight on read rate
            relationship_strength += read_rate * 0.4
            
            # Engagement
            engagement_ratio = min(1.0, threads_with_multiple_messages / max(1, len(thread_ids)))
            relationship_strength += engagement_ratio * 0.4
            
            # Volume 
            volume_bonus = min(0.2, (total_received / 50) * 0.2)
            relationship_strength += volume_bonus

        # 7. Cold sender detection
        is_cold_sender = (
            total_received <= 3 and 
            read_rate == 0.0 and 
            threads_with_multiple_messages == 0 and
            categories.get("promotional", 0) + categories.get("spam", 0) > 0
        )

        return {
            "sender_email": sender_email,
            "sender_name": sender_name,
            "total_emails": total_received,
            "read_rate": read_rate,
            "engaged_threads": threads_with_multiple_messages,
            "first_contact": first_contact,
            "last_contact": last_contact,
            "categories": categories,
            "relationship_strength": round(relationship_strength, 2),
            "is_cold_sender": is_cold_sender,
            "is_vip": relationship_strength >= 0.8,
            "updated_at": datetime.now(timezone.utc)
        }
