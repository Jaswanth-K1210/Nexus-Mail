"""
Nexus Mail — Cold Email Blocker Routes
AI-powered cold email detection and blocking endpoints.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.routes.middleware import get_current_user
from app.services.cold_email_service import ColdEmailBlocker

router = APIRouter(prefix="/cold-emails", tags=["Cold Email Blocker"])
blocker = ColdEmailBlocker()


class BlockerSettingsRequest(BaseModel):
    enabled: Optional[bool] = None
    mode: Optional[str] = None  # "list" | "auto_label" | "auto_archive_label"
    custom_prompt: Optional[str] = None
    label_name: Optional[str] = None


class WhitelistRequest(BaseModel):
    sender_email: str


@router.get("/settings")
async def get_settings(user: dict = Depends(get_current_user)):
    """Get current cold email blocker settings."""
    return await blocker.get_blocker_settings(user["user_id"])


@router.put("/settings")
async def update_settings(
    body: BlockerSettingsRequest, user: dict = Depends(get_current_user)
):
    """Update blocker settings (enable/disable, mode, custom prompt)."""
    return await blocker.update_settings(
        user["user_id"],
        enabled=body.enabled,
        mode=body.mode,
        custom_prompt=body.custom_prompt,
        label_name=body.label_name,
    )


@router.get("/list")
async def list_cold_emails(limit: int = 50, user: dict = Depends(get_current_user)):
    """List detected cold emails."""
    data = await blocker.get_cold_emails(user["user_id"], limit)
    return {"emails": data}


@router.post("/whitelist")
async def whitelist_sender(
    body: WhitelistRequest, user: dict = Depends(get_current_user)
):
    """Add a sender to whitelist — never flag as cold email."""
    return await blocker.whitelist_sender(user["user_id"], body.sender_email)
