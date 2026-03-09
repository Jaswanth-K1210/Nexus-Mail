"""
Nexus Mail — Gmail Webhook Routes
Handles push notifications from Google Cloud Pub/Sub when new emails arrive.
Replaces the old manual polling pattern with real-time ingestion.
"""

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, status
import base64
import json

from app.services.gmail_service import GmailService
from app.core.database import get_database

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks/gmail", tags=["Webhooks"])
gmail_service = GmailService()


@router.post("")
async def receive_gmail_notification(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint for Google Cloud Pub/Sub to push notifications to.
    
    Payload format:
    {
      "message": {
        "data": "eyJlbWFpbEFkZHJlc3MiOiAidXNlckBleGFtcGxlLmNvbSIsICJoaXN0b3J5SWQiOiAiMTIzNDU2In0=",
        "messageId": "12345",
        "publishTime": "2024-03-01T12:00:00.000Z"
      },
      "subscription": "projects/myproject/subscriptions/mysubscription"
    }
    """
    try:
        body = await request.json()
        message = body.get("message", {})
        encoded_data = message.get("data")
        
        if not encoded_data:
            return {"status": "ignored", "reason": "no data payload"}
            
        # Decode base64 payload
        # Pad with "=" to ensure a multiple of 4
        padded = encoded_data + "=" * (-len(encoded_data) % 4)
        data_json = base64.urlsafe_b64decode(padded).decode("utf-8")
        data = json.loads(data_json)
        
        email_address = data.get("emailAddress")
        history_id = data.get("historyId")
        
        if not email_address:
            return {"status": "ignored", "reason": "missing emailAddress"}
            
        logger.info(
            "Push notification received", 
            email=email_address, 
            history_id=history_id
        )
        
        # Look up user_id by email
        db = get_database()
        user = await db.users.find_one({"email": email_address}, {"_id": 1})
        
        if not user:
            logger.warning("Unrecognized user in webhook", email=email_address)
            return {"status": "ignored", "reason": "user not found"}
            
        # Add background task to sync the new emails using historyId cursor
        user_id = str(user["_id"])
        background_tasks.add_task(gmail_service.sync_emails, user_id=user_id)
        
        # Acknowledge the message to Google Pub/Sub
        return {"status": "ok"}
        
    except Exception as e:
        logger.error("Error processing webhook", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid payload"
        )
