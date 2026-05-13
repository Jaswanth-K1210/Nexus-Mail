"""
Nexus Mail — Tool Implementations

Concrete tools wrapping existing services for agent use.
Each tool provides a structured interface with tracing, retries, and metrics.
"""

import time
from typing import Any, Optional

from app.tools.base import BaseTool, ToolResult

import structlog

logger = structlog.get_logger(__name__)


# ─── Gmail Tool ───────────────────────────────────────────────────────────────

class GmailTool(BaseTool):
    """
    Tool for interacting with Gmail API.
    Wraps GmailService for agent use with structured I/O.
    """
    name = "gmail"
    description = "Send emails, search inbox, mark as read, sync emails via Gmail API"

    async def _run(self, action: str = "search", **kwargs) -> Any:
        from app.services.gmail_service import GmailService
        gmail = GmailService()

        if action == "mark_read":
            user_id = kwargs["user_id"]
            gmail_id = kwargs["gmail_id"]
            await gmail.mark_as_read_on_gmail(user_id, gmail_id)
            return {"action": "mark_read", "gmail_id": gmail_id, "success": True}

        elif action == "send_reply":
            result = await gmail.send_reply(
                user_id=kwargs["user_id"],
                to_email=kwargs["to_email"],
                subject=kwargs["subject"],
                body=kwargs["body"],
                thread_id=kwargs.get("thread_id"),
            )
            return {"action": "send_reply", "success": True, "result": result}

        elif action == "sync":
            await gmail.sync_emails(kwargs["user_id"])
            return {"action": "sync", "success": True}

        else:
            raise ValueError(f"Unknown Gmail action: {action}")


# ─── Calendar Tool ────────────────────────────────────────────────────────────

class CalendarTool(BaseTool):
    """
    Tool for interacting with Google Calendar API.
    Wraps calendar logic from meeting_intelligence.py for agent use.
    """
    name = "calendar"
    description = "Check availability, find conflicts, suggest meeting slots via Google Calendar"

    async def _run(self, action: str = "check_availability", **kwargs) -> Any:
        from app.ai_worker.tasks.meeting_intelligence import (
            check_calendar_availability,
            determine_availability,
        )
        from app.services.auth_service import AuthService

        if action == "check_availability":
            auth = AuthService()
            credentials = await auth.get_user_credentials(kwargs["user_id"])
            if not credentials:
                return {"availability": "unknown", "reason": "No calendar credentials"}

            window_start = kwargs["window_start"]
            window_end = kwargs["window_end"]

            events = await check_calendar_availability(credentials, window_start, window_end)
            result = determine_availability(
                kwargs["proposed_start"],
                kwargs["proposed_end"],
                events,
            )
            return {
                "availability": result["status"],
                "conflicts": [
                    {"title": c.get("title", ""), "start": str(c.get("start", "")), "end": str(c.get("end", ""))}
                    for c in result.get("conflicts", [])
                ],
                "total_events": len(events),
            }

        else:
            raise ValueError(f"Unknown Calendar action: {action}")


# ─── Draft Tool ───────────────────────────────────────────────────────────────

class DraftTool(BaseTool):
    """
    Tool for generating and managing email drafts.
    Wraps reply_draft.py and draft_service.py for agent use.
    """
    name = "draft"
    description = "Generate AI reply drafts using user's tone profile"

    async def _run(self, action: str = "generate", **kwargs) -> Any:
        from app.ai_worker.tasks.reply_draft import generate_reply_draft

        if action == "generate":
            result = await generate_reply_draft(
                subject=kwargs.get("subject", ""),
                body=kwargs.get("body", ""),
                sender=kwargs.get("sender", ""),
                sender_name=kwargs.get("sender_name", ""),
                is_meeting=kwargs.get("is_meeting", False),
                tone_profile=kwargs.get("tone_profile"),
                availability=kwargs.get("availability"),
                priority_score=kwargs.get("priority_score", 50),
                thread_messages=kwargs.get("thread_messages"),
            )
            return result

        else:
            raise ValueError(f"Unknown Draft action: {action}")


# ─── Search Tool ──────────────────────────────────────────────────────────────

