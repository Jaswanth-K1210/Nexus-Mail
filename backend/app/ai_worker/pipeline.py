"""
Nexus Mail — Email Processing Pipeline
Orchestrates the 6-task AI pipeline for each email.
Per v3.1 spec Task Order:
  Task 1: classify.py — every email
  Task 2: meeting_intelligence.py — conditional (if meeting)
  Task 3: summarise.py — every email
  Task 4: extract_actions.py — every email
  Task 5: risk_detect.py — every email
  Task 6: reply_draft.py — every email
"""

from datetime import datetime, timezone

from app.core.database import get_database
from app.services.auth_service import AuthService
from app.ai_worker.tasks.classify import classify_email
from app.ai_worker.tasks.meeting_intelligence import process_meeting_invitation
from app.ai_worker.tasks.summarise import summarise_email
from app.ai_worker.tasks.extract_actions import extract_actions
from app.ai_worker.tasks.risk_detect import detect_risks
from app.ai_worker.tasks.reply_draft import generate_reply_draft

from app.services.cold_email_service import ColdEmailBlocker
from app.services.unsubscribe_service import UnsubscribeService
from app.services.sse_service import push_to_user
from app.services.rules_engine import RulesEngine
from app.services.draft_service import DraftService
from app.services.priority_service import PriorityService
from app.ai_worker.sanitizer import sanitize_email_body

import structlog

logger = structlog.get_logger(__name__)


