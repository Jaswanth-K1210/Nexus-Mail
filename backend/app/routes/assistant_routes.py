from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict
from datetime import datetime, timezone, timedelta
from app.routes.middleware import get_current_user
from app.core.database import get_database
from app.services.meeting_service import MeetingService
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/assistant", tags=["Assistant"])
meeting_service = MeetingService()

@router.get("/timeline")
async def get_specialist_timeline(user: dict = Depends(get_current_user)):
    """
    Returns a unified timeline of upcoming meetings, appointments, deadlines, and actionable tasks.
    Aggregates data from Google Calendar and AI-extracted email action items.
    """
    db = get_database()
    user_id = user["user_id"]
    
    try:
        # 1. Fetch Google Calendar events (expanded scope)
        events = await meeting_service.get_upcoming_events(user_id, max_results=30)
        
        # 2. Fetch pending action items from recent emails
        # Look at emails from the last 14 days that have action items
        fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)
        
        cursor = db.emails.find({
            "user_id": user_id,
            "is_processed": True,
            "action_items": {"$exists": True, "$not": {"$size": 0}},
            "received_at": {"$gte": fourteen_days_ago}
        }).sort("received_at", -1)
        
        action_items = []
        async for email in cursor:
            for item in email.get("action_items", []):
                if isinstance(item, dict):
                    action_text = item.get("action", str(item))
                    source_quote = item.get("source_quote", "")
                else:
                    action_text = str(item)
                    source_quote = ""

                action_items.append({
                    "id": str(email["_id"]),
                    "type": "action_item",
                    "text": action_text,
                    "source_sender": email.get("sender_name", ""),
                    "source_subject": email.get("subject", ""),
                    "received_at": email.get("received_at").isoformat() if hasattr(email.get("received_at"), 'isoformat') else email.get("received_at"),
                    "source_quote": source_quote
                })
        
        return {
            "calendar_events": events,
            "action_items": action_items
        }
    except Exception as e:
        logger.error("Failed to generate assistant timeline", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
