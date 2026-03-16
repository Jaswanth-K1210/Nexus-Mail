"""
Nexus Mail — Auth Routes
Google OAuth flow + consent status.
"""

from fastapi import APIRouter, HTTPException, Request, status, Depends
from app.services.auth_service import AuthService
from app.models.schemas import AuthCallbackRequest
from app.routes.middleware import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_service = AuthService()


@router.get("/google/url")
async def get_google_auth_url(state: str | None = None):
    """
    Get the Google OAuth consent URL.
    Frontend redirects user to this URL to begin sign-up.
    Optionally accepts a state parameter for CSRF protection.
    """
    try:
        url = auth_service.get_authorization_url(state=state)
        return {"auth_url": url}
    except Exception as e:
        from structlog import get_logger
        get_logger(__name__).error("Failed to generate auth URL", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authentication URL. Please try again.",
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
            state=body.state,
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
        from structlog import get_logger
        get_logger(__name__).error("OAuth callback failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed. Please try again.",
        )

@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Return the current user's full profile."""
    return await auth_service.get_user_profile(user["user_id"])


@router.get("/consent-status")
async def consent_status(user: dict = Depends(get_current_user)):
    """
    Check if the current user has a valid consent record.
    Per v3.1 spec section 3.3.
    """
    result = await auth_service.get_consent_status(user["user_id"])
    return result
