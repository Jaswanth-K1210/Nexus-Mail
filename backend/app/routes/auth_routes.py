"""
Nexus Mail — Auth Routes
Google OAuth flow + consent status.
"""

from fastapi import APIRouter, HTTPException, Request, status, Depends, BackgroundTasks
from app.services.auth_service import AuthService
from app.models.schemas import AuthCallbackRequest
from app.routes.middleware import get_current_user
from app.core.security import create_access_token

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
async def google_callback(request: Request, body: AuthCallbackRequest, background_tasks: BackgroundTasks):
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

        # Trigger immediate background sync
        from app.services.gmail_service import GmailService
        from app.ai_worker.pipeline import ProcessingPipeline
        import asyncio
        from structlog import get_logger
        
        async def run_initial_sync(user_id: str):
            logger = get_logger(__name__)
            try:
                logger.info("Starting immediate background sync after login", user_id=user_id)
                svc = GmailService()
                pipe = ProcessingPipeline()
                await svc.sync_emails(user_id)
                await pipe.process_unprocessed_emails(user_id, limit=20)
                logger.info("Immediate background sync complete", user_id=user_id)
            except Exception as e:
                logger.error("Failed immediate background sync", user_id=user_id, error=str(e))
                
        user_id = result["user"]["id"]
        background_tasks.add_task(run_initial_sync, user_id)

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


@router.post("/refresh")
async def refresh_token(user: dict = Depends(get_current_user)):
    """Issue a fresh JWT if the current token is still valid."""
    new_token = create_access_token(
        data={"sub": user["user_id"], "email": user.get("email", "")}
    )
    return {"access_token": new_token, "token_type": "bearer"}


@router.get("/consent-status")
async def consent_status(user: dict = Depends(get_current_user)):
    """
    Check if the current user has a valid consent record.
    Per v3.1 spec section 3.3.
    """
    result = await auth_service.get_consent_status(user["user_id"])
    return result
