from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from app.routes.middleware import get_current_user
from app.core.database import get_database
from app.services.meeting_service import MeetingService
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/assistant", tags=["Assistant"])
meeting_service = MeetingService()


def extract_name_from_email(email_address: str) -> str:
    """Extract a readable name from an email address.
    e.g. 'john.doe@gmail.com' -> 'John Doe', 'alice_smith@company.com' -> 'Alice Smith'
    """
    if not email_address or "@" not in email_address:
        return email_address or "Unknown"
    local_part = email_address.split("@")[0]
    # Replace common separators with spaces
    name = local_part.replace(".", " ").replace("_", " ").replace("-", " ")
    # Title case each word
    return name.title()


class UpdateActionStatusRequest(BaseModel):
    action_id: str
    status: str  # "done", "cancelled", "rescheduled", "resolved"


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

        # 2. Get action item statuses for this user
        status_doc = await db.action_statuses.find_one({"user_id": user_id})
        statuses = status_doc.get("statuses", {}) if status_doc else {}

        # 3. Fetch action items from recent emails
        fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)

        cursor = db.emails.find({
            "user_id": user_id,
            "is_processed": True,
            "action_items": {"$exists": True, "$not": {"$size": 0}},
            "received_at": {"$gte": fourteen_days_ago}
        }).sort("received_at", -1)

        action_items = []
        async for email in cursor:
            for idx, item in enumerate(email.get("action_items", [])):
                action_id = f"{email['_id']}_{idx}"

                if isinstance(item, dict):
                    action_text = item.get("action") or item.get("task") or str(item)
                    source_quote = item.get("source_quote", "")
                    item_type = item.get("type", "other")
                else:
                    action_text = str(item)
                    source_quote = ""
                    item_type = "other"

                # Build sender display name
                sender_name = email.get("sender_name", "")
                if not sender_name or not sender_name.strip():
                    sender_name = extract_name_from_email(email.get("sender", ""))

                item_status = statuses.get(action_id, "pending")

                action_items.append({
                    "id": action_id,
                    "type": item_type,
                    "text": action_text,
                    "status": item_status,
                    "source_sender": sender_name,
                    "source_subject": email.get("subject", ""),
                    "received_at": email.get("received_at").isoformat() if hasattr(email.get("received_at"), 'isoformat') else email.get("received_at"),
                    "source_quote": source_quote
                })

        # 4. Inject local statuses into calendar events
        for event in events:
            event_key = f"event_{event['id']}"
            local_status = statuses.get(event_key)
            event["local_status"] = local_status or "pending"

        return {
            "calendar_events": events,
            "action_items": action_items
        }
    except Exception as e:
        logger.error("Assistant timeline generation failed", user_id=user["user_id"], error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate assistant timeline. Please try again later.",
        )


@router.post("/timeline/resolve")
async def update_action_status(body: UpdateActionStatusRequest, user: dict = Depends(get_current_user)):
    """Update the status of an action item (done, cancelled, rescheduled, resolved)."""
    db = get_database()
    user_id = user["user_id"]

    valid_statuses = {"done", "cancelled", "rescheduled", "resolved"}
    if body.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    await db.action_statuses.update_one(
        {"user_id": user_id},
        {"$set": {f"statuses.{body.action_id}": body.status}},
        upsert=True
    )

    return {"status": body.status, "action_id": body.action_id}
