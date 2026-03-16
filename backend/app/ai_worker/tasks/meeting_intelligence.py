"""
Nexus Mail — Task 2: Meeting Intelligence
Conditional task — runs only if is_meeting_invitation is true.
Extracts meeting data, checks Google Calendar, creates meeting alert.
Per v3.1 spec: Section 4 (Meeting Intelligence Engine).
"""

import asyncio
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateutil_parser
from dateutil.tz import gettz

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from bson import ObjectId

from app.ai_worker.ai_provider import ai_provider, TaskType
from app.core.database import get_database
from app.core.config import get_settings

import structlog

logger = structlog.get_logger(__name__)

# ──────────────────────────────────────────────
# Meeting Data Extraction Prompt
# ──────────────────────────────────────────────

EXTRACT_MEETING_PROMPT = """You are an AI assistant that extracts structured meeting data from email content.

Extract the following fields from the email. If a field cannot be determined, use the default value.

Respond in JSON format:
{
    "proposed_datetime": "<ISO 8601 format, e.g. 2026-03-07T15:00:00>",
    "proposed_timezone": "<IANA timezone, e.g. Asia/Kolkata, America/New_York>",
    "duration_minutes": <integer, default 60 if not mentioned>,
    "meeting_link": "<URL or null if not found>",
    "meeting_platform": "<google_meet | zoom | teams | calendly | other>",
    "is_ics_attached": false,
    "confidence_score": <0.0-1.0 how confident this is a real meeting invite>
}

Rules:
- Parse natural language dates like "Thursday at 3pm", "next Monday morning", "March 10th, 10:30 AM"
- If only a day is mentioned without time, default to 10:00 AM
- Detect meeting platforms from URLs: meet.google.com → google_meet, zoom.us → zoom, teams.microsoft.com → teams
- If timezone is not explicit, try to infer from context or default to UTC
- Duration: look for phrases like "30 min", "1 hour", "45 minutes". Default to 60."""


async def extract_meeting_data(email_body: str, sender: str, subject: str) -> dict:
    """
    Extract structured meeting data from email content using AI.
    Stage 2 of the Meeting Intelligence Engine.
    """
    user_prompt = f"""Extract meeting details from this email:

FROM: {sender}
SUBJECT: {subject}

BODY:
{email_body[:3000]}"""

    try:
        result = await ai_provider.complete_json(
            system_prompt=EXTRACT_MEETING_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
            task_type=TaskType.MEETING_INTELLIGENCE,
        )
        return result
    except Exception as e:
        logger.error("Meeting data extraction failed", error=str(e))
        return {
            "proposed_datetime": datetime.now(timezone.utc).isoformat(),
            "proposed_timezone": "UTC",
            "duration_minutes": 60,
            "meeting_link": None,
            "meeting_platform": "other",
            "is_ics_attached": False,
            "confidence_score": 0.0,
        }


def parse_datetime_to_utc(datetime_str: str, timezone_str: str) -> datetime:
    """
    Convert a datetime string with timezone to UTC.
    Per v3.1 spec: always store in UTC, keep original timezone for display.
    """
    try:
        dt = dateutil_parser.parse(datetime_str)

        # If naive (no timezone info), apply the provided timezone
        if dt.tzinfo is None:
            tz = gettz(timezone_str) or timezone.utc
            dt = dt.replace(tzinfo=tz)

        # Convert to UTC
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError) as e:
        logger.warning("Could not parse datetime", datetime_str=datetime_str, error=str(e))
        return datetime.now(timezone.utc)


async def check_calendar_availability(
    credentials: Credentials,
    window_start: datetime,
    window_end: datetime,
) -> list[dict]:
    """
    Check Google Calendar for events in the given time window.
    Stage 3 of the Meeting Intelligence Engine.
    Per v3.1 spec: 15-minute buffer before and after.
    """
    try:
        service = build("calendar", "v3", credentials=credentials)
        # BUG FIX: Google API calls are synchronous and block the event loop.
        # Run in a thread to avoid blocking all other async operations.
        def _fetch_events():
            return service.events().list(
                calendarId="primary",
                timeMin=window_start.isoformat(),
                timeMax=window_end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                fields="items(id,summary,start,end,status)",
            ).execute()

        events_result = await asyncio.to_thread(_fetch_events)

        events = events_result.get("items", [])
        return [
            {
                "title": e.get("summary", "Untitled"),
                "start": e["start"].get("dateTime", e["start"].get("date", "")),
                "end": e["end"].get("dateTime", e["end"].get("date", "")),
            }
            for e in events
            if e.get("status") != "cancelled"
        ]

    except Exception as e:
        logger.error("Calendar availability check failed", error=str(e))
        return []