class SearchTool(BaseTool):
    """
    Tool for searching emails and threads in MongoDB.
    Provides agents with historical email context.
    """
    name = "search"
    description = "Search emails, threads, and sender history in the database"

    async def _run(self, action: str = "sender_history", **kwargs) -> Any:
        from app.core.database import get_database
        db = get_database()

        if action == "sender_history":
            user_id = kwargs["user_id"]
            sender_email = kwargs["sender_email"]
            limit = kwargs.get("limit", 10)

            cursor = db.emails.find(
                {"user_id": user_id, "sender_email": sender_email},
                {"subject": 1, "category": 1, "ai_summary": 1, "received_at": 1, "priority_score": 1}
            ).sort("received_at", -1).limit(limit)

            emails = []
            async for doc in cursor:
                emails.append({
                    "subject": doc.get("subject", ""),
                    "category": doc.get("category"),
                    "summary": doc.get("ai_summary", ""),
                    "received_at": doc["received_at"].isoformat() if doc.get("received_at") else None,
                    "priority_score": doc.get("priority_score"),
                })
            return {"emails": emails, "count": len(emails)}

        elif action == "thread_context":
            user_id = kwargs["user_id"]
            thread_id = kwargs["thread_id"]

            cursor = db.emails.find(
                {"user_id": user_id, "thread_id": thread_id},
                {"subject": 1, "sender_name": 1, "sender_email": 1, "body_text": 1, "received_at": 1}
            ).sort("received_at", 1)

            messages = []
            async for doc in cursor:
                messages.append({
                    "sender_name": doc.get("sender_name", ""),
                    "sender_email": doc.get("sender_email", ""),
                    "body": doc.get("body_text", "")[:500],
                    "received_at": doc["received_at"].isoformat() if doc.get("received_at") else None,
                })
            return {"messages": messages, "thread_length": len(messages)}

        else:
            raise ValueError(f"Unknown Search action: {action}")


# ─── Analytics Tool ───────────────────────────────────────────────────────────

class AnalyticsTool(BaseTool):
    """
    Tool for retrieving email analytics and sender metrics.
    Wraps analytics_service.py and sender_intelligence.py.
    """
    name = "analytics"
    description = "Get email analytics, sender metrics, and priority statistics"

    async def _run(self, action: str = "sender_profile", **kwargs) -> Any:
        from app.services.sender_intelligence import SenderIntelligenceService

        if action == "sender_profile":
            svc = SenderIntelligenceService()
            profile = await svc.get_or_build_profile(
                kwargs["user_id"],
                kwargs["sender_email"],
            )
            # Serialize safely
            return {
                "sender_email": profile.get("sender_email", ""),
                "sender_name": profile.get("sender_name", ""),
                "total_emails": profile.get("total_emails", 0),
                "read_rate": profile.get("read_rate", 0),
                "relationship_strength": profile.get("relationship_strength", 0),
                "is_vip": profile.get("is_vip", False),
                "is_cold_sender": profile.get("is_cold_sender", False),
                "engaged_threads": profile.get("engaged_threads", 0),
                "categories": profile.get("categories", {}),
            }

        else:
            raise ValueError(f"Unknown Analytics action: {action}")


# ─── Thread Context Tool ─────────────────────────────────────────────────────

class ThreadContextTool(BaseTool):
    """
    Tool for retrieving and summarizing email thread context.
    Provides conversation history for response generation.
    """
    name = "thread_context"
    description = "Get full thread context and conversation summary for an email"

    async def _run(self, action: str = "get_summary", **kwargs) -> Any:
        from app.services.thread_service import ThreadService

        if action == "get_summary":
            svc = ThreadService()
            summary = await svc.get_thread_summary(
                kwargs["user_id"],
                kwargs["thread_id"],
            )
            return summary

        elif action == "get_messages":
            # Direct DB query for raw thread messages
            from app.core.database import get_database
            db = get_database()
            cursor = db.emails.find(
                {"user_id": kwargs["user_id"], "thread_id": kwargs["thread_id"]},
                {"subject": 1, "sender_name": 1, "sender_email": 1, "body_text": 1, "received_at": 1}
            ).sort("received_at", 1)

            messages = []
            async for doc in cursor:
                messages.append({
                    "sender_name": doc.get("sender_name", ""),
                    "sender_email": doc.get("sender_email", ""),
                    "body": doc.get("body_text", "")[:500],
                    "received_at": doc["received_at"].isoformat() if doc.get("received_at") else None,
                })
            return {"messages": messages, "thread_length": len(messages)}

        else:
            raise ValueError(f"Unknown ThreadContext action: {action}")
