"""
Nexus Mail — Tone Learning Routes
Passive tone profile learning and management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.routes.middleware import get_current_user
from app.services.tone_learning_service import ToneLearningService
from app.core.database import get_database

router = APIRouter(prefix="/tone", tags=["Tone Learning"])
tone_service = ToneLearningService()


class UserContextUpdate(BaseModel):
    role: str                        # e.g. "Startup Founder", "Software Engineer"
    industry: str                    # e.g. "SaaS", "Finance", "Healthcare"
    company_size: str                # e.g. "Solo", "Startup (1-10)", "SMB (10-100)", "Enterprise"
    important_senders: list[str]     # e.g. ["investors", "clients", "team", "vendors"]
    custom_persona: str = ""         # free-form override


@router.post("/learn")
async def learn_tone(user: dict = Depends(get_current_user)):
    """
    Trigger tone learning from user's sent emails.
    Scans last 25 sent emails and builds a stylistic profile.
    Called automatically on first login, can also be triggered manually.
    """
    return await tone_service.learn_from_sent_emails(user["user_id"])


@router.get("/profile")
async def get_tone_profile(user: dict = Depends(get_current_user)):
    """Get the user's current learned tone profile."""
    profile = await tone_service.get_tone_profile(user["user_id"])
    if not profile:
        return {"status": "not_learned", "profile": None}
    return profile


@router.get("/context")
async def get_user_context(user: dict = Depends(get_current_user)):
    """Get the user's explicitly set professional context."""
    from bson import ObjectId
    db = get_database()
    doc = await db.users.find_one(
        {"_id": ObjectId(user["user_id"])},
        {"user_context": 1}
    )
    return doc.get("user_context", {}) if doc else {}


@router.patch("/context")
async def update_user_context(
    body: UserContextUpdate,
    user: dict = Depends(get_current_user)
):
    """
    Let users explicitly declare their professional role and context.
    This is merged with the passively-learned tone profile and injected
    into the email classifier prompt so emails are prioritised correctly
    from day 1 — before enough sent emails exist for passive learning.
    """
    from bson import ObjectId
    db = get_database()

    # Build a rich persona string from structured fields for the AI prompt
    important_str = ", ".join(body.important_senders) if body.important_senders else "team members and key contacts"
    persona = (
        body.custom_persona.strip()
        or f"I am a {body.role} in the {body.industry} industry at a {body.company_size} company. "
           f"My most important emails come from: {important_str}. "
           f"Emails about fundraising, customers, hiring, and product are high priority for me."
    )

    context_doc = {
        "role": body.role,
        "industry": body.industry,
        "company_size": body.company_size,
        "important_senders": body.important_senders,
        "custom_persona": body.custom_persona,
        "generated_persona": persona,
    }

    await db.users.update_one(
        {"_id": ObjectId(user["user_id"])},
        {"$set": {
            "user_context": context_doc,
            # Also write to tone_profile.professional_persona so the pipeline picks it up immediately
            "tone_profile.professional_persona": persona,
        }},
        upsert=False,
    )

    return {"status": "saved", "persona": persona}


@router.post("/refresh")
async def refresh_tone(user: dict = Depends(get_current_user)):
    """Refresh the tone profile if it's older than 7 days, otherwise skip."""
    return await tone_service.refresh_if_stale(user["user_id"])
