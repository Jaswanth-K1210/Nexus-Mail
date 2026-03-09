"""
Nexus Mail — Gmail Routes
Email sync, status, and email listing endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.routes.middleware import get_current_user
from app.services.gmail_service import GmailService
from app.ai_worker.pipeline import ProcessingPipeline
from app.core.rate_limit import limiter

router = APIRouter(prefix="/gmail", tags=["Gmail"])
gmail_service = GmailService()
pipeline = ProcessingPipeline()


@router.get("/status")
@limiter.limit("60/minute")
async def gmail_status(request: Request, user: dict = Depends(get_current_user)):
    """
    Get Gmail sync status + pending meeting alerts.
    Per v3.1 spec section 7.1 — extension polls this every 60 seconds.
    """
    try:
        result = await gmail_service.get_sync_status(user["user_id"])
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/sync")
@limiter.limit("5/minute")
async def sync_gmail(request: Request, user: dict = Depends(get_current_user)):
    """Trigger a Gmail sync for the current user."""
    try:
        result = await gmail_service.sync_emails(user["user_id"])
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/process")
@limiter.limit("5/minute")
async def process_emails(request: Request, user: dict = Depends(get_current_user)):
    """
    Process unprocessed emails through the AI pipeline.
    Runs all 6 tasks on each unprocessed email.
    """
    try:
        result = await pipeline.process_unprocessed_emails(user["user_id"])
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/emails")
async def list_emails(
    category: str | None = None,
    limit: int = 50,
    skip: int = 0,
    user: dict = Depends(get_current_user),
):
    """
    List processed emails with optional category filter.
    Returns AI-enriched email data.
    """
    from app.core.database import get_database
    db = get_database()

    query = {"user_id": user["user_id"], "is_processed": True}
    if category:
        query["category"] = category

    cursor = db.emails.find(
        query,
        {
            "body_text": 0,
            "body_html": 0,
        },
    ).sort("received_at", -1).skip(skip).limit(limit)

    emails = []
    async for email in cursor:
        email["_id"] = str(email["_id"])
        emails.append(email)

    total = await db.emails.count_documents(query)

    return {"emails": emails, "total": total, "limit": limit, "skip": skip}


@router.get("/emails/{email_id}")
async def get_email(email_id: str, user: dict = Depends(get_current_user)):
    """Get a single email with full details."""
    from bson import ObjectId
    from app.core.database import get_database

    db = get_database()

    email = await db.emails.find_one({
        "_id": ObjectId(email_id),
        "user_id": user["user_id"],
    })

    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )

    email["_id"] = str(email["_id"])
    return email
