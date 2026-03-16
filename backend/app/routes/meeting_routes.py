"""
Nexus Mail — Meeting Routes
Meeting alert management endpoints.
Per v3.1 spec section 5.1: all 6 endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
import structlog
from app.routes.middleware import get_current_user
from app.core.database import get_database
from app.services.meeting_service import MeetingService
from app.models.schemas import MeetingDeclineRequest, MeetingSuggestRequest

router = APIRouter(prefix="/meetings", tags=["Meetings"])
meeting_service = MeetingService()
logger = structlog.get_logger(__name__)


@router.get("/pending")
async def get_pending_meetings(user: dict = Depends(get_current_user)):
    """
    Returns all pending meeting alerts for the current user.
    Used by dashboard + extension poll.
    """
    try:
        alerts = await meeting_service.get_pending_alerts(user["user_id"])
        return {"alerts": alerts}
    except Exception as e:
        logger.error("Failed to get pending meetings", user_id=user["user_id"], error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error. Please try again.",
        )

@router.get("/upcoming")
async def get_upcoming_events(user: dict = Depends(get_current_user)):
    """
    Returns upcoming Google Calendar events for the current user,
    with local status overrides (done, cancelled, rescheduled).
    """
    try:
        db = get_database()
        events = await meeting_service.get_upcoming_events(user["user_id"])

        # Inject local statuses
        status_doc = await db.action_statuses.find_one({"user_id": user["user_id"]})
        statuses = status_doc.get("statuses", {}) if status_doc else {}

        for event in events:
            event_key = f"event_{event['id']}"
            event["local_status"] = statuses.get(event_key, "pending")

        return {"events": events}
    except Exception as e:
        logger.error("Failed to get upcoming events", user_id=user["user_id"], error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error. Please try again.",
        )


@router.post("/{alert_id}/accept")
async def accept_meeting(alert_id: str, user: dict = Depends(get_current_user)):
    """
    Accept a meeting invitation.
    Per v3.1 spec section 5.2: sends reply, creates calendar event.
    """
    try:
        result = await meeting_service.accept_meeting(alert_id, user["user_id"])
        return result
    except ValueError as e:
        logger.warning("Validation error accepting meeting", user_id=user["user_id"], alert_id=alert_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Alert does not belong to this user",
        )
    except Exception as e:
        logger.error("Unexpected error accepting meeting", user_id=user["user_id"], alert_id=alert_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error. Please try again.",
        )


@router.post("/{alert_id}/decline")
async def decline_meeting(
    alert_id: str,
    body: MeetingDeclineRequest = MeetingDeclineRequest(),
    user: dict = Depends(get_current_user),
):
    """
    Decline a meeting invitation.
    Per v3.1 spec section 5.3. Optional reason in body.
    """
    try:
        result = await meeting_service.decline_meeting(
            alert_id, user["user_id"], body.reason
        )
        return result
    except ValueError as e:
        logger.warning("Validation error declining meeting", user_id=user["user_id"], alert_id=alert_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Alert does not belong to this user",
        )
    except Exception as e:
        logger.error("Unexpected error declining meeting", user_id=user["user_id"], alert_id=alert_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error. Please try again.",
        )


@router.post("/{alert_id}/suggest")
async def suggest_time(
    alert_id: str,
    body: MeetingSuggestRequest,
    user: dict = Depends(get_current_user),
):
    """
    Suggest an alternative meeting time.
    Per v3.1 spec section 5.4.
    """
    try:
        result = await meeting_service.suggest_time(
            alert_id, user["user_id"], body.suggested_datetime
        )
        return result
    except ValueError as e:
        logger.warning("Validation error suggesting time", user_id=user["user_id"], alert_id=alert_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Alert does not belong to this user",
        )
    except Exception as e:
        logger.error("Unexpected error suggesting time", user_id=user["user_id"], alert_id=alert_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error. Please try again.",
        )


@router.get("/{alert_id}/availability")
async def check_availability(
    alert_id: str, user: dict = Depends(get_current_user)
):
    """
    Real-time calendar availability check.
    Per v3.1 spec: used when 'Suggest Another Time' is clicked.
    Returns next available slots.
    """
    try:
        result = await meeting_service.get_availability(alert_id, user["user_id"])
        return result
    except ValueError as e:
        logger.warning("Validation error checking availability", user_id=user["user_id"], alert_id=alert_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Unexpected error checking availability", user_id=user["user_id"], alert_id=alert_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error. Please try again.",
        )


@router.post("/{alert_id}/dismiss")
async def dismiss_alert(alert_id: str, user: dict = Depends(get_current_user)):
    """
    Dismiss a meeting alert without taking action.
    Sets status to 'dismissed'.
    """
    try:
        result = await meeting_service.dismiss_alert(alert_id, user["user_id"])
        return result
    except ValueError as e:
        logger.warning("Validation error dismissing alert", user_id=user["user_id"], alert_id=alert_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Unexpected error dismissing alert", user_id=user["user_id"], alert_id=alert_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error. Please try again.",
        )
