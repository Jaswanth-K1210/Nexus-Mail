"""
Nexus Mail — Server-Sent Events (SSE) Service
Replaces the 60-second polling model with real-time push notifications.

Architecture change based on Superhuman analysis:
- Polling: 100K users = 100K requests/minute (most empty)
- SSE: Persistent lightweight connections, server pushes only when data exists
- Reduces backend load by orders of magnitude
- Notification latency: 60 seconds → sub-200 milliseconds
"""

import asyncio
import json
from datetime import datetime, timezone
from collections import defaultdict
from typing import AsyncGenerator

from fastapi import Request
from fastapi.responses import StreamingResponse

from app.core.database import get_database

import structlog

logger = structlog.get_logger(__name__)

# ─── Connection Registry ───
# Maps user_id → set of asyncio.Queue instances (one per connected client tab)
_connections: dict[str, set[asyncio.Queue]] = defaultdict(set)


def get_connection_count() -> int:
    """Total number of active SSE connections across all users."""
    return sum(len(queues) for queues in _connections.values())


async def push_to_user(user_id: str, event_type: str, data: dict) -> int:
    """
    Push an event to all connected clients for a given user.
    Returns the number of clients that received the event.

    This is the core function called by other services when they need
    to notify the user in real-time. Example:
        await push_to_user(user_id, "meeting_alert", alert_data)
    """
    queues = _connections.get(user_id, set())
    if not queues:
        return 0

    event = {
        "type": event_type,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    delivered = 0
    dead_queues = set()

    for queue in queues:
        try:
            queue.put_nowait(event)
            delivered += 1
        except asyncio.QueueFull:
            # Client is too slow to consume events — drop oldest
            try:
                queue.get_nowait()  # drop oldest
                queue.put_nowait(event)
                delivered += 1
            except Exception:
                dead_queues.add(queue)

    # Clean up dead connections
    for dq in dead_queues:
        _connections[user_id].discard(dq)

    if delivered > 0:
        logger.debug(
            "SSE event pushed",
            user_id=user_id,
            event_type=event_type,
            clients=delivered,
        )

    return delivered


async def event_stream(user_id: str, request: Request) -> AsyncGenerator[str, None]:
    """
    SSE event generator for a single client connection.
    Yields formatted SSE strings. Automatically cleans up on disconnect.
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    _connections[user_id].add(queue)

    logger.info("SSE client connected", user_id=user_id, total=get_connection_count())

    try:
        # Send initial connection confirmation
        yield _format_sse("connected", {"status": "ok", "user_id": user_id})

        # Send any pending alerts immediately on connect
        pending = await _get_pending_data(user_id)
        if pending:
            yield _format_sse("initial_state", pending)

        # Keep-alive + event loop
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            try:
                # Wait for events with a 30-second timeout (for keep-alive)
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield _format_sse(event["type"], event["data"])
            except asyncio.TimeoutError:
                # Send keep-alive comment to prevent connection timeout
                yield ": keep-alive\n\n"

    except asyncio.CancelledError:
        pass
    finally:
        _connections[user_id].discard(queue)
        if not _connections[user_id]:
            del _connections[user_id]
        logger.info("SSE client disconnected", user_id=user_id, total=get_connection_count())


def _format_sse(event_type: str, data: dict) -> str:
    """Format data as a proper SSE message string."""
    json_data = json.dumps(data, default=str)
    return f"event: {event_type}\ndata: {json_data}\n\n"


async def _get_pending_data(user_id: str) -> dict | None:
    """
    Fetch any pending data to send on initial SSE connection.
    This replaces the old polling — client gets everything immediately.
    """
    db = get_database()

    # Pending meeting alerts
    alerts = []
    cursor = db.meeting_alerts.find(
        {"user_id": user_id, "status": "pending"}
    ).sort("created_at", -1)

    async for alert in cursor:
        alerts.append({
            "id": str(alert["_id"]),
            "type": "meeting_invitation",
            "sender_name": alert.get("sender_name", ""),
            "sender_email": alert.get("sender_email", ""),
            "proposed_time": alert["proposed_datetime"].isoformat() if alert.get("proposed_datetime") else "",
            "duration_min": alert.get("duration_minutes", 60),
            "availability": alert.get("availability", "free"),
            "meeting_link": alert.get("meeting_link"),
        })

    # Reply tracker stats
    needs_reply = await db.emails.count_documents({
        "user_id": user_id,
        "category": {"$in": ["requires_response", "important"]},
        "replied": {"$ne": True},
        "reply_dismissed": {"$ne": True},
    })

    unread = await db.emails.count_documents({"user_id": user_id, "is_read": False})

    if not alerts and needs_reply == 0 and unread == 0:
        return None

    return {
        "pending_alerts": alerts,
        "needs_reply_count": needs_reply,
        "unread_count": unread,
    }


def create_sse_response(user_id: str, request: Request) -> StreamingResponse:
    """Create a FastAPI StreamingResponse for SSE."""
    return StreamingResponse(
        event_stream(user_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
