"""
Nexus Mail — Meeting Service
Handles Accept/Decline/Suggest flows for meeting invitations.
Per v3.1 spec section 5: User Response Handling.
"""

from datetime import datetime, timedelta, timezone
from bson import ObjectId

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from app.core.database import get_database
from app.core.config import get_settings
from app.services.auth_service import AuthService
from app.services.gmail_service import GmailService
from app.ai_worker.ai_provider import ai_provider, TaskType

import structlog

logger = structlog.get_logger(__name__)


class MeetingService:
    """
    Handles the meeting Accept/Decline/Suggest flows.
    Per v3.1 spec sections 5 and 6.
    """

    def __init__(self):
        self.auth_service = AuthService()
        self.gmail_service = GmailService()

    async def accept_meeting(self, alert_id: str, user_id: str) -> dict:
        """
        Accept Flow — v3.1 spec section 5.2 (10 steps).
        1. Verify alert is pending + belongs to user
        2. Fetch user tone profile + original email
        3. Generate acceptance reply via AI
        4. Send reply via Gmail API
        5. Create Google Calendar event
        6. Update meeting_alert status
        """
        db = get_database()

        # Step 1 & 2: Fetch and verify alert
        alert = await db.meeting_alerts.find_one({"_id": ObjectId(alert_id)})
        if not alert:
            raise ValueError("Meeting alert not found")
        if alert["user_id"] != user_id:
            raise PermissionError("Alert does not belong to this user")
        if alert["status"] != "pending":
            raise ValueError(f"Alert is not pending (status: {alert['status']})")

        # Get user credentials and info
        credentials = await self.auth_service.get_user_credentials(user_id)
        if not credentials:
            raise ValueError("No Google credentials found")

        user = await db.users.find_one({"_id": ObjectId(user_id)})
        tone_profile = user.get("tone_profile") if user else None

        # Get original email
        # BUG FIX: alert["email_id"] is a string, need ObjectId for MongoDB _id lookup
        email_doc = await db.emails.find_one({"_id": ObjectId(alert["email_id"])})

        # Step 3: Generate acceptance reply
        reply_text = await self._generate_accept_reply(
            sender_name=alert["sender_name"],
            proposed_time=alert["proposed_datetime"],
            subject=email_doc.get("subject", "") if email_doc else "",
            tone_profile=tone_profile,
        )

        # Step 4: Send the reply via Gmail
        if email_doc:
            await self.gmail_service.send_reply(
                user_id=user_id,
                to_email=alert["sender_email"],
                subject=email_doc.get("subject", "Meeting Confirmation"),
                body=reply_text,
                thread_id=email_doc.get("thread_id"),
            )

        # Step 5: Create Google Calendar event
        calendar_event_id = await self._create_calendar_event(
            credentials=credentials,
            sender_name=alert["sender_name"],
            proposed_datetime=alert["proposed_datetime"],
            proposed_timezone=alert.get("proposed_timezone", "UTC"),
            duration_minutes=alert.get("duration_minutes", 60),
            meeting_link=alert.get("meeting_link"),
            subject=email_doc.get("subject", "") if email_doc else "",
        )

        # Step 6: Update alert status
        await db.meeting_alerts.update_one(
            {"_id": ObjectId(alert_id), "user_id": user_id},
            {
                "$set": {
                    "status": "accepted",
                    "user_response": "yes",
                    "reply_sent": True,
                    "calendar_event_id": calendar_event_id,
                    "resolved_at": datetime.now(timezone.utc),
                }
            },
        )

        event_title = f"Meeting with {alert['sender_name']}"

        logger.info(
            "Meeting accepted",
            alert_id=alert_id,
            calendar_event_id=calendar_event_id,
        )

        return {
            "calendar_event_id": calendar_event_id,
            "reply_preview": reply_text,
            "event_title": event_title,
            "event_time": alert["proposed_datetime"].isoformat(),
        }

    async def decline_meeting(
        self, alert_id: str, user_id: str, reason: str | None = None
    ) -> dict:
        """
        Decline Flow — v3.1 spec section 5.3.
        Generates polite decline, sends via Gmail, updates alert.
        """
        db = get_database()

        alert = await db.meeting_alerts.find_one({"_id": ObjectId(alert_id)})
        if not alert:
            raise ValueError("Meeting alert not found")
        if alert["user_id"] != user_id:
            raise PermissionError("Alert does not belong to this user")
        if alert["status"] != "pending":
            raise ValueError(f"Alert is not pending (status: {alert['status']})")

        user = await db.users.find_one({"_id": ObjectId(user_id)})
        tone_profile = user.get("tone_profile") if user else None

        email_doc = await db.emails.find_one({"_id": ObjectId(alert["email_id"])})

        # Generate decline reply
        reply_text = await self._generate_decline_reply(
            sender_name=alert["sender_name"],
            reason=reason,
            tone_profile=tone_profile,
        )

        # Send via Gmail
        if email_doc:
            await self.gmail_service.send_reply(
                user_id=user_id,
                to_email=alert["sender_email"],
                subject=email_doc.get("subject", ""),
                body=reply_text,
                thread_id=email_doc.get("thread_id"),
            )

        # Update alert
        await db.meeting_alerts.update_one(
            {"_id": ObjectId(alert_id), "user_id": user_id},
            {
                "$set": {
                    "status": "declined",
                    "user_response": "no",
                    "reply_sent": True,
                    "resolved_at": datetime.now(timezone.utc),
                }
            },
        )

        logger.info("Meeting declined", alert_id=alert_id)
        return {"reply_preview": reply_text}

    async def suggest_time(
        self, alert_id: str, user_id: str, suggested_datetime: str
    ) -> dict:
        """
        Suggest Another Time — v3.1 spec section 5.4.
        Generates counter-proposal, sends reply, updates alert and email category.
        """
        from dateutil import parser as dateutil_parser

        db = get_database()

        alert = await db.meeting_alerts.find_one({"_id": ObjectId(alert_id)})
        if not alert:
            raise ValueError("Meeting alert not found")
        if alert["user_id"] != user_id:
            raise PermissionError("Alert does not belong to this user")
        if alert["status"] != "pending":
            raise ValueError(f"Alert is not pending (status: {alert['status']})")

        user = await db.users.find_one({"_id": ObjectId(user_id)})
        tone_profile = user.get("tone_profile") if user else None

        email_doc = await db.emails.find_one({"_id": ObjectId(alert["email_id"])})
        suggested_dt = dateutil_parser.parse(suggested_datetime)

        # Generate counter-proposal reply
        reply_text = await self._generate_suggest_reply(
            sender_name=alert["sender_name"],
            suggested_time=suggested_dt,
            tone_profile=tone_profile,
        )

        # Send via Gmail
        if email_doc:
            await self.gmail_service.send_reply(
                user_id=user_id,
                to_email=alert["sender_email"],
                subject=email_doc.get("subject", ""),
                body=reply_text,
                thread_id=email_doc.get("thread_id"),
            )

        # Update alert
        await db.meeting_alerts.update_one(
            {"_id": ObjectId(alert_id), "user_id": user_id},
            {
                "$set": {
                    "status": "suggested",
                    "user_response": "suggest",
                    "suggested_time": suggested_dt,
                    "reply_sent": True,
                }
            },
        )

        # Move email to 'awaiting_reply' category
        if email_doc:
            await db.emails.update_one(
                {"_id": email_doc["_id"], "user_id": user_id},
                {"$set": {"category": "awaiting_reply"}}
            )

        logger.info("Alternative time suggested", alert_id=alert_id)
        return {"reply_preview": reply_text}

    async def get_availability(self, alert_id: str, user_id: str) -> dict:
        """
        Fetch available time slots — v3.1 spec section 3.5.
        Returns next N available 1-hour slots within business hours.
        """
        settings = get_settings()
        db = get_database()

        alert = await db.meeting_alerts.find_one({"_id": ObjectId(alert_id)})
        if not alert:
            raise ValueError("Meeting alert not found")
        if alert["user_id"] != user_id:
            raise PermissionError("Alert does not belong to this user")

        credentials = await self.auth_service.get_user_credentials(user_id)
        if not credentials:
            raise ValueError("No Google credentials found")

        # Search next 5 business days
        proposed = alert.get("proposed_datetime", datetime.now(timezone.utc))
        slots = await self._find_available_slots(
            credentials=credentials,
            start_date=proposed,
            num_slots=settings.suggested_slots_count,
            business_start=settings.calendar_business_hours_start,
            business_end=settings.calendar_business_hours_end,
        )

        return {"available_slots": slots}

    async def get_pending_alerts(self, user_id: str) -> list[dict]:
        """Get all pending meeting alerts for a user, enriched with email subject and conflict info."""
        db = get_database()

        alerts = []
        cursor = db.meeting_alerts.find(
            {"user_id": user_id, "status": "pending"}
        ).sort("created_at", -1)

        async for alert in cursor:
            # Fetch the associated email to get the subject for a one-line summary
            email_subject = ""
            try:
                email_doc = await db.emails.find_one(
                    {"_id": ObjectId(alert["email_id"])},
                    {"subject": 1}
                )
                if email_doc:
                    email_subject = email_doc.get("subject", "")
            except Exception:
                pass

            # Build conflict info for "busy" alerts
            conflicts = []
            for c in alert.get("conflict_events", []):
                conflicts.append({
                    "title": c.get("title", ""),
                    "start": c["start"].isoformat() if hasattr(c.get("start"), "isoformat") else str(c.get("start", "")),
                    "end": c["end"].isoformat() if hasattr(c.get("end"), "isoformat") else str(c.get("end", "")),
                })

            alerts.append({
                "id": str(alert["_id"]),
                "type": "meeting_invitation",
                "sender_name": alert.get("sender_name", ""),
                "sender_email": alert.get("sender_email", ""),
                "email_subject": email_subject,
                "proposed_time": alert["proposed_datetime"].isoformat(),
                "duration_min": alert.get("duration_minutes", 60),
                "availability": alert.get("availability", "free"),
                "meeting_link": alert.get("meeting_link"),
                "meeting_platform": alert.get("meeting_platform", ""),
                "conflicts": conflicts,
                "status": alert.get("status", "pending"),
            })

        return alerts

    async def dismiss_alert(self, alert_id: str, user_id: str) -> dict:
        """Dismiss a meeting alert without taking action."""
        db = get_database()

        result = await db.meeting_alerts.update_one(
            {"_id": ObjectId(alert_id), "user_id": user_id, "status": "pending"},
            {
                "$set": {
                    "status": "dismissed",
                    "resolved_at": datetime.now(timezone.utc),
                }
            },
        )

        if result.modified_count == 0:
            raise ValueError("Alert not found or already resolved")

        return {"status": "dismissed"}

    async def resolve_conflict(self, alert_id: str, user_id: str, action: str) -> dict:
        """
        Handle conflict resolution. 
        action can be 'keep_both', 'reschedule_old', 'reschedule_new', 'remove_old'
        """
        db = get_database()

        alert = await db.meeting_alerts.find_one({"_id": ObjectId(alert_id)})
        if not alert:
            raise ValueError("Meeting alert not found")
        if alert["user_id"] != user_id:
            raise PermissionError("Alert does not belong to this user")

        if action == "keep_both":
            return await self.accept_meeting(alert_id, user_id)
            
        elif action == "reschedule_new":
            return await self.decline_meeting(alert_id, user_id, "I have a sudden conflict at that time. Could we please reschedule? Please suggest another time that works for you.")
            
        elif action == "remove_old" or action == "reschedule_old":
            if alert.get("conflict_events"):
                conflict = alert["conflict_events"][0]
                conflict_id = conflict.get("id")
                conflict_organizer = conflict.get("organizer_email")
                conflict_title = conflict.get("title", "Unknown")
                
                credentials = await self.auth_service.get_user_credentials(user_id)
                if credentials and conflict_id:
                    service = build("calendar", "v3", credentials=credentials)
                    try:
                        if action == "reschedule_old":
                            # Check if we are the organizer
                            event = service.events().get(calendarId='primary', eventId=conflict_id).execute()
                            attendees = event.get('attendees', [])
                            user = await db.users.find_one({"_id": ObjectId(user_id)})
                            user_email = user.get("email") if user else None
                            
                            is_organizer = True
                            if event.get('organizer', {}).get('email') and user_email and event['organizer']['email'] != user_email:
                                is_organizer = False
                            
                            if is_organizer:
                                service.events().delete(calendarId='primary', eventId=conflict_id, sendUpdates='all').execute()
                            else:
                                for att in attendees:
                                    if att.get('email') == user_email:
                                        att['responseStatus'] = 'declined'
                                event['attendees'] = attendees
                                service.events().update(calendarId='primary', eventId=conflict_id, body=event, sendUpdates='all').execute()
                                
                                if conflict_organizer:
                                    try:
                                        await self.gmail_service.send_reply(
                                            user_id=user_id,
                                            to_email=conflict_organizer,
                                            subject=f"Reschedule: {conflict_title}",
                                            body=f"Hi,\n\nI have a sudden conflict for our meeting '{conflict_title}'. Could we please reschedule it to a later time?\n\nBest regards",
                                            thread_id=None
                                        )
                                    except Exception as e:
                                        logger.warning("Failed to send reschedule email", error=str(e))
                                
                        elif action == "remove_old":
                            service.events().delete(calendarId='primary', eventId=conflict_id, sendUpdates='none').execute()
                    except Exception as e:
                        logger.warning("Failed to modify old google calendar event", error=str(e))
                        
            return await self.accept_meeting(alert_id, user_id)
            
        else:
            raise ValueError(f"Unknown action {action}")

    async def get_upcoming_events(self, user_id: str, max_results: int = 15) -> list[dict]:
        """Fetch the user's true upcoming schedule directly from Google Calendar."""
        credentials = await self.auth_service.get_user_credentials(user_id)
        if not credentials:
            raise ValueError("No Google credentials found")

        service = build("calendar", "v3", credentials=credentials)
        
        # Start looking from midnight today to show the full day's context
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

        try:
            events_result = service.events().list(
                calendarId='primary', 
                timeMin=today_start,
                maxResults=max_results, 
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            formatted_events = []
            
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                attendees = []
                for a in event.get('attendees', []):
                    attendees.append({
                        "email": a.get('email', ''),
                        "name": a.get('displayName', ''),
                        "status": a.get('responseStatus', 'needsAction'),
                        "organizer": a.get('organizer', False),
                    })

                formatted_events.append({
                    "id": event['id'],
                    "summary": event.get('summary', 'Busy'),
                    "start": start,
                    "end": end,
                    "location": event.get('location', ''),
                    "link": event.get('hangoutLink', ''),
                    "description": event.get('description', ''),
                    "attendees": attendees,
                    "organizer_email": event.get('organizer', {}).get('email', ''),
                    "status": event.get('status', 'confirmed'),
                })
                
            return formatted_events
        except Exception as e:
            logger.error("Failed to fetch calendar events", error=str(e))
            raise e

    # ──────────────────────────────────────────────
    # Private Helper Methods
    # ──────────────────────────────────────────────

    async def _generate_accept_reply(
        self, sender_name: str, proposed_time: datetime, subject: str, tone_profile: dict | None
    ) -> str:
        """Generate an AI-powered acceptance reply."""
        tone_str = str(tone_profile) if tone_profile else "Professional and friendly"

        result = await ai_provider.complete(
            system_prompt=f"You are an email reply assistant. Write in this style: {tone_str}. Write ONLY the reply text, no JSON.",
            user_prompt=f"Write a brief, warm acceptance reply to {sender_name} for a meeting on {proposed_time.strftime('%A, %B %d at %I:%M %p')}. Subject: {subject}. 2-3 sentences max.",
            temperature=0.4,
            task_type=TaskType.REPLY_DRAFT,
        )
        return result.strip()

    async def _generate_decline_reply(
        self, sender_name: str, reason: str | None, tone_profile: dict | None
    ) -> str:
        """Generate an AI-powered decline reply."""
        tone_str = str(tone_profile) if tone_profile else "Professional and friendly"
        reason_context = f" The reason is: {reason}" if reason else ""

        result = await ai_provider.complete(
            system_prompt=f"You are an email reply assistant. Write in this style: {tone_str}. Write ONLY the reply text, no JSON.",
            user_prompt=f"Write a polite, brief decline reply to {sender_name} for a meeting invitation.{reason_context} Be gracious. 2-3 sentences max.",
            temperature=0.4,
            task_type=TaskType.REPLY_DRAFT,
        )
        return result.strip()

    async def _generate_suggest_reply(
        self, sender_name: str, suggested_time: datetime, tone_profile: dict | None
    ) -> str:
        """Generate an AI-powered counter-proposal reply."""
        tone_str = str(tone_profile) if tone_profile else "Professional and friendly"

        result = await ai_provider.complete(
            system_prompt=f"You are an email reply assistant. Write in this style: {tone_str}. Write ONLY the reply text, no JSON.",
            user_prompt=f"Write a brief counter-proposal reply to {sender_name}. The proposed time doesn't work. Suggest {suggested_time.strftime('%A, %B %d at %I:%M %p')} instead. 2-3 sentences max.",
            temperature=0.4,
            task_type=TaskType.REPLY_DRAFT,
        )
        return result.strip()

    async def _create_calendar_event(
        self,
        credentials: Credentials,
        sender_name: str,
        proposed_datetime: datetime,
        proposed_timezone: str,
        duration_minutes: int,
        meeting_link: str | None,
        subject: str,
    ) -> str:
        """
        Create a Google Calendar event — v3.1 spec section 6.
        Returns the calendar event ID.
        """
        service = build("calendar", "v3", credentials=credentials)

        end_time = proposed_datetime + timedelta(minutes=duration_minutes)

        event = {
            "summary": f"Meeting with {sender_name}",
            "description": f"{meeting_link or ''}\n\nFrom email: {subject}",
            "location": meeting_link or "",
            "start": {
                "dateTime": proposed_datetime.isoformat(),
                "timeZone": proposed_timezone,
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": proposed_timezone,
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 15},
                    {"method": "email", "minutes": 60},
                ],
            },
            "source": {
                "title": "Nexus Mail",
                "url": "https://yourapp.vercel.app",
            },
        }

        result = service.events().insert(calendarId="primary", body=event).execute()
        calendar_event_id = result["id"]

        logger.info(
            "Calendar event created",
            event_id=calendar_event_id,
            summary=event["summary"],
        )

        return calendar_event_id

    async def _find_available_slots(
        self,
        credentials: Credentials,
        start_date: datetime,
        num_slots: int = 3,
        business_start: int = 9,
        business_end: int = 18,
    ) -> list[dict]:
        """
        Find available time slots — v3.1 spec section 3.5.
        - Search next 5 business days
        - Business hours: business_start to business_end
        - 1-hour slots with 15-minute buffer
        """
        service = build("calendar", "v3", credentials=credentials)
        slots = []

        current_date = start_date.replace(
            hour=business_start, minute=0, second=0, microsecond=0
        )

        days_checked = 0
        max_days = 7  # Check up to 7 days to find 5 business days

        while len(slots) < num_slots and days_checked < max_days:
            current_date += timedelta(days=1)
            days_checked += 1

            # Skip weekends
            if current_date.weekday() >= 5:
                continue

            # Check each hour in business hours
            for hour in range(business_start, business_end - 1):
                if len(slots) >= num_slots:
                    break

                slot_start = current_date.replace(hour=hour, minute=0)
                slot_end = slot_start + timedelta(hours=1)

                # Check with 15-min buffer
                buffer_start = slot_start - timedelta(minutes=15)
                buffer_end = slot_end + timedelta(minutes=15)

                try:
                    events_result = service.events().list(
                        calendarId="primary",
                        timeMin=buffer_start.isoformat(),
                        timeMax=buffer_end.isoformat(),
                        singleEvents=True,
                    ).execute()

                    events = events_result.get("items", [])
                    active_events = [e for e in events if e.get("status") != "cancelled"]

                    if not active_events:
                        slots.append({
                            "start": slot_start.isoformat(),
                            "end": slot_end.isoformat(),
                            "label": slot_start.strftime("%A %b %d · %I:%M %p"),
                        })
                except Exception as e:
                    logger.warning("Slot check failed", error=str(e))
                    continue

        return slots
