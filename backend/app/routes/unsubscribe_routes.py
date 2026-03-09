"""
Nexus Mail — Unsubscribe Routes
Bulk newsletter unsubscribe management endpoints.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.routes.middleware import get_current_user
from app.services.unsubscribe_service import UnsubscribeService

router = APIRouter(prefix="/unsubscribe", tags=["Bulk Unsubscriber"])
unsub_service = UnsubscribeService()


class AutoArchiveRequest(BaseModel):
    sender_email: str
    label: Optional[str] = None


class SenderRequest(BaseModel):
    sender_email: str


@router.get("/senders")
async def list_newsletter_senders(
    sort_by: str = "total_count",
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """List newsletter/promotional senders with email counts and read rates."""
    data = await unsub_service.get_newsletter_senders(user["user_id"], sort_by, limit)
    return {"senders": data}


@router.post("/unsubscribe")
async def unsubscribe(body: SenderRequest, user: dict = Depends(get_current_user)):
    """One-click unsubscribe from a sender."""
    return await unsub_service.unsubscribe(user["user_id"], body.sender_email)


@router.post("/auto-archive")
async def auto_archive(body: AutoArchiveRequest, user: dict = Depends(get_current_user)):
    """Set auto-archive (with optional label) for a sender."""
    return await unsub_service.auto_archive(user["user_id"], body.sender_email, body.label)


@router.post("/keep")
async def keep_sender(body: SenderRequest, user: dict = Depends(get_current_user)):
    """Mark sender as 'keep' — hides from unsubscribe list."""
    return await unsub_service.keep_sender(user["user_id"], body.sender_email)
