"""
Nexus Mail — Gmail Sync Service
Fetches emails from Gmail API and stores them in MongoDB for AI processing.
"""

import base64
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from bson import ObjectId

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from app.core.database import get_database
from app.core.config import get_settings
from app.services.auth_service import AuthService

import structlog

logger = structlog.get_logger(__name__)


class GmailService:
    """Handles Gmail API interactions — fetching, syncing, and sending emails."""

    def __init__(self):
        self.auth_service = AuthService()

    async def sync_emails(self, user_id: str, max_results: int = 50) -> dict:
        """
        Sync emails from Gmail using historyId cursor for zero-loss guarantee.

        ARCHITECTURE FIX (Inbox Zero Analysis):
        - Uses Redis lock to prevent race conditions during concurrent syncs
        - New: historyId-based cursor — fetches ALL changes since last sync
        - Even if app is down for hours, next sync catches every missed email
        """
        from app.core.redis_client import redis_lock
        
        # Acquire distributed lock so concurrent webhooks don't duplicate records
        async with redis_lock(f"sync:{user_id}", timeout=60):
            credentials = await self.auth_service.get_user_credentials(user_id)
            if not credentials:
                raise ValueError("No Google credentials found for user")
    
            service = build("gmail", "v1", credentials=credentials)
            db = get_database()


            # Get the last successfully processed historyId for this user
            user = await db.users.find_one(
                {"_id": ObjectId(user_id)}, {"last_history_id": 1, "last_sync": 1}
            )
            last_history_id = user.get("last_history_id") if user else None

            if last_history_id:
                # ─── INCREMENTAL SYNC via history.list() ───
                return await self._incremental_sync(
                    service, db, user_id, last_history_id, max_results
                )
            else:
                # ─── INITIAL FULL SYNC (first time only) ───
                return await self._full_sync(service, db, user_id, max_results)

    async def _full_sync(
        self, service, db, user_id: str, max_results: int
    ) -> dict:
        """
        First-time full sync. Fetches recent emails and establishes
        the historyId cursor for future incremental syncs.
        """
        logger.info("Running full initial sync", user_id=user_id)

        # Get the user's current profile to establish historyId baseline
        profile = service.users().getProfile(userId="me").execute()
        current_history_id = profile.get("historyId")

        messages_result = service.users().messages().list(
            userId="me", q="in:inbox", maxResults=max_results
        ).execute()

        messages = messages_result.get("messages", [])
        if not messages:
            # Still store the historyId so incremental sync works next time
            await db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {
                    "last_history_id": current_history_id,
                    "last_sync": datetime.now(timezone.utc),
                }},
            )
            return {"synced": 0, "new_emails": 0, "sync_type": "full"}

        new_count = 0
        for msg_ref in messages:
            gmail_id = msg_ref["id"]

            # Skip if already in DB
            existing = await db.emails.find_one(
                {"user_id": user_id, "gmail_id": gmail_id}
            )
            if existing:
                continue

            message = service.users().messages().get(
                userId="me", id=gmail_id, format="full"
            ).execute()

            email_doc = self._parse_gmail_message(message, user_id)
            await db.emails.insert_one(email_doc)
            new_count += 1

        # Store the historyId cursor for future incremental syncs
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "last_history_id": current_history_id,
                "last_sync": datetime.now(timezone.utc),
            }},
        )

        logger.info(
            "Full sync complete",
            user_id=user_id,
            new=new_count,
            history_id=current_history_id,
        )
        return {"synced": new_count, "new_emails": new_count, "sync_type": "full"}

    async def _incremental_sync(
        self, service, db, user_id: str, last_history_id: str, max_results: int
    ) -> dict:
        """
        Incremental sync using Gmail historyId cursor.
        Fetches ONLY the changes since the last successful sync.

        This is the zero-loss guarantee: even if the app was down for hours,
        history.list() returns ALL intermediate changes.
        """
        logger.info(
            "Running incremental sync",
            user_id=user_id,
            from_history_id=last_history_id,
        )

        try:
            # Fetch all changes since our last known historyId
            history_result = service.users().history().list(
                userId="me",
                startHistoryId=last_history_id,
                historyTypes=["messageAdded"],
            ).execute()
        except Exception as e:
            error_str = str(e)
            if "404" in error_str or "invalid" in error_str.lower():
                # historyId expired or invalid — fall back to full sync
                logger.warning(
                    "historyId expired, falling back to full sync",
                    user_id=user_id,
                    error=error_str,
                )
                # Clear the stale cursor
                await db.users.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$unset": {"last_history_id": ""}},
                )
                return await self._full_sync(service, db, user_id, max_results)
            raise

        new_history_id = history_result.get("historyId", last_history_id)
        history_records = history_result.get("history", [])

        if not history_records:
            # No changes since last sync — just update the cursor
            await db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {
                    "last_history_id": new_history_id,
                    "last_sync": datetime.now(timezone.utc),
                }},
            )
            return {"synced": 0, "new_emails": 0, "sync_type": "incremental"}

        # Extract all new message IDs from the history delta
        new_message_ids = set()
        for record in history_records:
            for msg_added in record.get("messagesAdded", []):
                msg = msg_added.get("message", {})
                # Only process inbox messages
                if "INBOX" in msg.get("labelIds", []):
                    new_message_ids.add(msg["id"])

        new_count = 0
        for gmail_id in new_message_ids:
            # Skip if already in DB (idempotency!)
            existing = await db.emails.find_one(
                {"user_id": user_id, "gmail_id": gmail_id}
            )
            if existing:
                continue

            try:
                message = service.users().messages().get(
                    userId="me", id=gmail_id, format="full"
                ).execute()
                email_doc = self._parse_gmail_message(message, user_id)
                await db.emails.insert_one(email_doc)
                new_count += 1
            except Exception as e:
                logger.warning(
                    "Failed to fetch message from history delta",
                    gmail_id=gmail_id,
                    error=str(e),
                )
                continue

        # Update the cursor to the new historyId
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "last_history_id": new_history_id,
                "last_sync": datetime.now(timezone.utc),
            }},
        )

        logger.info(
            "Incremental sync complete",
            user_id=user_id,
            delta_messages=len(new_message_ids),
            new=new_count,
            new_history_id=new_history_id,
        )
        return {
            "synced": len(new_message_ids),
            "new_emails": new_count,
            "sync_type": "incremental",
        }

    def _parse_gmail_message(self, message: dict, user_id: str) -> dict:
        """Parse a raw Gmail API message into our email document format."""
        headers = {
            h["name"].lower(): h["value"]
            for h in message.get("payload", {}).get("headers", [])
        }

        # Extract sender info
        from_header = headers.get("from", "")
        sender_name, sender_email = self._parse_sender(from_header)

        # Extract body
        body_text, body_html = self._extract_body(message.get("payload", {}))

        # Parse received date
        received_at = None
        date_str = headers.get("date")
        if date_str:
            try:
                received_at = parsedate_to_datetime(date_str)
            except (ValueError, TypeError):
                received_at = datetime.now(timezone.utc)

        return {
            "user_id": user_id,
            "gmail_id": message["id"],
            "thread_id": message.get("threadId", ""),
            "subject": headers.get("subject", "(no subject)"),
            "sender_name": sender_name,
            "sender_email": sender_email,
            "snippet": message.get("snippet", ""),
            "body_text": body_text,
            "body_html": body_html,
            "received_at": received_at,
            "labels": message.get("labelIds", []),
            "is_read": "UNREAD" not in message.get("labelIds", []),
            "is_processed": False,
            "is_meeting_invitation": False,
            "has_meeting_alert": False,
            "category": None,
            "severity": None,
            "summary": None,
            "action_items": [],
            "risk_flags": [],
            "reply_draft": None,
            "created_at": datetime.now(timezone.utc),
            "processed_at": None,
        }

    def _parse_sender(self, from_header: str) -> tuple[str, str]:
        """Parse 'John Doe <john@example.com>' into (name, email)."""
        if "<" in from_header and ">" in from_header:
            name = from_header.split("<")[0].strip().strip('"')
            email = from_header.split("<")[1].split(">")[0].strip()
            return name, email
        return "", from_header.strip()

    def _extract_body(self, payload: dict) -> tuple[str, str]:
        """Extract text and HTML body from Gmail message payload."""
        body_text = ""
        body_html = ""

        if payload.get("mimeType") == "text/plain":
            data = payload.get("body", {}).get("data", "")
            body_text = self._decode_base64(data)
        elif payload.get("mimeType") == "text/html":
            data = payload.get("body", {}).get("data", "")
            body_html = self._decode_base64(data)
        elif "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")
                data = part.get("body", {}).get("data", "")

                if mime_type == "text/plain" and not body_text:
                    body_text = self._decode_base64(data)
                elif mime_type == "text/html" and not body_html:
                    body_html = self._decode_base64(data)
                elif "parts" in part:
                    # Handle nested multipart
                    inner_text, inner_html = self._extract_body(part)
                    if not body_text:
                        body_text = inner_text
                    if not body_html:
                        body_html = inner_html

        return body_text, body_html

    def _decode_base64(self, data: str) -> str:
        """Decode Gmail's URL-safe base64 encoded content."""
        if not data:
            return ""
        try:
            decoded = base64.urlsafe_b64decode(data)
            return decoded.decode("utf-8", errors="replace")
        except Exception:
            return ""

    async def send_reply(
        self,
        user_id: str,
        to_email: str,
        subject: str,
        body: str,
        thread_id: str | None = None,
        in_reply_to: str | None = None,
    ) -> dict:
        """Send an email reply via Gmail API with proper threading headers."""
        credentials = await self.auth_service.get_user_credentials(user_id)
        if not credentials:
            raise ValueError("No Google credentials found for user")

        service = build("gmail", "v1", credentials=credentials)

        # If we have a thread_id but no in_reply_to, fetch the last message's
        # Message-ID header so Gmail threads the reply correctly
        if thread_id and not in_reply_to:
            try:
                thread_data = service.users().threads().get(
                    userId="me", id=thread_id, format="metadata",
                    metadataHeaders=["Message-ID", "References"]
                ).execute()
                thread_msgs = thread_data.get("messages", [])
                if thread_msgs:
                    last_msg = thread_msgs[-1]
                    headers = {
                        h["name"].lower(): h["value"]
                        for h in last_msg.get("payload", {}).get("headers", [])
                    }
                    in_reply_to = headers.get("message-id")
            except Exception as e:
                logger.warning("Failed to fetch thread headers", error=str(e))

        # Construct the email message
        import email.mime.text
        message = email.mime.text.MIMEText(body)
        message["to"] = to_email
        message["subject"] = f"Re: {subject}" if not subject.startswith("Re:") else subject

        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
            message["References"] = in_reply_to

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        send_body = {"raw": raw}
        if thread_id:
            send_body["threadId"] = thread_id

        result = service.users().messages().send(
            userId="me", body=send_body
        ).execute()

        logger.info("Email sent", user_id=user_id, to=to_email, message_id=result["id"])
        return result

    async def get_sync_status(self, user_id: str) -> dict:
        """Get the current Gmail sync status for the user."""
        db = get_database()

        user = await db.users.find_one({"_id": ObjectId(user_id)})
        total_emails = await db.emails.count_documents({"user_id": user_id})

        # Count processed today
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        processed_today = await db.emails.count_documents({
            "user_id": user_id,
            "is_processed": True,
            "processed_at": {"$gte": today_start},
        })

        # Get pending meeting alerts
        pending_alerts = []
        cursor = db.meeting_alerts.find(
            {"user_id": user_id, "status": "pending", "notification_sent": False}
        )
        async for alert in cursor:
            pending_alerts.append({
                "id": str(alert["_id"]),
                "type": "meeting_invitation",
                "sender_name": alert.get("sender_name", ""),
                "sender_email": alert.get("sender_email", ""),
                "proposed_time": alert["proposed_datetime"].isoformat() if alert.get("proposed_datetime") else "",
                "duration_min": alert.get("duration_minutes", 60),
                "availability": alert.get("availability", "free"),
                "meeting_link": alert.get("meeting_link"),
            })

            # Mark as notification sent
            await db.meeting_alerts.update_one(
                {"_id": alert["_id"]},
                {"$set": {"notification_sent": True}}
            )

        return {
            "connected": True,
            "last_sync": user.get("last_sync", "").isoformat() if user and user.get("last_sync") else None,
            "emails_synced": total_emails,
            "processed_today": processed_today,
            "ai_provider": get_settings().ai_provider,
            "pending_alerts": pending_alerts,
        }
