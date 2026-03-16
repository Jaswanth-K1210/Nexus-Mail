"""
Nexus Mail — Auto-Reply Routes
Endpoints for managing the automatic reply feature.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.routes.middleware import get_current_user
from app.services.auto_reply_service import AutoReplyService
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auto-reply", tags=["Auto-Reply"])
auto_reply_service = AutoReplyService()


class AutoReplySettingsUpdate(BaseModel):
    enabled: bool
    categories: list[str] | None = None


@router.get("/settings")
async def get_auto_reply_settings(user: dict = Depends(get_current_user)):
    """Get the user's auto-reply configuration."""
    return await auto_reply_service.get_settings(user["user_id"])


@router.put("/settings")
async def update_auto_reply_settings(
    body: AutoReplySettingsUpdate,
    user: dict = Depends(get_current_user),
):
    """Update auto-reply settings."""
    return await auto_reply_service.update_settings(
        user["user_id"], body.enabled, body.categories
    )


@router.get("/log")
async def get_auto_reply_log(user: dict = Depends(get_current_user)):
    """Get the history of auto-sent replies."""
    replies = await auto_reply_service.get_auto_reply_log(user["user_id"])
    return {"replies": replies}


@router.get("/stats")
async def get_auto_reply_stats(user: dict = Depends(get_current_user)):
    """Get auto-reply statistics."""
    return await auto_reply_service.get_stats(user["user_id"])
