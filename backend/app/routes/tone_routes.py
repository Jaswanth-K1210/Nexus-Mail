"""
Nexus Mail — Tone Learning Routes
Passive tone profile learning and management endpoints.
"""

from fastapi import APIRouter, Depends
from app.routes.middleware import get_current_user
from app.services.tone_learning_service import ToneLearningService

router = APIRouter(prefix="/tone", tags=["Tone Learning"])
tone_service = ToneLearningService()


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


@router.post("/refresh")
async def refresh_tone(user: dict = Depends(get_current_user)):
    """Refresh the tone profile if it's older than 7 days, otherwise skip."""
    return await tone_service.refresh_if_stale(user["user_id"])
