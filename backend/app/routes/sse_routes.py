"""
Nexus Mail — SSE and Events Routes
Real-time Server-Sent Events endpoint replacing the 60s polling model.
"""

from fastapi import APIRouter, Depends, Request
from app.routes.middleware import get_current_user
from app.services.sse_service import create_sse_response, get_connection_count

router = APIRouter(prefix="/events", tags=["Real-Time Events"])


@router.get("/stream")
async def sse_stream(request: Request, user: dict = Depends(get_current_user)):
    """
    Server-Sent Events stream for real-time notifications.

    Replaces the 60-second polling mechanism.
    Frontend connects once and receives push events:
    - meeting_alert: New meeting invitation detected
    - email_processed: Email finished AI processing
    - sync_complete: Gmail sync finished
    - reply_received: Someone replied to a tracked email

    Usage (frontend):
        const es = new EventSource('/api/events/stream', { headers: { Authorization: 'Bearer ...' } });
        es.addEventListener('meeting_alert', (e) => { ... });
    """
    return create_sse_response(user["user_id"], request)


@router.get("/status")
async def sse_status():
    """Get current SSE connection stats (for monitoring)."""
    return {"active_connections": get_connection_count()}
