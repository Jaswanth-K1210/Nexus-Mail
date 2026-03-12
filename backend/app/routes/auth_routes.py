"""
Nexus Mail — Auth Routes
Google OAuth flow + consent status.
"""

from fastapi import APIRouter, HTTPException, Request, status
from app.services.auth_service import AuthService
from app.models.schemas import AuthCallbackRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_service = AuthService()


@router.get("/google/url")
async def get_google_auth_url():
    """
    Get the Google OAuth consent URL.
    Frontend redirects user to this URL to begin sign-up.
    """
    try:
        url = auth_service.get_authorization_url()
        return {"auth_url": url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate auth URL: {str(e)}",
        )


@router.post("/google/callback")
async def google_callback(request: Request, body: AuthCallbackRequest):
    """
    Handle Google OAuth callback.
    Per v3.1 spec: requires consent_given=True or returns 400.
    """
    try:
        # Extract IP and User Agent for consent recording
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        result = await auth_service.handle_callback(
            code=body.code,
            consent_given=body.consent_given,
            ip_address=ip_address or body.ip_address,
            user_agent=user_agent or body.user_agent,
        )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}",
        )

@router.post("/demo")
async def demo_login():
    """Development-only: Bypasses Google OAuth for local testing."""
    from app.core.config import get_settings
    settings = get_settings()
    if not settings.enable_demo_mode:
        raise HTTPException(status_code=403, detail="Demo mode is disabled")
    try:
        return await auth_service.demo_login()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Demo login failed: {str(e)}",
        )



@router.get("/consent-status")
async def consent_status(user: dict = None):
    """
    Check if the current user has a valid consent record.
    Per v3.1 spec section 3.3.
    """
    # In production, use `Depends(get_current_user)` for user
    if not user:
        return {"consent_given": False, "calendar_connected": False}

    result = await auth_service.get_consent_status(user["user_id"])
    return result