class ProcessingPipeline:
    """
    Orchestrates the complete AI processing pipeline for emails.
    Processes unprocessed emails from MongoDB, runs all 6 AI tasks,
    and updates the email document with results.
    """

    def __init__(self):
        self.auth_service = AuthService()
        self.cold_email_blocker = ColdEmailBlocker()
        self.unsub_service = UnsubscribeService()
        self.rules_engine = RulesEngine()
        self.draft_service = DraftService()
        self.priority_service = PriorityService()

    async def process_email(self, email_id: str, user_id: str) -> dict:
        """
        Process a single email through the full 6-task AI pipeline.
        Returns a summary of what was done.
        """
        from app.core.redis_client import redis_lock

        async with redis_lock(f"process:{email_id}", timeout=120):
            db = get_database()
    
            # Fetch the email
            from bson import ObjectId
            email_doc = await db.emails.find_one({"_id": ObjectId(email_id)})
            if not email_doc:
                raise ValueError(f"Email not found: {email_id}")
    
            if email_doc.get("is_processed"):
                logger.info("Email already processed", email_id=email_id)
                return {"status": "already_processed"}


        # ─── Inbox Zero Feature: Bulk Unsubscriber Auto-Archive Check ───
        was_auto_archived = await self.unsub_service.apply_auto_archive_rules(user_id, email_doc)
        if was_auto_archived:
            # Mark as processed and skip further AI processing
            await db.emails.update_one(
                {"_id": ObjectId(email_id)},
                {"$set": {"is_processed": True, "processed_at": datetime.now(timezone.utc)}}
            )
            return {"status": "auto_archived"}

        # ─── Inbox Zero Feature: Cold Email Blocker ───
        cold_email_result = await self.cold_email_blocker.process_incoming_email(user_id, email_doc)
        if cold_email_result and cold_email_result.get("is_cold_email") and cold_email_result.get("confidence", 0) >= 0.7:
            # If auto-archived by blocker mode, we conceptually skip further tasks
            settings = await self.cold_email_blocker.get_blocker_settings(user_id)
            if settings.get("mode") == "auto_archive_label":
                await db.emails.update_one(
                    {"_id": ObjectId(email_id)},
                    {"$set": {"is_processed": True, "processed_at": datetime.now(timezone.utc)}}
                )
                return {"status": "blocked_cold_email"}

        subject = email_doc.get("subject", "")
        sender = email_doc.get("sender_email", "")
        sender_name = email_doc.get("sender_name", "")

        # ─── Sanitize email body before AI processing (Inbox Zero fix) ───
        # Strips tracking pixels, CSS, HTML noise, and signatures
        # Reduces token consumption by 40-70% on HTML-heavy emails
        body = sanitize_email_body(
            body_text=email_doc.get("body_text", ""),
            body_html=email_doc.get("body_html", ""),
        )

        results = {"email_id": email_id, "tasks_completed": []}

        # ─── Task 1: Classification ───
        logger.info("Task 1: Classifying email", email_id=email_id)
        classification = await classify_email(
            subject=subject,
            body=body,
            sender=sender,
            has_ics=False,  # TODO: check attachments for .ics
        )
        results["classification"] = classification
        results["tasks_completed"].append("classify")

        is_meeting = classification.get("is_meeting_invitation", False)

        # ─── Task 2: Meeting Intelligence (conditional) ───
        meeting_result = None
        if is_meeting:
            logger.info("Task 2: Processing meeting invitation", email_id=email_id)

            # Get user's Google credentials for calendar access
            credentials = await self.auth_service.get_user_credentials(user_id)

            meeting_result = await process_meeting_invitation(
                email_id=email_id,
                user_id=user_id,
                email_body=body,
                sender_name=sender_name,
                sender_email=sender,
                subject=subject,
                credentials=credentials,
            )
            results["meeting_intelligence"] = meeting_result
            results["tasks_completed"].append("meeting_intelligence")

        # ─── Task 3: Summarization ───
        logger.info("Task 3: Summarizing email", email_id=email_id)
        summary = await summarise_email(
            subject=subject,
            body=body,
            sender=f"{sender_name} <{sender}>",
            is_meeting=is_meeting,
        )
        results["summary"] = summary
        results["tasks_completed"].append("summarise")

        # ─── Task 4: Action Items ───
        logger.info("Task 4: Extracting actions", email_id=email_id)
        actions = await extract_actions(
            subject=subject,
            body=body,
            sender=f"{sender_name} <{sender}>",
            is_meeting=is_meeting,
        )
        results["actions"] = actions
        results["tasks_completed"].append("extract_actions")

        # ─── Task 5: Risk Detection ───
        logger.info("Task 5: Detecting risks", email_id=email_id)
        risks = await detect_risks(
            subject=subject,
            body=body,
            sender=sender_name,
            sender_email=sender,
            is_meeting=is_meeting,
        )
        results["risks"] = risks
        results["tasks_completed"].append("risk_detect")

        # ─── Task 6: Reply Draft ───
        # ARCHITECTURE FIX (Superhuman Analysis — Pre-Computation Paradox):
        # Meeting reply drafts are NO LONGER pre-computed here.
        # They are generated on-demand when the user clicks Accept/Decline.
        # This saves ~60% of wasted LLM inference on dismissed meetings.
        # Only regular (non-meeting) emails get pre-computed drafts.

        reply = {}
        if not is_meeting:
            logger.info("Task 6: Generating reply draft", email_id=email_id)

            user = await db.users.find_one({"_id": user_id}, {"tone_profile": 1})
            tone_profile = user.get("tone_profile") if user else None

            reply = await generate_reply_draft(
                subject=subject,
                body=body,
                sender=sender,
                sender_name=sender_name,
                is_meeting=False,
                tone_profile=tone_profile,
                availability=None,
            )
            results["reply"] = reply
            results["tasks_completed"].append("reply_draft")
        else:
            logger.info(
                "Task 6: Skipped (meeting draft generated on-demand)",
                email_id=email_id,
            )
            results["tasks_completed"].append("reply_draft_deferred")

        # ─── Task 7: Smart Priority Scoring (Phase 2.1) ───
        logger.info("Task 7: Scoring priority", email_id=email_id)
        # We need to construct a rich email doc so the PriorityService has all the data.
        enriched_email_doc = {**email_doc}
        enriched_email_doc["category"] = classification.get("category")
        enriched_email_doc["severity"] = classification.get("severity")
        enriched_email_doc["is_meeting_invitation"] = is_meeting
        enriched_email_doc["subject"] = subject
        enriched_email_doc["body_text"] = body
        enriched_email_doc["sender_email"] = sender
        
        priority_score = await self.priority_service.score_email(user_id, enriched_email_doc)
        results["tasks_completed"].append("priority_scoring")
        results["priority_score"] = priority_score

        # ─── Update email document with all AI results ───
        update_data = {
            "is_processed": True,
            "processed_at": datetime.now(timezone.utc),
            "category": classification.get("category"),
            "severity": classification.get("severity"),
            "is_meeting_invitation": is_meeting,
            "summary": summary.get("summary"),
            "priority_score": priority_score,
            "action_items": [
                item.get("action", "") for item in actions.get("action_items", [])
            ],
            "risk_flags": risks.get("risk_flags", []),
        }

        # Store reply draft via draft-first service (not directly on email)
        if not is_meeting and reply.get("reply_draft"):
            await self.draft_service.create_draft(
                user_id=user_id,
                email_id=email_id,
                draft_body=reply.get("reply_draft", ""),
                draft_type="reply",
                ai_confidence=0.8,
                recipient_email=sender,
                recipient_name=sender_name,
                subject=subject,
                thread_id=email_doc.get("thread_id"),
                source="pipeline",
            )
        # RELY ON MONGODB 30-DAY TTL FOR SAAS SCALING
        # We store the email so it appears in the 'Other Inbox' and the user can actually read it if they need to.
        # The database automatically purges all emails older than 30 days to save cloud storage costs.
        await db.emails.update_one(
            {"_id": ObjectId(email_id)},
            {"$set": update_data}
        )

        # ─── Evaluate natural language rules (Phase 1.2) ───
        matched_rules = await self.rules_engine.evaluate_all_rules(user_id, email_doc)
        if matched_rules:
            # Merge email_doc with AI results for richer rule evaluation
            enriched_doc = {**email_doc, **update_data}
            for rule_match in matched_rules:
                action_results = await self.rules_engine.execute_actions(
                    user_id, email_id, rule_match["actions"], enriched_doc
                )
                results.setdefault("rules_executed", []).append({
                    "rule": rule_match["rule_text"][:60],
                    "actions": action_results,
                })

        # ─── Push real-time SSE events ───
        await push_to_user(user_id, "email_processed", {
            "email_id": email_id,
            "category": classification.get("category"),
            "summary": summary.get("summary", "")[:100],
            "is_meeting": is_meeting,
            "rules_matched": len(matched_rules),
        })

        if is_meeting and meeting_result:
            await push_to_user(user_id, "meeting_alert", {
                "email_id": email_id,
                "sender_name": sender_name,
                "sender_email": sender,
                "availability": meeting_result.get("availability", "free"),
                "proposed_time": str(meeting_result.get("proposed_datetime", "")),
            })

        return results

    async def process_unprocessed_emails(self, user_id: str, limit: int = 10) -> dict:
        """
        Process all unprocessed emails for a user.
        Called by the background worker or on-demand.
        """
        db = get_database()

        cursor = db.emails.find(
            {"user_id": user_id, "is_processed": False},
            {"_id": 1},
        ).sort("received_at", -1).limit(limit)

        processed = 0
        errors = 0

        async for email_doc in cursor:
            try:
                await self.process_email(str(email_doc["_id"]), user_id)
                processed += 1
            except Exception as e:
                logger.error(
                    "Failed to process email",
                    email_id=str(email_doc["_id"]),
                    error=str(e),
                )
                errors += 1

        logger.info(
            "Batch processing complete",
            user_id=user_id,
            processed=processed,
            errors=errors,
        )

        return {"processed": processed, "errors": errors}
