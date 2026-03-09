"""
Nexus Mail — Reply Tracker Routes
Reply Zero-style tracking endpoints.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.routes.middleware import get_current_user
from app.services.reply_tracker_service import ReplyTrackerService

router = APIRouter(prefix="/replies", tags=["Reply Tracker"])
tracker = ReplyTrackerService()


class EmailIdRequest(BaseModel):
    email_id: str


@router.get("/stats")
async def reply_stats(user: dict = Depends(get_current_user)):
    """Get counts for To Reply, Awaiting Reply, and overdue items."""
    return await tracker.get_reply_stats(user["user_id"])


@router.get("/needs-reply")
async def needs_reply(
    filter_age: str | None = None,
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """Emails that need your reply (To Reply list)."""
    data = await tracker.get_needs_reply(user["user_id"], filter_age, limit)
    return {"emails": data}


@router.get("/awaiting")
async def awaiting_reply(
    filter_age: str | None = None,
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """Emails awaiting a reply from someone else."""
    data = await tracker.get_awaiting_reply(user["user_id"], filter_age, limit)
    return {"emails": data}


@router.post("/nudge/{email_id}")
async def generate_nudge(email_id: str, user: dict = Depends(get_current_user)):
    """AI-generates a polite follow-up nudge message."""
    return await tracker.generate_nudge(user["user_id"], email_id)


@router.post("/mark-replied")
async def mark_replied(body: EmailIdRequest, user: dict = Depends(get_current_user)):
    """Mark an email as replied to."""
    return await tracker.mark_as_replied(user["user_id"], body.email_id)


@router.post("/mark-done")
async def mark_done(body: EmailIdRequest, user: dict = Depends(get_current_user)):
    """Mark tracking as done — removes from all lists."""
    return await tracker.mark_as_done(user["user_id"], body.email_id)