def determine_availability(
    proposed_start: datetime,
    proposed_end: datetime,
    existing_events: list[dict],
) -> dict:
    """
    Determine availability status based on existing calendar events.
    Per v3.1 spec:
    - FREE: no events in the window
    - PARTIAL: events within 30 min but not directly overlapping
    - BUSY: at least one event directly overlaps
    """
    if not existing_events:
        return {"status": "free", "conflicts": []}

    conflicts = []
    has_direct_overlap = False

    for event in existing_events:
        try:
            event_start = dateutil_parser.parse(event["start"])
            event_end = dateutil_parser.parse(event["end"])

            # Check for direct overlap
            if event_start < proposed_end and event_end > proposed_start:
                has_direct_overlap = True
                conflicts.append({
                    "title": event["title"],
                    "start": event_start,
                    "end": event_end,
                })
        except (ValueError, KeyError):
            continue

    if has_direct_overlap:
        return {"status": "busy", "conflicts": conflicts}
    elif existing_events:
        return {"status": "partial", "conflicts": conflicts}
    else:
        return {"status": "free", "conflicts": []}


async def process_meeting_invitation(
    email_id: str,
    user_id: str,
    email_body: str,
    sender_name: str,
    sender_email: str,
    subject: str,
    thread_id: str | None = None,
    credentials: Credentials | None = None,
) -> dict | None:
    """
    Full Meeting Intelligence pipeline (Stages 1-5).
    Per v3.1 spec section 4.

    1. Extract meeting data using AI
    2. Convert to UTC datetime
    3. Check Google Calendar availability
    4. Create meeting_alert document
    5. Mark email as having pending alert
    """
    settings = get_settings()
    db = get_database()

    # Stage 1 & 2: Extract meeting data
    meeting_data = await extract_meeting_data(email_body, sender_email, subject)

    # Check confidence threshold
    confidence = meeting_data.get("confidence_score", 0)
    if confidence < settings.meeting_detection_confidence_threshold:
        logger.info(
            "Meeting confidence below threshold",
            confidence=confidence,
            threshold=settings.meeting_detection_confidence_threshold,
        )
        return None

    # Parse datetime to UTC
    proposed_dt = parse_datetime_to_utc(
        meeting_data.get("proposed_datetime", ""),
        meeting_data.get("proposed_timezone", "UTC"),
    )
    duration = meeting_data.get("duration_minutes", 60)

    # Check for duplicate: same sender, same time
    existing_alert = await db.meeting_alerts.find_one({
        "user_id": user_id,
        "sender_email": sender_email,
        "proposed_datetime": proposed_dt
    })
    
    if existing_alert:
        logger.info("Skipping duplicate meeting alert", email_id=email_id, proposed_time=proposed_dt.isoformat())
        await db.emails.update_one(
            {"_id": ObjectId(email_id)},
            {"$set": {"has_meeting_alert": True, "is_meeting_invitation": True}}
        )
        return {
            "alert_id": str(existing_alert["_id"]),
            "availability": existing_alert.get("availability", "free"),
            "proposed_datetime": proposed_dt.isoformat(),
            "duration_minutes": duration,
        }

    # Stage 3: Check calendar availability
    availability_result = {"status": "free", "conflicts": []}
    if credentials:
        window_start = proposed_dt - timedelta(minutes=15)
        window_end = proposed_dt + timedelta(minutes=duration + 15)

        events = await check_calendar_availability(credentials, window_start, window_end)
        availability_result = determine_availability(
            proposed_dt,
            proposed_dt + timedelta(minutes=duration),
            events,
        )

    # Stage 4: Create meeting_alert document
    alert_doc = {
        "user_id": user_id,
        "email_id": email_id,
        "thread_id": thread_id,
        "sender_name": sender_name,
        "sender_email": sender_email,
        "proposed_datetime": proposed_dt,
        "proposed_timezone": meeting_data.get("proposed_timezone", "UTC"),
        "duration_minutes": duration,
        "meeting_link": meeting_data.get("meeting_link"),
        "meeting_platform": meeting_data.get("meeting_platform", "other"),
        "availability": availability_result["status"],
        "conflict_events": [
            {
                "title": c["title"],
                "start": c["start"] if isinstance(c["start"], datetime) else dateutil_parser.parse(str(c["start"])),
                "end": c["end"] if isinstance(c["end"], datetime) else dateutil_parser.parse(str(c["end"])),
            }
            for c in availability_result["conflicts"]
        ],
        "status": "pending",
        "user_response": None,
        "suggested_time": None,
        "reply_sent": False,
        "calendar_event_id": None,
        "notification_sent": False,
        "created_at": datetime.now(timezone.utc),
        "resolved_at": None,
    }

    result = await db.meeting_alerts.insert_one(alert_doc)

    # Stage 5: Mark email as having a pending alert
    await db.emails.update_one(
        {"_id": ObjectId(email_id)},
        {"$set": {"has_meeting_alert": True, "is_meeting_invitation": True}}
    )

    logger.info(
        "Meeting alert created",
        alert_id=str(result.inserted_id),
        availability=availability_result["status"],
        proposed_time=proposed_dt.isoformat(),
    )

    return {
        "alert_id": str(result.inserted_id),
        "availability": availability_result["status"],
        "proposed_datetime": proposed_dt.isoformat(),
        "duration_minutes": duration,
    }
