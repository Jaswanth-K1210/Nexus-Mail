"""
Nexus Mail — Email Analytics Service
Inspired by Inbox Zero's Analytics feature.
Tracks email activity, sender patterns, category distribution, and trends.
"""

from datetime import datetime, timedelta, timezone
from app.core.database import get_database

import structlog

logger = structlog.get_logger(__name__)


class AnalyticsService:
    """
    Email analytics engine providing insights into inbox activity.

    Features (inspired by Inbox Zero):
    - Daily send/receive counts
    - Top senders who email you most
    - Top domains (organizations) emailing you
    - Category distribution breakdown
    - Read vs unread rate tracking
    - Email volume trends over time
    - Response time tracking
    """

    async def get_dashboard_stats(self, user_id: str) -> dict:
        """
        Get overview stats for the analytics dashboard.
        Quick counts displayed as stat cards.
        """
        db = get_database()
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())

        total = await db.emails.count_documents({"user_id": user_id})
        today = await db.emails.count_documents(
            {"user_id": user_id, "received_at": {"$gte": today_start}}
        )
        this_week = await db.emails.count_documents(
            {"user_id": user_id, "received_at": {"$gte": week_start}}
        )
        unread = await db.emails.count_documents(
            {"user_id": user_id, "is_read": False}
        )
        processed = await db.emails.count_documents(
            {"user_id": user_id, "is_processed": True}
        )

        # Pending actions
        pending_meetings = await db.meeting_alerts.count_documents(
            {"user_id": user_id, "status": "pending"}
        )
        requires_response = await db.emails.count_documents(
            {"user_id": user_id, "category": "requires_response", "is_read": False}
        )

        return {
            "total_emails": total,
            "today_received": today,
            "this_week_received": this_week,
            "unread_count": unread,
            "processed_count": processed,
            "pending_meetings": pending_meetings,
            "requires_response": requires_response,
            "read_rate": round((total - unread) / total * 100, 1) if total > 0 else 0,
        }

    async def get_daily_volume(self, user_id: str, days: int = 30) -> list[dict]:
        """
        Get daily email receive/send counts for the past N days.
        Used for the email volume chart.
        """
        db = get_database()
        start = datetime.now(timezone.utc) - timedelta(days=days)

        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "received_at": {"$gte": start},
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$received_at",
                        }
                    },
                    "received": {"$sum": 1},
                    "read": {
                        "$sum": {"$cond": [{"$eq": ["$is_read", True]}, 1, 0]}
                    },
                }
            },
            {"$sort": {"_id": 1}},
        ]

        results = []
        async for doc in db.emails.aggregate(pipeline):
            results.append({
                "date": doc["_id"],
                "received": doc["received"],
                "read": doc["read"],
            })

        return results

    async def get_top_senders(self, user_id: str, limit: int = 10) -> list[dict]:
        """
        Get the top N senders by email count.
        Shows who is filling up your inbox.
        """
        db = get_database()

        pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": "$sender_email",
                    "name": {"$first": "$sender_name"},
                    "email": {"$first": "$sender_email"},
                    "count": {"$sum": 1},
                    "unread": {
                        "$sum": {"$cond": [{"$eq": ["$is_read", False]}, 1, 0]}
                    },
                    "last_email": {"$max": "$received_at"},
                }
            },
            {"$sort": {"count": -1}},
            {"$limit": limit},
        ]

        results = []
        async for doc in db.emails.aggregate(pipeline):
            results.append({
                "name": doc["name"],
                "email": doc["email"],
                "count": doc["count"],
                "unread": doc["unread"],
                "last_email": doc["last_email"].isoformat() if doc.get("last_email") else None,
            })

        return results

    async def get_top_domains(self, user_id: str, limit: int = 10) -> list[dict]:
        """
        Get top sender domains by email count.
        Shows which organizations email you most.
        """
        db = get_database()

        pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$addFields": {
                    "domain": {
                        "$arrayElemAt": [
                            {"$split": ["$sender_email", "@"]}, 1
                        ]
                    }
                }
            },
            {
                "$group": {
                    "_id": "$domain",
                    "domain": {"$first": "$domain"},
                    "count": {"$sum": 1},
                    "senders": {"$addToSet": "$sender_email"},
                }
            },
            {
                "$addFields": {
                    "unique_senders": {"$size": "$senders"},
                }
            },
            {"$sort": {"count": -1}},
            {"$limit": limit},
            {"$project": {"senders": 0}},
        ]

        results = []
        async for doc in db.emails.aggregate(pipeline):
            results.append({
                "domain": doc["domain"],
                "count": doc["count"],
                "unique_senders": doc["unique_senders"],
            })

        return results

    async def get_category_breakdown(self, user_id: str) -> list[dict]:
        """
        Get email distribution by AI-assigned category.
        Used for the category pie/bar chart.
        """
        db = get_database()

        pipeline = [
            {"$match": {"user_id": user_id, "is_processed": True}},
            {
                "$group": {
                    "_id": "$category",
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"count": -1}},
        ]

        total = await db.emails.count_documents(
            {"user_id": user_id, "is_processed": True}
        )

        results = []
        async for doc in db.emails.aggregate(pipeline):
            category = doc["_id"] or "uncategorized"
            results.append({
                "category": category,
                "count": doc["count"],
                "percentage": round(doc["count"] / total * 100, 1) if total > 0 else 0,
            })

        return results

    async def get_hourly_pattern(self, user_id: str) -> list[dict]:
        """
        Get email receive pattern by hour of day.
        Shows when you receive the most emails.
        """
        db = get_database()

        pipeline = [
            {"$match": {"user_id": user_id, "received_at": {"$ne": None}}},
            {
                "$group": {
                    "_id": {"$hour": "$received_at"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ]

        # Initialize all 24 hours
        hourly = {h: 0 for h in range(24)}

        async for doc in db.emails.aggregate(pipeline):
            hourly[doc["_id"]] = doc["count"]

        return [
            {"hour": h, "count": c, "label": f"{h:02d}:00"}
            for h, c in hourly.items()
        ]
