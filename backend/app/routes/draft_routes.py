"""
Nexus Mail — Draft Routes
CRUD endpoints for draft-first workflow.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from app.routes.middleware import get_current_user
from app.services.draft_service import DraftService

router = APIRouter(prefix="/drafts", tags=["Draft-First Mode"])
draft_service = DraftService()


class EditDraftRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=10000)


class AutoSendSettingsRequest(BaseModel):
    enabled: bool
    threshold: float = Field(default=0.95, ge=0.8, le=1.0)


@router.get("")
async def list_pending_drafts(user: dict = Depends(get_current_user)):
    """List all pending drafts awaiting user review."""
    drafts = await draft_service.get_pending_drafts(user["user_id"])
    return {"drafts": drafts, "count": len(drafts)}


@router.post("/{draft_id}/approve")
async def approve_draft(draft_id: str, user: dict = Depends(get_current_user)):
    """Approve a draft — sends the email via Gmail."""
    try:
        return await draft_service.approve_draft(draft_id, user["user_id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{draft_id}/reject")
async def reject_draft(draft_id: str, user: dict = Depends(get_current_user)):
    """Reject a draft — discards without sending."""
    try:
        return await draft_service.reject_draft(draft_id, user["user_id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{draft_id}/edit")
async def edit_draft(
    draft_id: str,
    body: EditDraftRequest,
    user: dict = Depends(get_current_user),
):
    """Edit a draft's body text before sending."""
    try:
        return await draft_service.edit_draft(draft_id, user["user_id"], body.body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/settings/auto-send")
async def get_auto_send_settings(user: dict = Depends(get_current_user)):
    """Get auto-send configuration."""
    return await draft_service.get_auto_send_settings(user["user_id"])


@router.put("/settings/auto-send")
async def update_auto_send_settings(
    settings: AutoSendSettingsRequest,
    user: dict = Depends(get_current_user),
):
    """Update auto-send configuration. Minimum threshold is 0.8."""
    return await draft_service.update_auto_send_settings(
        user["user_id"], settings.enabled, settings.threshold
    )
