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


class RefineDraftRequest(BaseModel):
    style: str = Field(..., description="One of: polish, formal, shorter")


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


@router.post("/{draft_id}/refine")
async def refine_draft(
    draft_id: str,
    body: RefineDraftRequest,
    user: dict = Depends(get_current_user),
):
    """Refine a draft body using AI — polish, make formal, or make shorter."""
    from app.core.database import get_database
    from app.ai_worker.ai_provider import ai_provider, TaskType
    from bson import ObjectId

    db = get_database()
    draft_doc = await db.email_drafts.find_one({
        "_id": ObjectId(draft_id),
        "user_id": user["user_id"],
        "status": "pending",
    })
    if not draft_doc:
        raise HTTPException(status_code=404, detail="Draft not found")

    current_body = draft_doc.get("draft_body", "")

    # Fetch the original email for context
    email_doc = await db.emails.find_one({"_id": ObjectId(draft_doc["email_id"])})
    original_subject = email_doc.get("subject", "") if email_doc else ""
    original_body = email_doc.get("body_text", "")[:1500] if email_doc else ""

    style_instructions = {
        "polish": "Improve the grammar, clarity, and flow of this reply. Fix any awkward phrasing. Keep the same tone and length. Make it sound natural and polished.",
        "formal": "Rewrite this reply in a highly professional, formal business tone. Use proper salutations and sign-offs. Avoid contractions and casual language. Keep the same core message.",
        "shorter": "Condense this reply to be as brief as possible while keeping the core message intact. Remove filler words and unnecessary pleasantries. Max 2 sentences.",
    }

    instruction = style_instructions.get(body.style)
    if not instruction:
        raise HTTPException(status_code=400, detail=f"Unknown style: {body.style}. Use: polish, formal, shorter")

    system_prompt = f"""You are a professional email writing assistant.
{instruction}

The original email this replies to:
SUBJECT: {original_subject}
BODY: {original_body}

Respond ONLY with the refined reply text. No JSON, no explanation, just the refined email reply body."""

    try:
        result = await ai_provider.complete(
            system_prompt=system_prompt,
            user_prompt=f"Refine this draft reply:\n\n{current_body}",
            temperature=0.3,
            task_type=TaskType.REPLY_DRAFT,
        )

        refined_body = result.strip()
        if not refined_body:
            raise HTTPException(status_code=500, detail="AI returned empty result")

        # Update the draft in DB
        await db.email_drafts.update_one(
            {"_id": ObjectId(draft_id)},
            {"$set": {"draft_body": refined_body}}
        )

        draft_doc["draft_body"] = refined_body
        draft_doc["_id"] = str(draft_doc["_id"])
        return draft_doc

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refinement failed: {str(e)}")


@router.post("/generate/{email_id}")
async def generate_draft_on_demand(email_id: str, user: dict = Depends(get_current_user)):
    """Generate a reply draft on-demand from the UI, with full thread context."""
    from app.core.database import get_database
    from app.ai_worker.tasks.reply_draft import generate_reply_draft
    from bson import ObjectId

    db = get_database()
    email_doc = await db.emails.find_one({"_id": ObjectId(email_id), "user_id": user["user_id"]})
    if not email_doc:
        raise HTTPException(status_code=404, detail="Email not found")

    if not email_doc.get("is_processed"):
        raise HTTPException(status_code=400, detail="Email has not been processed by AI yet. Please wait for processing to complete.")

    # Check if a draft already exists
    existing_draft = await db.email_drafts.find_one({
        "email_id": email_id,
        "user_id": user["user_id"],
        "status": "pending"
    })
    if existing_draft:
        existing_draft["_id"] = str(existing_draft["_id"])
        return existing_draft

    user_doc = await db.users.find_one({"_id": user["user_id"]})
    tone_profile = user_doc.get("tone_profile") if user_doc else None

    # Fetch full thread context if this email is part of a conversation
    thread_id = email_doc.get("thread_id")
    thread_messages = []
    if thread_id:
        cursor = db.emails.find(
            {"user_id": user["user_id"], "thread_id": thread_id}
        ).sort("received_at", 1)
        async for msg in cursor:
            thread_messages.append({
                "sender_name": msg.get("sender_name", ""),
                "sender_email": msg.get("sender_email", ""),
                "subject": msg.get("subject", ""),
                "body": msg.get("body_text", "")[:1500],
                "received_at": msg.get("received_at", ""),
            })

    # Use AI to generate draft with thread context
    reply = await generate_reply_draft(
        subject=email_doc.get("subject", ""),
        body=email_doc.get("body_text", ""),
        sender=email_doc.get("sender_email", ""),
        sender_name=email_doc.get("sender_name", ""),
        is_meeting=email_doc.get("is_meeting_invitation", False),
        tone_profile=tone_profile,
        availability=None,
        priority_score=email_doc.get("priority_score", 50),
        thread_messages=thread_messages if len(thread_messages) > 1 else None,
    )

    if not reply or not reply.get("reply_draft"):
        raise HTTPException(status_code=500, detail="AI failed to generate draft")

    # Store via draft service (auto-send logic evaluated inside)
    draft_result = await draft_service.create_draft(
        user_id=user["user_id"],
        email_id=email_id,
        draft_body=reply.get("reply_draft", ""),
        draft_type="reply",
        ai_confidence=reply.get("confidence", 0.8),
        recipient_email=email_doc.get("sender_email", ""),
        recipient_name=email_doc.get("sender_name", ""),
        subject=email_doc.get("subject", ""),
        thread_id=thread_id,
        source="on_demand",
    )

    new_draft = await db.email_drafts.find_one({"_id": ObjectId(draft_result["draft_id"])})
    if new_draft:
        new_draft["_id"] = str(new_draft["_id"])
        return new_draft

    raise HTTPException(status_code=500, detail="Failed to retrieve created draft")


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
