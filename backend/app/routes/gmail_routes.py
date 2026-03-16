"""
Nexus Mail — Gmail Routes
Email sync, status, and email listing endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.routes.middleware import get_current_user
from app.services.gmail_service import GmailService
from app.ai_worker.pipeline import ProcessingPipeline
from app.core.rate_limit import limiter
import structlog

logger = structlog.get_logger(__name__)

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
        logger.error("Failed to get Gmail status", user_id=user["user_id"], error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve Gmail status. Please try again later.",
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
        logger.error("Gmail sync failed", user_id=user["user_id"], error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync emails. Please try again later.",
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
        logger.error("AI processing failed", user_id=user["user_id"], error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process emails through AI. Please try again later.",
        )


@router.post("/reprocess")
@limiter.limit("2/minute")
async def reprocess_emails(request: Request, user: dict = Depends(get_current_user)):
    """
    Reset recent emails to unprocessed and run the AI pipeline again.
    Used when a user changes their role/context to reclassify their inbox.
    """
    from app.core.database import get_database
    db = get_database()
    
    try:
        # Reset the 50 most recent emails
        cursor = db.emails.find({"user_id": user["user_id"]}).sort("received_at", -1).limit(50)
        email_ids = [doc["_id"] async for doc in cursor]

        if hasattr(db.emails, "update_many"):
            if email_ids:
                await db.emails.update_many(
                    {"_id": {"$in": email_ids}},
                    {"$set": {"is_processed": False}}
                )
        
        # Process them with the new context
        result = await pipeline.process_unprocessed_emails(user["user_id"], limit=50)
        return {"status": "reprocessed", "count": len(email_ids), "result": result}
    except Exception as e:
        logger.error("Reprocessing failed", user_id=user["user_id"], error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reprocess emails. Please try again later.",
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
    """Get a single email with full details. Marks it as read in DB and Gmail."""
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

    # Mark as read on Gmail + DB when the user opens the email
    if not email.get("is_read"):
        await db.emails.update_one(
            {"_id": ObjectId(email_id)},
            {"$set": {"is_read": True}},
        )
        email["is_read"] = True

        # Mark as read on Gmail directly (remove UNREAD label)
        gmail_id = email.get("gmail_id")
        if gmail_id:
            try:
                gmail_svc = GmailService()
                await gmail_svc.mark_as_read_on_gmail(user["user_id"], gmail_id)
            except Exception as e:
                logger.warning("Gmail mark-as-read failed on open", gmail_id=gmail_id, error=str(e))

    email["_id"] = str(email["_id"])
    return email


@router.put("/emails/{email_id}/category")
async def update_email_category(email_id: str, body: dict, user: dict = Depends(get_current_user)):
    """Manually reclassify an email's category."""
    from bson import ObjectId
    from app.core.database import get_database

    db = get_database()

    valid_categories = [
        "important", "requires_response", "meeting_invitation",
        "newsletter", "promotional", "social", "transactional", "spam",
    ]
    new_category = body.get("category", "")
    if new_category not in valid_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Must be one of: {valid_categories}",
        )

    result = await db.emails.update_one(
        {"_id": ObjectId(email_id), "user_id": user["user_id"]},
        {"$set": {"category": new_category}},
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )

    return {"status": "updated", "category": new_category}


@router.get("/threads/{thread_id}")
async def get_thread(thread_id: str, user: dict = Depends(get_current_user)):
    """Get all emails in a thread, ordered oldest to newest."""
    from app.core.database import get_database

    db = get_database()

    cursor = db.emails.find(
        {"user_id": user["user_id"], "thread_id": thread_id},
        {"body_html": 0},
    ).sort("received_at", 1)

    messages = []
    async for msg in cursor:
        msg["_id"] = str(msg["_id"])
        messages.append(msg)

    if not messages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        )

    return {"thread_id": thread_id, "messages": messages, "count": len(messages)}
