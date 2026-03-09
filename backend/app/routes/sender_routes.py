"""
Nexus Mail — Sender Intelligence Routes
Endpoints to retrieve comprehensive sender profiles.
"""

from fastapi import APIRouter, Depends, HTTPException
from app.routes.middleware import get_current_user
from app.services.sender_intelligence import SenderIntelligenceService

router = APIRouter(prefix="/senders", tags=["Sender Intelligence"])
sender_service = SenderIntelligenceService()


@router.get("/{sender_email}/profile")
async def get_sender_profile(
    sender_email: str,
    user: dict = Depends(get_current_user),
):
    """
    Get a comprehensive intelligence profile for a specific sender.
    Includes relationship strength, read rates, cold email risk, and classification stats.
    """
    profile = await sender_service.get_or_build_profile(
        user["user_id"], sender_email
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile could not be generated")
        
    return profile
