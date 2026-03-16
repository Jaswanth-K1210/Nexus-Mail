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

import asyncio
from datetime import datetime, timezone
from bson import ObjectId

from app.core.database import get_database
from app.services.auth_service import AuthService
from app.ai_worker.tasks.classify import classify_email
from app.ai_worker.tasks.meeting_intelligence import process_meeting_invitation
from app.ai_worker.tasks.summarise import summarise_email
from app.ai_worker.tasks.extract_actions import extract_actions
from app.ai_worker.tasks.risk_detect import detect_risks

from app.services.cold_email_service import ColdEmailBlocker
from app.services.unsubscribe_service import UnsubscribeService
from app.services.sse_service import push_to_user
from app.services.rules_engine import RulesEngine
from app.services.priority_service import PriorityService
from app.services.gmail_service import GmailService
from app.services.auto_reply_service import AutoReplyService
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
        self.priority_service = PriorityService()
        self.gmail_service = GmailService()
        self.auto_reply_service = AutoReplyService()

    async def process_email(self, email_id: str, user_id: str) -> dict:
        """
        Process a single email through the full 6-task AI pipeline.
        Returns a summary of what was done.
        Bug #1 Fix: The Redis lock now covers the ENTIRE pipeline, preventing
        duplicate concurrent processing of the same email.
        """
        from app.core.redis_client import redis_lock

        db = get_database()

        async with redis_lock(f"process:{email_id}", timeout=300):
            # Fetch the email
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

            # ─── Fetch User Persona + Role for Classification ───
            user_doc = await db.users.find_one(
                {"_id": ObjectId(user_id)},
                {"tone_profile": 1, "user_context": 1},
            )
            user_persona = ""
            user_role = None
            if user_doc:
                if user_doc.get("tone_profile"):
                    user_persona = user_doc["tone_profile"].get("professional_persona", "")
                if user_doc.get("user_context"):
                    user_role = user_doc["user_context"].get("role_key")

            # ─── Task 1: Classification ───
            logger.info("Task 1: Classifying email", email_id=email_id, user_role=user_role)
            classification = await classify_email(
                subject=subject,
                body=body,
                sender=sender,
                has_ics=False,  # TODO: check attachments for .ics
                user_persona=user_persona,
                user_role=user_role,
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
                    thread_id=email_doc.get("thread_id"),
                    credentials=credentials,
                )
                results["meeting_intelligence"] = meeting_result
                results["tasks_completed"].append("meeting_intelligence")

            # ─── Tasks 3, 4, 5: Run in parallel (independent) ───
            logger.info("Tasks 3-5: Running summarization, action extraction, risk detection in parallel", email_id=email_id)
            summary_task = summarise_email(
                subject=subject,
                body=body,
                sender=f"{sender_name} <{sender}>",
                is_meeting=is_meeting,
            )
            actions_task = extract_actions(
                subject=subject,
                body=body,
                sender=f"{sender_name} <{sender}>",
                is_meeting=is_meeting,
            )
            risks_task = detect_risks(
                subject=subject,
                body=body,
                sender=sender_name,
                sender_email=sender,
                is_meeting=is_meeting,
            )

            summary, actions, risks = await asyncio.gather(
                summary_task, actions_task, risks_task,
                return_exceptions=True,
            )

            # Handle any exceptions from parallel tasks
            if isinstance(summary, Exception):
                logger.error("Summarization failed", error=str(summary))
                summary = {"summary": "Summary generation failed", "key_topic": "Unknown"}
            if isinstance(actions, Exception):
                logger.error("Action extraction failed", error=str(actions))
                actions = {"action_items": []}
            if isinstance(risks, Exception):
                logger.error("Risk detection failed", error=str(risks))
                risks = {"risk_flags": []}

            results["summary"] = summary
            results["tasks_completed"].append("summarise")
            results["actions"] = actions
            results["tasks_completed"].append("extract_actions")
            results["risks"] = risks
            results["tasks_completed"].append("risk_detect")

            # ARCHITECTURE FIX: All reply drafts are now ON-DEMAND only.
            # Drafts are generated when the user explicitly clicks "Generate Draft"
            # in the email detail modal. This prevents unwanted pre-computed drafts
            # and saves LLM inference costs.
            logger.info(
                "Task 6: Skipped (all drafts are on-demand)",
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
                "suggested_action": classification.get("suggested_action", "REVIEW ONLY"),
                "is_meeting_invitation": is_meeting,
                "ai_summary": summary.get("summary"),
                "priority_score": priority_score,
                "action_items": [
                    {
                        "task": item.get("action", ""),
                        "priority": item.get("priority", "medium"),
                        "deadline": item.get("deadline"),
                        "type": item.get("type", "other"),
                    }
                    for item in actions.get("action_items", [])
                ],
                "risk_flags": risks.get("risk_flags", []),
            }

            # RELY ON MONGODB 30-DAY TTL FOR SAAS SCALING
            # We store the email so it appears in the 'Other Inbox' and the user can actually read it if they need to.
            # The database automatically purges all emails older than 30 days to save cloud storage costs.
            await db.emails.update_one(
                {"_id": ObjectId(email_id)},
                {"$set": update_data}
            )

            # ─── Auto-Reply for low-priority emails ───
            enriched_doc = {**email_doc, **update_data}
            try:
                if await self.auto_reply_service.should_auto_reply(user_id, enriched_doc):
                    auto_reply_result = await self.auto_reply_service.generate_and_send(user_id, enriched_doc)
                    if auto_reply_result:
                        results["auto_reply"] = auto_reply_result
                        results["tasks_completed"].append("auto_reply")
                        logger.info("Auto-reply sent", email_id=email_id, to=sender)
            except Exception as e:
                logger.warning("Auto-reply step failed (non-fatal)", email_id=email_id, error=str(e))

            # ─── Evaluate natural language rules (Phase 1.2) ───
            # BUG FIX: Use enriched doc with AI results so category/meeting-based rules work.
            # Previously used raw email_doc where category=None, so rules never matched.
            matched_rules = await self.rules_engine.evaluate_all_rules(user_id, enriched_doc)
            if matched_rules:
                for rule_match in matched_rules:
                    try:
                        action_results = await self.rules_engine.execute_actions(
                            user_id, email_id, rule_match["actions"], enriched_doc
                        )
                        results.setdefault("rules_executed", []).append({
                            "rule": rule_match["rule_text"][:60],
                            "actions": action_results,
                        })
                    except Exception as e:
                        logger.warning(
                            "Rule action execution failed",
                            rule=rule_match.get("rule_text", "")[:60],
                            error=str(e),
                        )

            # ─── Mark as read on Gmail after processing (IBM pattern) ───
            # This prevents the sync from re-fetching the same email on every cycle.
            # Gmail query uses "is:unread", so marking read = never re-synced.
            gmail_id = email_doc.get("gmail_id")
            if gmail_id:
                try:
                    await self.gmail_service.mark_as_read_on_gmail(user_id, gmail_id)
                except Exception as e:
                    logger.warning("Gmail mark-as-read failed", gmail_id=gmail_id, error=str(e))

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
